from flask import Flask, render_template, request, jsonify
import sys
import os
sys.path.append(os.path.dirname(__file__))
from scraper import parse_rednote_url, fetch_from_web_page  # Your custom logic
from flask import Response, stream_with_context
import requests
from urllib.parse import urlparse, unquote

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


# Simple proxy endpoint that streams a remote file so the browser treats it as a download from this server.
@app.route('/download')
def download_proxy():
    url = request.args.get('url')
    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    # Basic safety: only allow http(s)
    if not url.startswith('http://') and not url.startswith('https://'):
        return jsonify({'success': False, 'error': 'Invalid URL scheme'}), 400

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, stream=True, timeout=15)
        r.raise_for_status()

        # Try to determine filename from URL path
        parsed = urlparse(url)
        filename = unquote(os.path.basename(parsed.path)) or 'download'

        def generate():
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

        resp = Response(stream_with_context(generate()), content_type=r.headers.get('content-type', 'application/octet-stream'))
        resp.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return resp
    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'error': f'Error fetching remote file: {e}'}), 502


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


if __name__ == '__main__':
    app.run(debug=True)  # Set debug=False in production