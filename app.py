from flask import Flask, request, jsonify, render_template, send_file, Response, stream_with_context
from scraper import scrape_xhs
from dotenv import load_dotenv
import logging
import os
import requests
import io
import zipfile
import random
import time

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

env_cookie = os.getenv("XHS_COOKIE")
COOKIE_POOL = []
if env_cookie:
    if "|" in env_cookie:
        COOKIE_POOL = [c.strip() for c in env_cookie.split("|") if c.strip()]
    else:
        COOKIE_POOL.append(env_cookie)

# Header giả lập để vượt qua cơ chế chặn của XHS
def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Referer": "https://www.xiaohongshu.com/"
    }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    # ... (Giữ nguyên logic analyze cũ) ...
    data = request.get_json()
    raw_urls = data.get('urls', '').split('\n')
    user_provided_cookie = data.get('custom_cookie', '').strip()
    
    results = []
    errors = []

    for raw_url in raw_urls:
        if not raw_url.strip(): continue
        current_cookie = user_provided_cookie if user_provided_cookie else (random.choice(COOKIE_POOL) if COOKIE_POOL else None)
        try:
            result = scrape_xhs(raw_url, cookies=current_cookie)
            if result and result.get('success'):
                results.append(result['data'])
            else:
                msg = result.get('message', 'Unknown') if result else "No data"
                errors.append(f"{raw_url}: {msg}")
        except Exception as e:
            errors.append(f"Sys Error: {str(e)}")

    if not results:
        return jsonify({"success": False, "message": " | ".join(errors)}), 400

    return jsonify({"success": True, "data": results})

# --- API MỚI: PROXY CHO MOBILE ---
# Giúp Mobile tải file thông qua Server để tránh lỗi CORS và Force Download
@app.route('/api/proxy')
def proxy_file():
    url = request.args.get('url')
    filename = request.args.get('filename', 'file.jpg')
    
    if not url: return "Missing URL", 400

    try:
        # Stream content từ XHS về Client thông qua Server mình
        req = requests.get(url, headers=get_headers(), stream=True, timeout=20)
        
        return Response(
            stream_with_context(req.iter_content(chunk_size=1024)),
            content_type=req.headers['content-type'],
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        return f"Proxy Error: {e}", 500

# --- API UPDATE: ZIP CẢ VIDEO VÀ ẢNH ---
@app.route('/api/download-zip', methods=['POST'])
def download_zip():
    data = request.get_json()
    files = data.get('files', [])
    
    if not files: return jsonify({"error": "No files"}), 400

    # Sử dụng BytesIO để tạo file ZIP trong RAM
    mem_file = io.BytesIO()
    
    try:
        with zipfile.ZipFile(mem_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_info in files:
                url = file_info['url']
                # Đảm bảo tên file không bị lỗi ký tự lạ
                filename = file_info['filename']
                
                try:
                    # Tải file từ XHS (Stream để tiết kiệm RAM server với video nặng)
                    with requests.get(url, headers=get_headers(), stream=True, timeout=30) as r:
                        if r.status_code == 200:
                            # Đọc nội dung và ghi vào ZIP
                            zf.writestr(filename, r.content)
                        else:
                            logging.error(f"Failed to download {url}: {r.status_code}")
                except Exception as e:
                    logging.error(f"Error zipping {url}: {e}")
                    
        mem_file.seek(0)
        return send_file(
            mem_file, 
            mimetype='application/zip', 
            as_attachment=True, 
            download_name=f'RedNote_Batch_{int(time.time())}.zip'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)