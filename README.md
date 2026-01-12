# RedNote Downloader – Xiaohongshu (Tiểu Hồng Thư) Downloader

Ứng dụng web giúp tải xuống hình ảnh và video từ Xiaohongshu (RedNote) **không có watermark (logo chìm)**. Hỗ trợ tự động xử lý link rút gọn, link chứa văn bản hỗn độn và tải hàng loạt.

---

## 🚀 Tính năng chính

- **Tự động lọc link**  
  Chỉ cần copy toàn bộ nội dung chia sẻ (bao gồm cả tiêu đề, icon, link rút gọn `xhslink.com`), hệ thống sẽ tự động tách và lấy link chuẩn.

- **No Watermark**  
  Tải video và hình ảnh gốc với chất lượng cao nhất, không dính logo.

- **Đa nền tảng**

  - **PC**: Hỗ trợ gom tất cả ảnh/video vào một file ZIP để tải nhanh.
  - **Mobile (iOS/Android)**: Hỗ trợ cơ chế Proxy Stream để tải trực tiếp vào thư viện ảnh (giúp vượt qua lỗi chặn download của trình duyệt mobile).

- **Giao diện thân thiện**  
  Xem trước ảnh/video dạng slide trượt mượt mà, dễ sử dụng.

---

## 🛠 Hướng dẫn cài đặt tiện ích Get Cookies

### 1. Truy cập vào trình duyệt

### 2. Nhấn vào 3 chấm dọc (hoặc ngang nếu sử dụng Edge)

### 3. Chọn `Cài đặt (Settings)` => Chọn `Tiện ích (Extensions)`

### 4. Bật `Chế độ cho nhà phát triển (Developer mode)`

### 5. - Nếu dùng `Microsoft Edge` thì chọn `Pack extension`

       - Nếu dùng `Chrome` thì chọn `Tải tiện ích đã giải nén`

### 6. Cuối dùng chọn folder `xhs_cookie` là xong

> Còn nếu không muốn thì làm như `Bước 2: Lấy Cookie từ trình duyệt`

## 🛠 Cài đặt & Chạy

### 1. Yêu cầu hệ thống

- Python 3.8 trở lên
- Git (tùy chọn)

### 2. Cài đặt thư viện

Chạy lệnh sau trong terminal để cài các thư viện cần thiết:

```bash
pip install -r requirements.txt
```

### 3. Cấu hình Cookie (Quan trọng)

Xiaohongshu yêu cầu **Cookie** để việc tải dữ liệu được ổn định.

#### Bước 1: Tạo file `.env`

Tạo file `.env` ở thư mục gốc của dự án.
Hoặc gõ lệnh:

```bash
cp .env.example .env
```

#### Bước 2: Lấy Cookie từ trình duyệt

1. Truy cập https://www.xiaohongshu.com và đăng nhập
2. Nhấn `F12` (Developer Tools) → chuyển sang tab **Network**
3. Refresh trang (`F5`)
4. Chọn `Fetch/XHR` và Tích vào ô `Preserve log`
5. Tìm request tên `webprofile` ở phần Filter
6. Trong phần **Request Headers**, copy toàn bộ giá trị của **Cookie**

#### Bước 3: Dán vào file `.env`

Ví dụ:

```env
XHS_COOKIE=abRequestId=xxxxxx; web_session=xxxxxxx; a1=xxxxxx; ...
```

Nếu bạn có nhiều Cookie dự phòng, hãy ngăn cách chúng bằng dấu gạch đứng `|`:

```env
XHS_COOKIE=cookie_tk_1|cookie_tk_2|cookie_tk_3
```

---

### 4. Chạy ứng dụng

```bash
python app.py
```

Mở trình duyệt và truy cập:

```
http://127.0.0.1:5000
```

---

## 📂 Cấu trúc thư mục

```
RedNote-Downloader/
├── static/
│   ├── css/
│   │   └── style.css        # Tailwind config & Custom CSS
│   └── js/
│       └── main.js          # Logic Frontend (xử lý UI, gọi API)
├── templates/
│   └── index.html           # Giao diện chính
├── app.py                   # Backend Flask API
├── scraper.py               # Logic cào dữ liệu (Core)
├── requirements.txt         # Danh sách thư viện
└── README.md                # Hướng dẫn sử dụng
```

---

## 📝 Lưu ý sử dụng

- Link dạng `http://xhslink.com/...` sẽ được hệ thống tự động giải mã.
- Các dạng link rút gọn sẽ khó khăn có thể bị lỗi
- Trên iPhone (iOS), khi bấm **"Tải Tất Cả"**, hệ thống sẽ bật nhiều popup tải xuống lần lượt → vui lòng cho phép trình duyệt tải file.

---

> Dự án vẫn đang được **UPDATE** ... Nếu bạn thấy dự án hữu ích, hãy ⭐ star repo để ủng hộ nhé!
> Source code by peggy2402 !
