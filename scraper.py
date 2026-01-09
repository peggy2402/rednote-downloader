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
    Tìm URL video trực tiếp từ Xiaohongshu bằng cách gọi API XHS.
    """
    # Extract post ID từ URL
    # Format: https://www.xiaohongshu.com/explore/[POST_ID]?...
    post_id = None
    
    # Cách 1: Từ /explore/ path
    explore_match = re.search(r'/explore/([a-zA-Z0-9]+)', url)
    if explore_match:
        post_id = explore_match.group(1)
    
    # Cách 2: Từ /user/[USER_ID]/[POST_ID] 
    if not post_id:
        user_match = re.search(r'/user/[a-zA-Z0-9]+/([a-zA-Z0-9]+)', url)
        if user_match:
            post_id = user_match.group(1)
    
    if not post_id:
        return {'error': 'Không thể extract ID từ URL.'}
    
    # Gọi XHS API để lấy dữ liệu post
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://www.xiaohongshu.com',
        'Referer': 'https://www.xiaohongshu.com/',
    }
    
    try:
        # API endpoint để lấy chi tiết post
        api_url = 'https://edith.xiaohongshu.com/api/sns/web/v1/feed'
        
        payload = {
            'cursor_score': '',
            'num': 1,
            'refresh_type': 1,
            'note_index': 0,
            'unread_begin_note_id': '',
            'unread_end_note_id': '',
            'unread_note_count': 0,
            'category': 'explore'
        }
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        # Thử tìm post trong response
        items = data.get('data', {}).get('items', [])
        
        if not items:
            # Fallback: gọi API khác
            return fetch_from_web_page(url)
        
        for item in items:
            interact = item.get('interact_info', {})
            note = interact.get('note_card', {})
            
            if note.get('note_id') == post_id or note.get('interact_id') == post_id:
                return extract_media_from_note(note)
        
        # Nếu không tìm được trong feed, thử parse HTML
        return fetch_from_web_page(url)
        
    except Exception as e:
        # Fallback: parse HTML
        return fetch_from_web_page(url)


def fetch_from_web_page(url):
    """
    Fallback: parse HTML page trực tiếp để lấy ảnh/video
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
        
        # 1) Tìm link video trực tiếp
        video_pattern = r'https?://sns-video[^\s<>"\']+\.mp4'
        video_matches = re.findall(video_pattern, html_content, re.IGNORECASE)
        
        if video_matches:
            chosen = video_matches[0]
            for v in video_matches:
                if '_258.' in v or '_720' in v or '_1080' in v:
                    chosen = v
                    break
            return {
                'type': 'video',
                'media_url': chosen,
                'view_url': chosen,
                'title': 'Xiaohongshu Video'
            }
        
        # 2) Tìm ảnh từ script tags (dữ liệu JSON embed)
        images_found = []
        
        # Pattern để tìm image URLs (sns-webpic)
        img_pattern = r'https?://[a-z0-9-]*\.(?:xhscdn\.com|xiaohongshu\.com)/[^\s<>"\']*?\.(?:jpg|jpeg|png|webp|heic|heif)'
        
        # Tìm trong tất cả script tags
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                try:
                    img_matches = re.findall(img_pattern, script.string, re.IGNORECASE)
                    images_found.extend(img_matches)
                    
                    # Thử parse JSON để lấy thêm dữ liệu
                    try:
                        # Tìm JSON object trong script
                        json_match = re.search(r'\{.*?"image".*?\}', script.string, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(0)
                            # Extract URLs từ JSON
                            json_urls = re.findall(img_pattern, json_str, re.IGNORECASE)
                            images_found.extend(json_urls)
                    except:
                        pass
                except:
                    pass
        
        # 3) Tìm img tags
        for img_tag in soup.find_all('img'):
            src = img_tag.get('src', '')
            if 'xhscdn' in src or 'xiaohongshu' in src:
                if src not in images_found:
                    images_found.append(src)
        
        # 4) Tìm picture > source tags
        for pic in soup.find_all('picture'):
            for source in pic.find_all('source'):
                srcset = source.get('srcset', '')
                if 'xhscdn' in srcset or 'xiaohongshu' in srcset:
                    # Extract URLs từ srcset
                    urls = re.findall(r'https?://[^\s]+', srcset)
                    images_found.extend(urls)
        
        # Loại bỏ trùng lặp và filter
        unique_imgs = []
        for img in images_found:
            # Lọc URL hợp lệ
            if img and len(img) > 20 and 'xhscdn' in img and not img.endswith('!'):
                # Remove query params và fragments
                clean_url = img.split('?')[0].split('#')[0]
                if clean_url not in unique_imgs:
                    unique_imgs.append(clean_url)
        
        if unique_imgs:
            unique_imgs = unique_imgs[:20]
            page_title = soup.title.string.strip() if soup.title and soup.title.string else 'Xiaohongshu Images'
            logger.info(f"✓ Tìm thấy {len(unique_imgs)} ảnh từ scripts")
            return {
                'type': 'image',
                'media_urls': unique_imgs,
                'title': page_title,
                'count': len(unique_imgs)
            }
        
        # 5) Tìm og:image
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return {
                'type': 'image',
                'media_urls': [og_image.get('content')],
                'title': soup.title.string.strip() if soup.title and soup.title.string else 'Xiaohongshu Image',
                'count': 1
            }
        
        # 6) Last resort: find any image-like URLs in HTML
        all_urls = re.findall(r'https?://[^\s<>"\']+\.(?:jpg|jpeg|png|webp|heic|heif)', html_content, re.IGNORECASE)
        if all_urls:
            unique_imgs = list(dict.fromkeys(all_urls))[:20]  # Remove duplicates
            return {
                'type': 'image',
                'media_urls': unique_imgs,
                'title': soup.title.string.strip() if soup.title and soup.title.string else 'Xiaohongshu Images',
                'count': len(unique_imgs)
            }
        
        return {'error': 'Không tìm thấy media (video hoặc ảnh) trong trang.'}
    
    except requests.exceptions.RequestException as e:
        return {'error': f'Lỗi kết nối: {str(e)[:100]}'}
    except Exception as e:
        return {'error': f'Lỗi xử lý: {str(e)[:100]}'}


def extract_media_from_note(note):
    """
    Extract media URLs từ note object của XHS API
    """
    try:
        # Thử lấy ảnh từ interact_interact
        image_list = note.get('image_list', [])
        if image_list:
            images = []
            for img in image_list:
                img_url = img.get('url')
                if img_url:
                    images.append(img_url)
            
            if images:
                return {
                    'type': 'image',
                    'media_urls': images,
                    'title': note.get('title', 'Xiaohongshu Images'),
                    'count': len(images)
                }
        
        # Thử lấy video
        video = note.get('video')
        if video:
            video_url = video.get('url')
            if video_url:
                return {
                    'type': 'video',
                    'media_url': video_url,
                    'view_url': video_url,
                    'title': note.get('title', 'Xiaohongshu Video')
                }
        
        return {'error': 'Không tìm thấy media trong post.'}
    except Exception as e:
        return {'error': f'Lỗi parse media: {e}'}