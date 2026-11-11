# Link Manager (Flask)

## Cài đặt
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
```

## Chạy trên Windows CMD
```bat
set FLASK_SECRET_KEY=ChuoiBiMatDaiVaNgauNhien
python main.py
```
Mở:
- Trang quản trị: http://127.0.0.1:5000/admin
- Link người truy cập: http://127.0.0.1:5000/<ma-link>

## Ghi chú
- Tạo liên kết trong /admin; mã ví dụ `2cc1` sẽ tạo URL `/2cc1`.
- Các tham số tracking trên URL đầu vào được chuyển tiếp sang URL đích. Nếu URL đích đã có cùng tên tham số thì giá trị ở URL đích được giữ nguyên.
- `links.db` được tạo tự động.
- Trước khi đưa lên Internet, lưu ý trang /admin KHÔNG còn mật khẩu — chỉ chạy ở 127.0.0.1, đừng mở ra Internet; đặt FLASK_SECRET_KEY mạnh, bật HTTPS, và triển khai bằng máy chủ WSGI phù hợp. `app.run()` chỉ dành cho thử nghiệm cục bộ.
- Đây là ứng dụng Flask chạy trên máy chủ Python; Cloudflare Pages không chạy trực tiếp Flask. Có thể dùng VPS/hosting Python hoặc chuyển backend sang Cloudflare Workers + D1 nếu muốn triển khai thuần Cloudflare.
- Trang trung gian dùng nút “Tiếp tục” minh bạch, không giả danh CAPTCHA/Google reCAPTCHA.
