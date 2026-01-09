from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import sys
import os
sys.path.append(os.path.dirname(__file__))
from scraper import parse_rednote_url, fetch_from_web_page  # Your custom logic
from flask import Response, stream_with_context
import requests
from urllib.parse import urlparse, unquote, quote

app = Flask(__name__)

# Route for the main page
@app.route('/')
def index():
    return render_template('index.html')

# API endpoint to handle download requests
@app.route('/api/download', methods=['POST'])
def api_download():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    try:
        # This function needs to be implemented in scraper.py
        result = parse_rednote_url(url)
        # `parse_rednote_url` returns a dict. If it contains 'error', return a failure response.
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'success': False, 'error': result.get('error')}), 404
        if result:
            return jsonify({'success': True, 'data': result})
        return jsonify({'success': False, 'error': 'Could not process the link'}), 404
    except Exception as e:
        # Log the error for debugging
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

# Thêm endpoint proxy cho video stream
@app.route('/video_stream')
def video_stream():
    """
    Proxy stream video với headers phù hợp để bypass 403
    """
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({'error': 'Missing video URL'}), 400
    
    # Chỉ chấp nhận URL từ xhscdn.com
    if 'xhscdn.com' not in video_url:
        return jsonify({'error': 'Invalid video domain'}), 400
    
    try:
        # Headers mô phỏng trình duyệt từ Xiaohongshu
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.xiaohongshu.com/',
            'Origin': 'https://www.xiaohongshu.com',
            'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Range': request.headers.get('Range', 'bytes=0-'),  # Hỗ trợ seek video
            'Cookie': f'xsec_source=pc_feed; xsec_token={quote(request.args.get("token", ""))}'
        }
        
        # Thêm token nếu có
        token = request.args.get('token')
        if token:
            headers['xsec_token'] = token
        
        # Gửi request với stream
        r = requests.get(video_url, headers=headers, stream=True, timeout=30)
        r.raise_for_status()
        
        # Trả về response với headers phù hợp
        response_headers = dict(r.headers)
        
        # Loại bỏ headers không cần thiết từ upstream
        unwanted_headers = ['Transfer-Encoding', 'Content-Encoding', 'Connection']
        for h in unwanted_headers:
            response_headers.pop(h, None)
        
        # Đảm bảo Content-Type đúng
        if 'Content-Type' not in response_headers:
            response_headers['Content-Type'] = 'video/mp4'
        
        # Hỗ trợ CORS cho video stream
        response_headers['Access-Control-Allow-Origin'] = '*'
        response_headers['Access-Control-Allow-Headers'] = 'Range'
        response_headers['Access-Control-Expose-Headers'] = 'Content-Range, Content-Length'
        
        def generate():
            for chunk in r.iter_content(chunk_size=1024 * 512):  # 512KB chunks
                if chunk:
                    yield chunk
        
        return Response(
            stream_with_context(generate()),
            status=r.status_code,
            headers=response_headers,
            content_type=response_headers.get('Content-Type', 'video/mp4')
        )
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Video stream error: {str(e)}'}), 502
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500
# Simple proxy endpoint that streams a remote file so the browser treats it as a download from this server.
@app.route('/download')
def download_proxy():
    url = request.args.get('url')
    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400
    
    # Xác định loại nội dung
    is_video = 'sns-video' in url or '.mp4' in url
    is_image = any(ext in url for ext in ['.jpg', '.jpeg', '.png', '.webp', 'xhscdn', 'xiaohongshu']) or '/notes_pre_post/' in url
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.xiaohongshu.com/'  # QUAN TRỌNG: Thêm Referer
        }
        
        # Thêm token nếu có trong URL
        if 'xsec_token' in request.args:
            headers['Cookie'] = f'xsec_token={request.args.get("xsec_token")}'
        
        r = requests.get(url, headers=headers, stream=True, timeout=30)
        r.raise_for_status()
        
        # Xác định filename
        parsed = urlparse(url)
        filename = unquote(os.path.basename(parsed.path)) or 'download'
        
        # Nếu filename quá dài hoặc có ký tự đặc biệt, tạo filename mới
        if len(filename) > 50 or '!' in filename:
            import time
            timestamp = int(time.time())
            if is_video:
                filename = f'video_{timestamp}.mp4'
            else:
                # Kiểm tra content-type từ response
                content_type = r.headers.get('content-type', '')
                if 'webp' in content_type:
                    filename = f'image_{timestamp}.webp'
                elif 'png' in content_type:
                    filename = f'image_{timestamp}.png'
                else:
                    filename = f'image_{timestamp}.jpg'
        else:
            # Thêm extension nếu thiếu
            if is_video and not filename.endswith('.mp4'):
                filename += '.mp4'
            elif is_image and not any(filename.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                # Kiểm tra content-type
                content_type = r.headers.get('content-type', '')
                if 'webp' in content_type:
                    filename += '.webp'
                elif 'png' in content_type:
                    filename += '.png'
                else:
                    filename += '.jpg'
        
        def generate():
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        
        # Xác định content-type
        content_type = r.headers.get('content-type', 
            'video/mp4' if is_video else 
            'image/webp' if is_image else 
            'application/octet-stream')
        
        resp = Response(stream_with_context(generate()), content_type=content_type)
        
        # Chỉ đặt attachment cho download, không phải stream
        resp.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return resp
        
    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'error': f'Error fetching file: {e}'}), 502


# Debug endpoint - xem scraper lấy được gì
@app.route('/debug-scraper')
def debug_scraper():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Missing URL parameter'}), 400
    
    try:
        # Fetch và parse HTML
        import re
        from bs4 import BeautifulSoup
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://www.xiaohongshu.com/'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        html = response.text
        
        # Tìm ảnh
        img_pattern = r'https?://[a-z0-9-]*\.(?:xhscdn\.com|xiaohongshu\.com)/[^\s<>"\']*?\.(?:jpg|jpeg|png|webp)'
        imgs = re.findall(img_pattern, html, re.IGNORECASE)
        
        # Tìm video
        video_pattern = r'https?://sns-video[^\s<>"\']+\.mp4'
        videos = re.findall(video_pattern, html, re.IGNORECASE)
        
        return jsonify({
            'html_size': len(html),
            'images_found': len(imgs),
            'image_samples': imgs[:3],
            'videos_found': len(videos),
            'video_samples': videos[:2],
            'html_snippet': html[500:1000] if len(html) > 500 else html
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Endpoint để tải tất cả ảnh thành ZIP file
@app.route('/download-all', methods=['POST'])
def download_all():
    data = request.get_json()
    urls = data.get('urls', [])
    
    if not urls or len(urls) == 0:
        return jsonify({'error': 'No URLs provided'}), 400
    
    try:
        import io
        import zipfile
        from datetime import datetime
        
        # Tạo ZIP file trong memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.xiaohongshu.com/'
            }
            
            for idx, url in enumerate(urls, 1):
                try:
                    # Fetch image
                    resp = requests.get(url, headers=headers, timeout=10, stream=True)
                    resp.raise_for_status()
                    
                    # Xác định extension
                    content_type = resp.headers.get('content-type', '')
                    if 'webp' in content_type:
                        ext = 'webp'
                    elif 'png' in content_type:
                        ext = 'png'
                    else:
                        ext = 'jpg'
                    
                    # Tên file trong ZIP
                    filename = f'image_{idx:03d}.{ext}'
                    
                    # Thêm vào ZIP
                    zip_file.writestr(filename, resp.content)
                    
                except Exception as e:
                    # Skip ảnh lỗi
                    continue
        
        # Chuẩn bị response
        zip_buffer.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f'xiaohongshu_images_{timestamp}.zip'
        
        resp = Response(zip_buffer.getvalue(), 
                       content_type='application/zip')
        resp.headers['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        
        return resp
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Proxy endpoint để load ảnh từ XHS (bypass CORS + headers)
@app.route('/proxy-image')
def proxy_image():
    img_url = request.args.get('url')
    if not img_url:
        return jsonify({'error': 'Missing URL'}), 400
    
    # Basic security: chỉ cho phép URLs từ XHS
    if 'xhscdn.com' not in img_url and 'xiaohongshu.com' not in img_url:
        return jsonify({'error': 'Invalid image source'}), 403
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.xiaohongshu.com/',
            'Accept': 'image/webp,image/*,*/*;q=0.8'
        }
        
        response = requests.get(img_url, headers=headers, timeout=10, stream=True)
        response.raise_for_status()
        
        # Stream image data
        def generate():
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        
        resp = Response(stream_with_context(generate()), 
                       content_type=response.headers.get('content-type', 'image/jpeg'))
        resp.headers['Cache-Control'] = 'public, max-age=3600'
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
    except Exception as e:
        return jsonify({'error': str(e)}), 502


if __name__ == '__main__':
    app.run(debug=True)  # Set debug=False in production