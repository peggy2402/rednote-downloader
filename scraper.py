import requests
import re
import json
import logging
import time
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("XHS_Scraper")

def extract_urls_from_text(text):
    """
    Tìm link http/https trong văn bản hỗn độn.
    Lọc bỏ các ký tự dính đuôi như dấu chấm, dấu phẩy, ngoặc...
    """
    raw_urls = re.findall(r'(https?://[^\s]+)', text)
    clean_urls = []
    for url in raw_urls:
        url = url.rstrip('.,;)]}”"\'')
        if 'xiaohongshu.com' in url or 'xhslink.com' in url:
            clean_urls.append(url.strip())
    return list(set(clean_urls))

class XHSScraper:
    def __init__(self, cookies=None):
        self.session = requests.Session()
        self.cookie = cookies if cookies else ""
        self.ua_desktop = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        # User-Agent Mobile mới nhất
        self.ua_mobile = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"

    def _get_headers(self, type="desktop"):
        headers = {
            "User-Agent": self.ua_mobile if type == "mobile" else self.ua_desktop,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Upgrade-Insecure-Requests": "1"
        }
        if self.cookie: headers["Cookie"] = self.cookie
        return headers

    def resolve_redirects(self, url: str) -> str:
        if "xhslink" not in url: return url
        logger.info(f"Resolving short link: {url}")
        try:
            res = self.session.get(url, headers=self._get_headers("mobile"), allow_redirects=False, timeout=10)
            if res.status_code in [301, 302, 307, 308]:
                location = res.headers.get('Location')
                if location: return location
            res = self.session.get(url, headers=self._get_headers("mobile"), allow_redirects=True, timeout=15)
            return res.url
        except Exception as e:
            logger.error(f"Redirect error: {e}")
            return url

    def extract_note_id(self, url: str) -> str:
        clean_url = url.split('?')[0]
        patterns = [r'/explore/([a-fA-F0-9]{24})', r'/discovery/item/([a-fA-F0-9]{24})', r'item/([a-fA-F0-9]{24})']
        
        for p in patterns:
            match = re.search(p, clean_url)
            if match: return match.group(1)
        for p in patterns: 
            match = re.search(p, url)
            if match: return match.group(1)
        return None

    def get_data(self, raw_url: str):
        real_url = self.resolve_redirects(raw_url.strip())
        if "xhslink" in real_url:
             try:
                res = self.session.get(raw_url, headers=self._get_headers("desktop"), allow_redirects=True, timeout=10)
                real_url = res.url
             except: pass

        note_id = self.extract_note_id(real_url)
        if not note_id: 
            return {"success": False, "message": f"Không tìm thấy ID. URL: {real_url}"}

        # 1. API Lib (Ưu tiên 1)
        try:
            from xhs import XhsClient
            if self.cookie:
                logger.info("Attempting Strategy: API Lib")
                client = XhsClient(cookie=self.cookie)
                note = client.get_note_by_id(note_id)
                if note: return self._format_response(note, "API Lib")
        except Exception as e: 
            logger.warning(f"Strategy API Lib failed: {e}")

        # 2. HTML Mobile (Ưu tiên 2)
        try:
            logger.info("Attempting Strategy: HTML Mobile")
            res = self.session.get(real_url, headers=self._get_headers("mobile"), timeout=10)
            data = self._parse_html_soup(res.text)
            if data: return data
        except Exception as e: logger.error(f"Mobile failed: {e}")

        # 3. HTML Desktop (Fallback)
        try:
            logger.info("Attempting Strategy: HTML Desktop")
            res = self.session.get(real_url, headers=self._get_headers("desktop"), timeout=10)
            data = self._parse_html_soup(res.text)
            if data: return data
        except Exception as e: logger.error(f"Desktop failed: {e}")
             
        return {"success": False, "message": "Không thể lấy dữ liệu. Hãy cập nhật Cookie mới!"}

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
                        note_data = state.get("note", {}).get("noteDetailMap", {})
                        target_note = None
                        if note_data:
                            first_val = next(iter(note_data.values()))
                            target_note = first_val.get("note", first_val)
                        else:
                            target_note = state.get("note", {}).get("note", {})

                        if target_note and target_note.get("noteId"):
                            return self._format_response(target_note, "HTML Soup")
                except: pass
        return None

    def _format_response(self, note, source):
        if not note: return None
        title = note.get('title', 'No Title')
        type_ = note.get('type', 'normal')
        note_id = note.get('noteId')
        files = []

        # --- LOGIC VIDEO NO WATERMARK (CẬP NHẬT MẠNH) ---
        if type_ == 'video':
            video_node = note.get('video', {})
            url = None

            # CHIẾN THUẬT 1: Lấy originVideoKey (Chuẩn nhất - Không logo)
            origin_key = video_node.get('consumer', {}).get('originVideoKey')
            if origin_key:
                url = f"https://sns-video-bd.xhscdn.com/{origin_key}"
                logger.info(f"Got Video via OriginKey: {origin_key}")

            # CHIẾN THUẬT 2: Fallback an toàn
            # Nếu không có originKey, ta dùng masterUrl GỐC.
            # TUYỆT ĐỐI KHÔNG cắt gọt tham số (?sign=...) vì sẽ làm hỏng link.
            if not url:
                master_url = video_node.get('masterUrl')
                # Nếu masterUrl rỗng, tìm trong h264
                if not master_url:
                    media = video_node.get('media', {})
                    stream = media.get('stream', {})
                    if stream.get('h264'):
                        master_url = stream['h264'][0].get('masterUrl')
                
                # Sử dụng link gốc để đảm bảo chạy được (dù có thể có watermark)
                url = master_url
                logger.info(f"Got Video via MasterURL Fallback: {url}")

            if url:
                 files.append({
                    "type": "video", 
                    "url": self._force_https(url), 
                    "cover": self._force_https(note.get('imageList', [{}])[0].get('urlDefault', '')),
                    "filename": f"RedNoteVid_{note_id}.mp4"
                })
        
        # --- LOGIC ẢNH NO WATERMARK ---
        else:
            for idx, img in enumerate(note.get('imageList', [])):
                url = None
                
                # 1. Thử lấy traceId (No Watermark)
                trace_id = img.get('traceId') or img.get('fileId')
                if trace_id:
                    url = f"https://sns-img-bd.xhscdn.com/{trace_id}"
                
                # 2. Fallback
                if not url: url = img.get('urlOriginal')
                if not url: url = img.get('urlDefault')

                if url:
                    files.append({
                        "type": "image", 
                        "url": self._force_https(url), 
                        "filename": f"RedNoteImg_{note_id}_{idx+1}.jpg"
                    })

        return {
            "success": True,
            "data": {
                "id": note_id,
                "title": title,
                "author": {
                    "name": note.get('user', {}).get('nickname', 'Unknown'), 
                    "avatar": self._force_https(note.get('user', {}).get('avatar', ''))
                },
                "files": files,
                "total": len(files),
                "source": source
            }
        }

    def _force_https(self, url):
        if not url: return ""
        if url.startswith("//"): return "https:" + url
        if url.startswith("http:"): return url.replace("http:", "https:")
        return url

def scrape_xhs(url, cookies=None):
    return XHSScraper(cookies).get_data(url)