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
    Hỗ trợ 3 loại URL:
    1. https://www.xiaohongshu.com/explore/[POST_ID]
    2. https://www.xiaohongshu.com/discovery/item/[POST_ID]
    3. http://xhslink.com/o/[SHORT_CODE] (short URL - need redirect)
    """
    import json
    
    # Normalize URL - handle short links
    if 'xhslink.com' in url:
        logger.info(f"Detected xhslink.com short URL, resolving...")
        try:
            # Follow redirect để lấy URL thực
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            url = response.url  # Lấy URL sau redirect
            logger.info(f"✓ Resolved to: {url}")
        except Exception as e:
            logger.warning(f"Failed to resolve short URL: {e}")
            return {'error': f'Không thể resolve URL ngắn: {e}'}
    
    post_id = None
    
    # Format 1: /explore/[POST_ID]
    explore_match = re.search(r'/explore/([a-zA-Z0-9]+)', url)
    if explore_match:
        post_id = explore_match.group(1)
        logger.info(f"Found /explore/ POST_ID: {post_id}")
    
    # Format 2: /discovery/item/[POST_ID]
    if not post_id:
        discovery_match = re.search(r'/discovery/item/([a-zA-Z0-9]+)', url)
        if discovery_match:
            post_id = discovery_match.group(1)
            logger.info(f"Found /discovery/item/ POST_ID: {post_id}")
    
    # Format 3: /user/[USER_ID]/[POST_ID]
    if not post_id:
        user_match = re.search(r'/user/[a-zA-Z0-9]+/([a-zA-Z0-9]+)', url)
        if user_match:
            post_id = user_match.group(1)
            logger.info(f"Found /user/ POST_ID: {post_id}")
    
    if not post_id:
        return {'error': 'Không thể extract ID từ URL. Vui lòng kiểm tra lại URL.'}
    
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
    Parse HTML page để lấy ảnh/video, đặc biệt cho ảnh carousel.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://www.xiaohongshu.com/',
        'Cookie': 'xsec_source=pc_feed'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html_content = response.text
        
        logger.info(f"✓ Đã fetch HTML, dung lượng: {len(html_content)} bytes")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 1) Tìm video (giữ nguyên)
        video_pattern = r'https?://sns-video[^\s<>"\']+\.mp4'
        video_matches = re.findall(video_pattern, html_content, re.IGNORECASE)
        if video_matches:
            chosen = max(video_matches, key=lambda x: ('_720' in x) or ('_1080' in x) or (x))
            return {
                'type': 'video',
                'media_url': chosen,
                'title': 'Xiaohongshu Video'
            }
        
        # 2) TÌM ẢNH CAROUSEL - PHƯƠNG PHÁP CHÍNH
        all_images = []
        
        # Pattern mới cho link ảnh Xiaohongshu (bao gồm cả carousel)
        # Pattern 1: Link có đuôi file thông thường
        img_pattern_ext = r'https?://[a-z0-9\-.]*\.?(xhscdn\.com|xiaohongshu\.com)[^\s<>"\']*\.(?:jpg|jpeg|png|webp|heic|heif|avif)[^\s<>"\']*'
        
        # Pattern 2: Link carousel không có đuôi (quan trọng!)
        # Khớp: https://.../notes_pre_post/...!nd_dft_wlteh_webp_3
        img_pattern_carousel = r'https?://[a-z0-9\-.]*\.?xhscdn\.com[^\s<>"\']*/notes_pre_post/[^\s<>"\']*!nd_dft_[^\s<>"\']*'
        
        # Pattern 3: Link với format mới hơn
        img_pattern_general = r'https?://sns-webpic[^\s<>"\']*\.xhscdn\.com[^\s<>"\']*'
        
        # Tìm trong toàn bộ HTML
        all_images.extend(re.findall(img_pattern_ext, html_content, re.IGNORECASE))
        all_images.extend(re.findall(img_pattern_carousel, html_content, re.IGNORECASE))
        all_images.extend(re.findall(img_pattern_general, html_content, re.IGNORECASE))
        
        # 3) Tìm trong các script tags chứa JSON data
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                content = script.string
                
                # Tìm window.__INITIAL_STATE__ (chứa dữ liệu chính)
                if 'window.__INITIAL_STATE__' in content:
                    try:
                        # Extract JSON
                        json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;', content, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(1)
                            json_data = json.loads(json_str)
                            
                            # Hàm đệ quy tìm URLs trong JSON
                            def extract_urls_from_json(obj):
                                urls = []
                                if isinstance(obj, dict):
                                    for key, value in obj.items():
                                        # Tìm các key liên quan đến ảnh
                                        if any(img_key in key.lower() for img_key in ['url', 'image', 'pic', 'src', 'cover']):
                                            if isinstance(value, str) and ('xhscdn.com' in value or 'xiaohongshu.com' in value):
                                                urls.append(value)
                                        else:
                                            urls.extend(extract_urls_from_json(value))
                                elif isinstance(obj, list):
                                    for item in obj:
                                        urls.extend(extract_urls_from_json(item))
                                return urls
                            
                            json_urls = extract_urls_from_json(json_data)
                            all_images.extend(json_urls)
                    except Exception as e:
                        logger.debug(f"Lỗi parse JSON từ __INITIAL_STATE__: {e}")
                
                # Tìm các object JSON khác
                try:
                    # Tìm pattern: "imageList": [...]
                    if 'imageList' in content or 'image_list' in content:
                        # Tìm tất cả URLs trong script
                        urls_in_script = re.findall(r'https?://[^\s<>"\']+\.xhscdn\.com[^\s<>"\']+', content, re.IGNORECASE)
                        all_images.extend(urls_in_script)
                except:
                    pass
        
        # 4) Tìm trong các thẻ meta và img
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            all_images.append(og_image.get('content'))
        
        for img in soup.find_all('img', src=True):
            src = img['src']
            if 'xhscdn.com' in src or 'xiaohongshu.com' in src:
                all_images.append(src)
        
        # 5) Lọc và làm sạch URLs
        unique_images = []
        for img in all_images:
            if not img or len(img) < 20:
                continue
            
            # Làm sạch URL
            clean_url = img.split('?')[0].split('#')[0].strip()
            
            # Chỉ lấy link từ domain Xiaohongshu
            if 'xhscdn.com' not in clean_url and 'xiaohongshu.com' not in clean_url:
                continue
            
            # Loại bỏ các link không phải ảnh (có thể tùy chỉnh)
            if any(ext in clean_url.lower() for ext in ['.js', '.css', '.html', '.php']):
                continue
            
            # Ưu tiên link carousel (/notes_pre_post/)
            if '/notes_pre_post/' in clean_url and clean_url not in unique_images:
                unique_images.insert(0, clean_url)  # Đưa lên đầu
            elif clean_url not in unique_images:
                unique_images.append(clean_url)
        
        # 6) Phân loại và trả kết quả
        if unique_images:
            # Lọc ra ảnh carousel (có /notes_pre_post/ và !nd_dft_)
            carousel_images = [img for img in unique_images 
                             if '/notes_pre_post/' in img and '!nd_dft_' in img]
            
            # Nếu có ảnh carousel, ưu tiên chúng
            if carousel_images:
                final_images = carousel_images[:20]  # Giới hạn số lượng
                logger.info(f"✓ Tìm thấy {len(carousel_images)} ảnh carousel")
            else:
                final_images = unique_images[:20]
                logger.info(f"✓ Tìm thấy {len(unique_images)} ảnh (không phải carousel)")
            
            title = soup.title.string.strip() if soup.title and soup.title.string else 'Xiaohongshu Images'
            
            return {
                'type': 'image',
                'media_urls': final_images,
                'title': title,
                'count': len(final_images),
                'is_carousel': len(carousel_images) > 0
            }
        
        return {'error': 'Không tìm thấy media (video hoặc ảnh) trong trang.'}
    
    except requests.exceptions.RequestException as e:
        return {'error': f'Lỗi kết nối: {str(e)}'}
    except Exception as e:
        logger.exception("Lỗi không xác định trong fetch_from_web_page")
        return {'error': f'Lỗi xử lý: {str(e)}'}


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