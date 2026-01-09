from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import re
app = FastAPI()
# Thêm CORS để frontend gọi được
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.post("/api/extract")
async def extract_video(url_data: dict):
    xhs_url = url_data.get("url")
    user_cookie = url_data.get("cookie", "") # Lấy cookie từ frontend
    if not xhs_url:
        raise HTTPException(status_code=400, detail="Thiếu URL")
    try:
        # 1. Dùng Cookie (nếu có) để gửi request, giả lập trình duyệt
        headers = {
            'User-Agent': 'Mozilla/5.0...',
            'Cookie': user_cookie # Cookie là then chốt
        }
        response = requests.get(xhs_url, headers=headers)
        html_content = response.text
        # 2. TÌM KIẾM LOGIC THEN CHỐT: Trích xuất link video từ HTML hoặc dữ liệu JSON ẩn
        # Đây là phần bạn cần nghiên cứu sâu bằng DevTools của trình duyệt.
        # Ví dụ: Tìm kiếm sơ bộ các pattern có thể chứa link video
        video_urls = re.findall(r'"(https?://[^"]*\.mp4[^"]*)"', html_content)
        # 3. Làm sạch và trả về kết quả
        if video_urls:
            return {"success": True, "video_urls": video_urls[:3]} # Giới hạn số lượng
        else:
            # Nếu không tìm thấy, có thể dữ liệu nằm trong JSON blob
            # Cần thêm xử lý phức tạp hơn ở đây
            return {"success": False, "message": "Không tìm thấy link video. Thử với Cookie."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")