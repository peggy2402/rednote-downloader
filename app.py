from flask import Flask, request, jsonify, render_template, send_file, Response, stream_with_context
from scraper import scrape_xhs, extract_urls_from_text
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

# --- QUẢN LÝ COOKIE ---
# Bạn nên lấy cookie từ trình duyệt (F12 -> Network -> request bất kỳ -> copy value cookie)
# Lưu vào file .env biến XHS_COOKIE. Nếu có nhiều cookie, cách nhau bằng dấu |
env_cookie = os.getenv("XHS_COOKIE")
COOKIE_POOL = []
if env_cookie:
    if "|" in env_cookie:
        COOKIE_POOL = [c.strip() for c in env_cookie.split("|") if c.strip()]
    else:
        COOKIE_POOL.append(env_cookie)

def get_random_cookie():
    if not COOKIE_POOL:
        return None
    return random.choice(COOKIE_POOL)

# Header giả lập
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
    data = request.get_json()
    raw_text = data.get('urls', '')
    
    # BƯỚC 1: TRÍCH XUẤT LINK TỪ VĂN BẢN HỖN ĐỘN
    # Người dùng có thể paste cả đoạn văn kèm link, hàm này sẽ lọc ra list link sạch
    clean_urls = extract_urls_from_text(raw_text)
    
    if not clean_urls:
        return jsonify({"success": False, "message": "Không tìm thấy link Xiaohongshu hợp lệ nào."}), 400

    results = []
    errors = []

    # BƯỚC 2: XỬ LÝ TỪNG LINK
    for url in clean_urls:
        # Sử dụng cookie của Server (ẩn danh với người dùng cuối)
        current_cookie = get_random_cookie()
        
        try:
            # Truyền url đã lọc vào scraper
            result = scrape_xhs(url, cookies=current_cookie)
            if result and result.get('success'):
                results.append(result['data'])
            else:
                msg = result.get('message', 'Lỗi không xác định') if result else "Không lấy được dữ liệu"
                errors.append(f"Link lỗi: {msg}")
        except Exception as e:
            logging.error(f"System Error for {url}: {e}")
            errors.append(f"Lỗi hệ thống khi xử lý link")

    if not results:
        # Nếu thất bại toàn bộ
        return jsonify({"success": False, "message": " | ".join(errors)}), 400

    # Trả về dù chỉ thành công 1 link, kèm theo danh sách lỗi (nếu có) để debug
    return jsonify({
        "success": True, 
        "data": results,
        "debug_errors": errors 
    })

# --- API PROXY (QUAN TRỌNG CHO MOBILE) ---
@app.route('/api/proxy')
def proxy_file():
    url = request.args.get('url')
    filename = request.args.get('filename', 'file.jpg')
    
    if not url: return "Missing URL", 400

    try:
        # Stream request để không tốn RAM server
        req = requests.get(url, headers=get_headers(), stream=True, timeout=20)
        
        # Chuyển tiếp stream xuống client
        return Response(
            stream_with_context(req.iter_content(chunk_size=4096)),
            content_type=req.headers.get('content-type', 'application/octet-stream'),
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        return f"Proxy Error: {e}", 500

# --- API DOWNLOAD ZIP (CHO PC) ---
@app.route('/api/download-zip', methods=['POST'])
def download_zip():
    data = request.get_json()
    files = data.get('files', [])
    
    if not files: return jsonify({"error": "No files"}), 400

    mem_file = io.BytesIO()
    
    try:
        with zipfile.ZipFile(mem_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_info in files:
                url = file_info['url']
                filename = file_info['filename']
                
                try:
                    # Timeout ngắn hơn để tránh treo server lâu
                    with requests.get(url, headers=get_headers(), stream=True, timeout=15) as r:
                        if r.status_code == 200:
                            zf.writestr(filename, r.content)
                        else:
                            logging.error(f"Download fail: {r.status_code} - {url}")
                except Exception as e:
                    logging.error(f"Zip error: {e}")
                    
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