import re
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urlparse, parse_qs
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def parse_rednote_url(url):
    """
    Tìm URL media từ Xiaohongshu, ưu tiên dùng API.
    """
    import json
    post_id = None
    explore_match = re.search(r'/explore/([a-zA-Z0-9]+)', url)
    if explore_match:
        post_id = explore_match.group(1)
    
    if not post_id:
        user_match = re.search(r'/user/[a-zA-Z0-9]+/([a-zA-Z0-9]+)', url)
        if user_match:
            post_id = user_match.group(1)
    
    if not post_id:
        return {'error': 'Không thể extract ID từ URL.'}
    
    # THỬ CÁCH 1: Gọi API chi tiết note chính thức (nếu có)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': 'https://www.xiaohongshu.com/',
        'Origin': 'https://www.xiaohongshu.com',
        # Cookie có thể cần thiết, bạn có thể cần cập nhật nó thủ công nếu có
        'Cookie': 'xsec_source=pc_feed;'
    }
    
    try:
        # API endpoint chính thức để lấy chi tiết một note - ĐÂY LÀ ĐIỂM SỬA QUAN TRỌNG
        api_detail_url = f'https://edith.xiaohongshu.com/api/sns/web/v1/note/{post_id}'
        logger.info(f"Đang thử gọi API: {api_detail_url}")
        
        response = requests.get(api_detail_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Debug: Log cấu trúc dữ liệu trả về
        logger.debug(f"API response keys: {data.keys() if isinstance(data, dict) else 'not dict'}")
        
        # Đường dẫn dữ liệu có thể thay đổi, cần kiểm tra kỹ
        note_data = data.get('data', {}).get('items', [{}])[0] if data.get('data', {}).get('items') else data.get('data', {})
        if note_data:
            result = extract_media_from_note(note_data)
            if not result.get('error'):
                return result
    except Exception as e:
        logger.warning(f"API chi tiết thất bại, chuyển sang parse HTML: {e}")
    
    # THỬ CÁCH 2: Parse HTML trang (fallback)
    return fetch_from_web_page(url)


def fetch_from_web_page(url):
    """
    Parse HTML page để lấy ảnh/video.
    Tối ưu để tìm dữ liệu JSON ẩn.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://www.xiaohongshu.com/',  # QUAN TRỌNG
        'Cookie': 'xsec_source=pc_feed',
        'Origin': 'https://www.xiaohongshu.com',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html_content = response.text
        
        # Trích xuất token từ URL nếu có
        token = None
        token_match = re.search(r'xsec_token=([^&]+)', url)
        if token_match:
            token = token_match.group(1)

        # THỬ CÁCH A: Tìm video trực tiếp
        video_pattern = r'https?://sns-video[^\s<>"\']+\.mp4'
        video_matches = re.findall(video_pattern, html_content, re.IGNORECASE)
        if video_matches:
            quality_order = ['_1080', '_720', '_480', '_360', '_258']
            chosen = video_matches[0]
            for quality in quality_order:
                for v in video_matches:
                    if quality in v:
                        chosen = v
                        break
                if chosen != video_matches[0]:
                    break

            result = {
                'type': 'video',
                'media_url': chosen,
                'view_url': chosen,
                'origin_url': url,  # Thêm URL gốc
                'title': 'Xiaohongshu Video'
            }

            if token:
                result['token'] = token
                
            return result
        
        # THỬ CÁCH B: Parse kỹ các thẻ <script> để tìm JSON chứa ảnh
        soup = BeautifulSoup(html_content, 'html.parser')
        all_images = []
        
        # Pattern cho link ảnh Xiaohongshu (đã mở rộng)
        img_pattern = r'(https?://[a-z0-9\-.]*\.?(xhscdn\.com|xiaohongshu\.com)[^\s<>"\']*\.(?:jpg|jpeg|png|webp|heic|heif|avif))'
        
        # Tìm trong TẤT CẢ script tags
        for script in soup.find_all('script'):
            if script.string:
                content = script.string
                # Tìm các object JSON lớn (thường chứa dữ liệu note)
                json_matches = re.findall(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;', content, re.DOTALL)
                for json_str in json_matches:
                    try:
                        json_data = json.loads(json_str)
                        # Dùng hàm đệ quy để tìm tất cả URL ảnh trong JSON
                        def extract_urls_from_json(obj):
                            urls = []
                            if isinstance(obj, dict):
                                for key, value in obj.items():
                                    if isinstance(value, str) and re.match(img_pattern, value, re.IGNORECASE):
                                        urls.append(value)
                                    else:
                                        urls.extend(extract_urls_from_json(value))
                            elif isinstance(obj, list):
                                for item in obj:
                                    urls.extend(extract_urls_from_json(item))
                            return urls
                        
                        found_urls = extract_urls_from_json(json_data)
                        all_images.extend(found_urls)
                    except json.JSONDecodeError:
                        pass
                
                # Vẫn tìm bằng regex trực tiếp trong script như cũ
                found = re.findall(img_pattern, content, re.IGNORECASE)
                all_images.extend(found)
        
        # THỬ CÁCH C: Tìm trong thẻ meta và img thông thường
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            all_images.append(og_image.get('content'))
        
        for img in soup.find_all('img', src=True):
            src = img['src']
            if 'xhscdn' in src or 'xiaohongshu' in src:
                all_images.append(src)
        
        # Lọc và làm sạch URLs
        unique_images = []
        for img in all_images:
            clean = img.split('?')[0].split('#')[0]
            if clean not in unique_images and 'xhscdn' in clean:
                unique_images.append(clean)
        
        if unique_images:
            title_elem = soup.find('title')
            title = title_elem.text.strip() if title_elem else 'Xiaohongshu Images'
            return {
                'type': 'image',
                'media_urls': unique_images[:30],  # Giới hạn số lượng
                'title': title,
                'count': len(unique_images[:30])
            }
        
        return {'error': 'Không tìm thấy media (video hoặc ảnh) trong trang.'}
    
    except requests.exceptions.RequestException as e:
        return {'error': f'Lỗi kết nối: {str(e)}'}
    except Exception as e:
        logger.exception(f"Lỗi fetch_from_web_page: {e}")
        return {'error': f'Lỗi xử lý: {str(e)[:100]}'}


def extract_media_from_note(note):
    """
    Extract media URLs từ note object của XHS API.
    CẬP NHẬT: Điều chỉnh theo cấu trúc dữ liệu API thực tế.
    """
    try:
        images = []
        
        # Thử các đường dẫn dữ liệu có thể có
        # 1. Từ image_list cũ
        image_list = note.get('image_list', [])
        # 2. Từ imageList mới
        if not image_list:
            image_list = note.get('imageList', [])
        # 3. Từ note_detail -> imageList
        if not image_list and 'note_detail' in note:
            image_list = note['note_detail'].get('imageList', [])
        
        for img in image_list:
            # Hỗ trợ nhiều format trả về
            url = img.get('url') or img.get('original') or img.get('info', {}).get('url')
            if url and isinstance(url, str):
                # Đảm bảo URL đầy đủ
                if url.startswith('//'):
                    url = 'https:' + url
                elif url.startswith('/'):
                    url = 'https://www.xiaohongshu.com' + url
                images.append(url)
        
        # Tìm video
        video_info = note.get('video', {}) or note.get('video_info', {})
        video_url = video_info.get('url') or video_info.get('video_url')
        if video_url and isinstance(video_url, str):
            if video_url.startswith('//'):
                video_url = 'https:' + video_url
            return {
                'type': 'video',
                'media_url': video_url,
                'title': note.get('title', 'Xiaohongshu Video')
            }
        
        if images:
            return {
                'type': 'image',
                'media_urls': images,
                'title': note.get('title', 'Xiaohongshu Images'),
                'count': len(images)
            }
        
        return {'error': 'Không tìm thấy media trong post.'}
        
    except Exception as e:
        logger.error(f"Lỗi extract_media_from_note: {e}")
        return {'error': f'Lỗi parse media: {e}'}