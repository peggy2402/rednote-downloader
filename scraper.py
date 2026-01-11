import requests
import re
import json
import random
import string
import time
from urllib.parse import urlparse, parse_qs, unquote

# Giả lập iPhone (Mobile) - Dễ bypass hơn Desktop
MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

def get_random_id(length=32):
    return ''.join(random.choices(string.hexdigits.lower(), k=length))

def resolve_short_link(url):
    if "xhslink.com" in url:
        try:
            resp = requests.head(url, allow_redirects=True, timeout=5)
            return resp.url
        except: return url
    return url

def get_headers(is_mobile=True, web_id=None, xsec_token=None):
    """Tạo headers linh hoạt cho Mobile hoặc Desktop"""
    cookies = {
        "webId": web_id,
        "a1": get_random_id(30),
    }
    if xsec_token: cookies["xsec_token"] = xsec_token

    headers = {
        "User-Agent": MOBILE_UA if is_mobile else DESKTOP_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    return headers, cookies

def extract_from_html(html):
    """Hàm tách dữ liệu dùng chung cho cả JSON và Regex"""
    result = None
    
    # 1. Thử lấy JSON __INITIAL_STATE__
    data_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
    if data_match:
        try:
            json_str = data_match.group(1).replace('undefined', 'null')
            data = json.loads(json_str)
            note_base = data.get('note', {})
            note_data = note_base.get('noteDetailMap', {}).get(list(note_base.get('noteDetailMap', {}).keys())[0]) if note_base.get('noteDetailMap') else note_base.get('note')
            
            if note_data:
                # Parse chuẩn từ JSON
                res = {
                    "title": note_data.get('title', 'No Title'),
                    "author": note_data.get('user', {}).get('nickname', 'Unknown'),
                    "avatar": note_data.get('user', {}).get('avatar', ''),
                    "type": note_data.get('type', 'unknown'),
                }
                if res['type'] == 'video':
                    res['download_url'] = note_data.get('video', {}).get('media', {}).get('stream', {}).get('h264', [{}])[0].get('masterUrl', '')
                    res['cover'] = note_data.get('imageList', [{}])[0].get('urlDefault', '')
                else:
                    res['images'] = [
                        img.get('infoList')[-1].get('url', img.get('urlDefault')) 
                        for img in note_data.get('imageList', [])
                        if img.get('urlDefault')
                    ]
                    res['cover'] = res['images'][0] if res['images'] else ''
                return res
        except: pass

    # 2. Fallback Regex (Quét thẻ Meta - Quan trọng cho Mobile)
    print("Trying Regex Fallback...")
    
    # Tìm Title
    title = re.search(r'<meta name="og:title" content="(.*?)">', html)
    if not title: title = re.search(r'<title>(.*?)</title>', html)
    
    # Tìm Author (Mobile thường có json user ẩn)
    author = re.search(r'"nickname":"(.*?)"', html)
    avatar = re.search(r'"avatar":"(.*?)"', html)

    # Tìm Video
    video_url = re.search(r'"masterUrl":"(http[^"]+?)"', html)
    if not video_url: video_url = re.search(r'<meta name="og:video" content="(.*?)">', html)
    
    # Tìm Ảnh
    img_matches = re.findall(r'"urlDefault":"(http[^"]+?)"', html)
    if not img_matches: 
        # Tìm trong thẻ meta og:image (thường chỉ lấy được 1 ảnh cover)
        og_img = re.search(r'<meta name="og:image" content="(.*?)">', html)
        if og_img: img_matches = [og_img.group(1)]

    if video_url or img_matches:
        res = {
            "title": title.group(1) if title else "Xiaohongshu Post",
            "author": author.group(1) if author else "Xiaohongshu User",
            "avatar": avatar.group(1) if avatar else "",
            "type": "video" if video_url else "normal"
        }
        
        if video_url:
            res['download_url'] = video_url.group(1).replace(r'\u002F', '/')
            res['cover'] = ""
        else:
            res['images'] = list(set([img.replace(r'\u002F', '/') for img in img_matches]))
            res['cover'] = res['images'][0]
        return res
        
    return None

def parse_rednote_url(input_url):
    try:
        real_url = resolve_short_link(input_url)
        parsed = urlparse(real_url)
        xsec_token = parse_qs(parsed.query).get('xsec_token', [None])[0]
        web_id = get_random_id()
        
        # --- CHIẾN LƯỢC 1: MOBILE (Ưu tiên) ---
        print("Attempt 1: Mobile User-Agent...")
        headers_mob, cookies_mob = get_headers(is_mobile=True, web_id=web_id, xsec_token=xsec_token)
        session = requests.Session()
        resp_mob = session.get(real_url, headers=headers_mob, cookies=cookies_mob, timeout=10)
        
        result = extract_from_html(resp_mob.text)
        if result: return result

        # --- CHIẾN LƯỢC 2: DESKTOP (Fallback) ---
        print("Attempt 2: Desktop User-Agent...")
        headers_desk, cookies_desk = get_headers(is_mobile=False, web_id=web_id, xsec_token=xsec_token)
        resp_desk = session.get(real_url, headers=headers_desk, cookies=cookies_desk, timeout=10)
        
        result = extract_from_html(resp_desk.text)
        if result: return result

        return {"error": "Không thể lấy dữ liệu (Captcha quá mạnh). Vui lòng thử lại sau vài phút."}

    except Exception as e:
        return {"error": f"System Error: {str(e)}"}