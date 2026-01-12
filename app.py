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

# --- CẤU HÌNH LOGGING (FIX) ---
# Thêm force=True để đảm bảo ghi đè config mặc định của Flask
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("server.log", encoding='utf-8'),
        logging.StreamHandler()
    ],
    force=True 
)
logger = logging.getLogger("RedNote_App")

app = Flask(__name__)

# --- QUẢN LÝ COOKIE ---
env_cookie = os.getenv("XHS_COOKIE")
COOKIE_POOL = []

if env_cookie:
    if "|" in env_cookie:
        COOKIE_POOL = [c.strip() for c in env_cookie.split("|") if c.strip()]
    else:
        COOKIE_POOL.append(env_cookie)
    # Log ngay khi khởi động server
    logger.info(f"🚀 SERVER KHỞI ĐỘNG: Đã tải {len(COOKIE_POOL)} cookie vào hệ thống.")
else:
    logger.warning("⚠️ CẢNH BÁO: Không tìm thấy XHS_COOKIE trong file .env")

def get_random_cookie():
    if not COOKIE_POOL:
        logger.warning("COOKIE_POOL đang rỗng! Đang chạy chế độ Guest.")
        return None
    
    cookie = random.choice(COOKIE_POOL)
    # Masking cookie chỉ dùng khi log request thường để tránh rác log
    masked_cookie = cookie[:15] + "..." if len(cookie) > 15 else cookie
    logger.info(f"♻️  Đang sử dụng Cookie: {masked_cookie}")
    return cookie

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
    
    logger.info("-" * 30)
    logger.info(f"📩 Nhận request phân tích mới...")
    
    clean_urls = extract_urls_from_text(raw_text)
    
    if not clean_urls:
        logger.error("❌ Không tìm thấy link hợp lệ trong văn bản.")
        return jsonify({"success": False, "message": "Không tìm thấy link Xiaohongshu hợp lệ."}), 400

    results = []
    errors = []

    for url in clean_urls:
        current_cookie = get_random_cookie()
        
        try:
            logger.info(f"🚀 Bắt đầu Scrape: {url}")
            result = scrape_xhs(url, cookies=current_cookie)
            
            if result and result.get('success'):
                source = result['data'].get('source', 'Unknown')
                logger.info(f"✅ THÀNH CÔNG: {url} | Nguồn: {source}")
                results.append(result['data'])
            else:
                msg = result.get('message', 'Lỗi không xác định') if result else "No Data"
                logger.error(f"❌ THẤT BẠI: {url} | Lý do: {msg}")
                errors.append(f"{url}: {msg}")
                
        except Exception as e:
            logger.exception(f"🔥 Lỗi hệ thống nghiêm trọng với link {url}")
            errors.append(f"Lỗi hệ thống: {str(e)}")

    if not results:
        return jsonify({"success": False, "message": " | ".join(errors)}), 400

    return jsonify({
        "success": True, 
        "data": results,
        "debug_errors": errors 
    })

@app.route('/api/proxy')
def proxy_file():
    url = request.args.get('url')
    filename = request.args.get('filename', 'file.jpg')
    if not url: return "Missing URL", 400
    try:
        req = requests.get(url, headers=get_headers(), stream=True, timeout=20)
        return Response(
            stream_with_context(req.iter_content(chunk_size=4096)),
            content_type=req.headers.get('content-type', 'application/octet-stream'),
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Proxy Error: {e}")
        return f"Proxy Error: {e}", 500

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
                    with requests.get(url, headers=get_headers(), stream=True, timeout=15) as r:
                        if r.status_code == 200:
                            zf.writestr(filename, r.content)
                        else:
                            logger.error(f"Download fail: {r.status_code} - {url}")
                except Exception as e:
                    logger.error(f"Zip error: {e}")
        mem_file.seek(0)
        return send_file(mem_file, mimetype='application/zip', as_attachment=True, download_name=f'RedNote_Batch_{int(time.time())}.zip')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API MỚI: KIỂM TRA TRẠNG THÁI COOKIE (HIỂN THỊ FULL)
@app.route('/api/check-cookies', methods=['GET'])
def check_cookies():
    """API để bạn tự kiểm tra xem có bao nhiêu cookie đang hoạt động"""
    
    # GHI LOG ĐỂ KIỂM TRA
    logger.info(f"🔍 User đang kiểm tra Cookie. Tổng số: {len(COOKIE_POOL)}")
    
    return jsonify({
        "total_cookies": len(COOKIE_POOL),
        # Hiển thị cookie đã che bớt (để nhìn nhanh)
        "cookies_masked": [c[:20] + "..." for c in COOKIE_POOL],
        # Hiển thị TOÀN BỘ cookie (để bạn debug)
        "cookies_full": COOKIE_POOL,
        "status": "Active" if COOKIE_POOL else "No Cookies (Guest Mode)"
    })

if __name__ == '__main__':
    if not os.path.exists("server.log"):
        open("server.log", "w", encoding="utf-8").close()
    app.run(host='0.0.0.0', port=5000, debug=True)