import requests
import re
import json
import logging
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("XHS_Scraper")

# HÀM MỚI: Trích xuất URL từ văn bản bất kỳ
def extract_urls_from_text(text):
    """
    Tìm tất cả các link http/https trong văn bản.
    Xử lý cả trường hợp link bị dính liền với chữ (ví dụ: texthttp://...)
    """
    # Regex tìm pattern bắt đầu bằng http:// hoặc https://
    # Dừng lại khi gặp khoảng trắng hoặc các ký tự không phải URL
    url_pattern = r'(https?://[^\s]+)'
    found_urls = re.findall(url_pattern, text)
    
    clean_urls = []
    for url in found_urls:
        # Lọc sơ bộ, chỉ lấy link liên quan xiaohongshu hoặc xhslink
        if 'xiaohongshu.com' in url or 'xhslink.com' in url:
            clean_urls.append(url.strip())
            
    return list(set(clean_urls)) # Loại bỏ trùng lặp

class XHSScraper:
    def __init__(self, cookies=None):
        self.session = requests.Session()
        self.cookie = cookies if cookies else ""
        self.ua_desktop = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        self.ua_mobile = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"

    def _get_headers(self, type="desktop"):
        headers = {
            "User-Agent": self.ua_mobile if type == "mobile" else self.ua_desktop,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if self.cookie: headers["Cookie"] = self.cookie
        return headers

    def resolve_redirects(self, url: str) -> str:
        """
        Xử lý link rút gọn xhslink.com
        """
        if "xhslink.com" in url:
            try:
                # Phải chặn redirect tự động để lấy header Location chính xác hoặc để requests tự xử lý chuỗi redirect
                res = self.session.get(url, headers=self._get_headers("mobile"), allow_redirects=True, timeout=10)
                # Link thật thường nằm ở res.url sau khi redirect xong
                return res.url
            except Exception as e:
                logger.error(f"Error resolving redirect: {e}")
                return url
        return url

    def extract_note_id(self, url: str) -> str:
        # Làm sạch URL, bỏ các tham số query (?...) để tránh nhiễu
        clean_url = url.split('?')[0]
        
        patterns = [
            r'/explore/([a-fA-F0-9]{24})', 
            r'/discovery/item/([a-fA-F0-9]{24})', 
            r'item/([a-fA-F0-9]{24})'
        ]
        for p in patterns:
            match = re.search(p, clean_url)
            if match: return match.group(1)
            
        # Fallback: Thử tìm trong toàn bộ URL gốc nếu clean_url thất bại
        for p in patterns:
            match = re.search(p, url)
            if match: return match.group(1)
            
        return None

    def get_data(self, raw_url: str):
        # Bước 1: Giải mã link rút gọn
        real_url = self.resolve_redirects(raw_url.strip())
        logger.info(f"Processing Real URL: {real_url}")
        
        # Bước 2: Lấy Note ID
        note_id = self.extract_note_id(real_url)
        if not note_id: 
            return {"success": False, "message": f"Không tìm thấy ID bài viết. Link gốc: {raw_url}"}

        logger.info(f"Found Note ID: {note_id}")

        # Chiến thuật 1: Sử dụng HTML Mobile (Thường ổn định nhất nếu không có API Key xịn)
        try:
            res = self.session.get(real_url, headers=self._get_headers("mobile"), timeout=10)
            data = self._parse_html_soup(res.text)
            if data: return data
        except Exception as e:
            logger.warning(f"Strategy Mobile failed: {e}")

        # Chiến thuật 2: Sử dụng thư viện xhs (Nếu có cookie xịn)
        try:
            from xhs import XhsClient
            if self.cookie:
                client = XhsClient(cookie=self.cookie)
                note = client.get_note_by_id(note_id)
                if note: return self._format_response(note, "API Lib")
        except Exception as e:
             logger.warning(f"Strategy Lib failed: {e}")

        # Chiến thuật 3: HTML Desktop
        try:
            res = self.session.get(real_url, headers=self._get_headers("desktop"), timeout=10)
            data = self._parse_html_soup(res.text)
            if data: return data
        except Exception as e:
             logger.warning(f"Strategy Desktop failed: {e}")

        return {"success": False, "message": "Cần cập nhật Cookie mới để tải bài này."}

    def _parse_html_soup(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and '__INITIAL_STATE__' in script.string:
                try:
                    json_text = script.string
                    start = json_text.find('{')
                    end = json_text.rfind('}') + 1
                    if start != -1:
                        json_str = json_text[start:end].replace("undefined", "null")
                        state = json.loads(json_str)
                        
                        # Cấu trúc JSON của XHS thay đổi tùy lúc, cần traverse cẩn thận
                        note_data = state.get("note", {}).get("noteDetailMap", {})
                        if not note_data:
                            # Thử cấu trúc khác nếu có
                            note_data = state.get("note", {}).get("note", {})
                            
                        if note_data:
                            # noteDetailMap thường lưu dạng { "noteId": { ...data... } }
                            # Lấy value đầu tiên trong map
                            first_value = next(iter(note_data.values())) if isinstance(note_data, dict) else note_data
                            
                            # Có thể lồng nhau thêm 1 lớp nữa
                            final_note = first_value.get("note", first_value)
                            
                            return self._format_response(final_note, "HTML Soup")
                except Exception as e:
                    logger.error(f"Error parsing soup: {e}")
                    pass
        return None

    def _format_response(self, note, source):
        if not note: return None
        title = note.get('title', 'No Title')
        type_ = note.get('type', 'normal')
        note_id = note.get('noteId', 'unknown')
        files = []

        # Logic lấy Video
        if type_ == 'video':
            video_node = note.get('video', {})
            # Thử lấy nhiều nguồn url khác nhau
            url = None
            
            # Ưu tiên h264 master
            media = video_node.get('media', {})
            stream = media.get('stream', {})
            h264 = stream.get('h264', [])
            if h264 and len(h264) > 0:
                url = h264[0].get('masterUrl')
                
            if not url: url = video_node.get('masterUrl')
            
            # Xử lý trường hợp consumer key
            if not url: 
                origin_key = video_node.get('consumer', {}).get('originVideoKey')
                if origin_key:
                    url = f"https://sns-video-bd.xhscdn.com/{origin_key}"
            
            # FORCE HTTPS
            if url:
                if url.startswith('http:'): url = url.replace('http:', 'https:')
                if url.startswith('//'): url = 'https:' + url
                
                cover_url = note.get('imageList', [{}])[0].get('urlDefault', '')
                if cover_url.startswith('//'): cover_url = 'https:' + cover_url

                files.append({
                    "type": "video", 
                    "url": url, 
                    "cover": cover_url,
                    "filename": f"RedNote_{note_id}.mp4"
                })
        
        # Logic lấy Ảnh
        else:
            img_list = note.get('imageList', [])
            for idx, img in enumerate(img_list):
                # Ưu tiên ảnh gốc
                url = img.get('urlOriginal') or img.get('urlDefault')
                if not url: 
                    # Fallback pattern
                    trace_id = img.get('traceId')
                    if trace_id: url = f"https://sns-img-bd.xhscdn.com/{trace_id}"

                if url:
                    if url.startswith('http:'): url = url.replace('http:', 'https:')
                    if url.startswith('//'): url = 'https:' + url
                    
                    files.append({
                        "type": "image", 
                        "url": url, 
                        "filename": f"RedNote_{note_id}_{idx+1}.jpg"
                    })

        return {
            "success": True,
            "data": {
                "id": note_id,
                "title": title,
                "author": {
                    "name": note.get('user', {}).get('nickname', 'Unknown'), 
                    "avatar": note.get('user', {}).get('avatar', '')
                },
                "files": files,
                "total": len(files),
                "source": source
            }
        }

def scrape_xhs(url, cookies=None):
    return XHSScraper(cookies).get_data(url)

