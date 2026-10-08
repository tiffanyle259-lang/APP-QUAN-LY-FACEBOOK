# Kịch bản quay video cho Meta (khoảng 2 phút)

Meta yêu cầu video quay màn hình cho thấy ứng dụng dùng quyền như thế nào. Quay bằng điện thoại (ghi màn hình) hoặc máy tính (Windows: Win+G). Nên **thêm chữ tiếng Anh** hoặc đọc thuyết minh tiếng Anh ngắn, nếu không có thì giữ nguyên tiếng Việt cũng được vì người duyệt chủ yếu nhìn thao tác.

Dùng tài khoản **"Keo Dán Siêu Dính"** (có vai trò trong ứng dụng).

## Cảnh 1: Nhắn tin hỏi sản phẩm (pages_messaging)
1. Mở Messenger, vào Fanpage **KEO DÁN GIÀY**.
2. Gõ: `Keo nào dán mút sofa mà không hôi?` → gửi.
3. **Chờ bot trả lời** và để màn hình dừng 3 giây trên câu trả lời.
   *Chữ ghi chú: "The customer asks a product question; the assistant answers from our catalog."*

## Cảnh 2: Hỏi giá, bot chuyển nhân viên (pages_messaging)
1. Gõ: `Keo này giá bao nhiêu?` → bot xin số điện thoại.
2. Gõ: `Số của tôi 0912345678, cần 15kg` → bot xác nhận.
3. Mở **Google Sheet "Duyệt bài"**, tab **Khách hàng**, cho thấy dòng mới vừa ghi.
   *Chữ ghi chú: "For prices the assistant collects a phone number and our staff follows up."*

## Cảnh 3: Trả lời bình luận (pages_read_user_content, pages_manage_engagement)
1. Mở một bài đăng của Fanpage, bình luận: `Keo phun 339 giá bao nhiêu shop?`
2. Chờ bot trả lời công khai dưới bình luận, rồi mở Messenger cho thấy tin nhắn riêng bot vừa gửi.
   *Chữ ghi chú: "The assistant replies to the comment and continues in Messenger."*

## Cảnh 4: Chính sách quyền riêng tư và xóa dữ liệu
1. Mở trình duyệt, vào `https://hoanbao-bot.onrender.com/chinh-sach-rieng-tu` rồi cuộn xuống phần tiếng Anh.
2. Mở `https://hoanbao-bot.onrender.com/xoa-du-lieu`.
   *Chữ ghi chú: "Privacy policy and data deletion instructions."*

## Mẹo
- Quay dọc hoặc ngang đều được, nhưng chữ phải đọc rõ.
- Không để lộ khóa, token, mật khẩu trong video. Che Google Sheet nếu có số điện thoại thật.
- Chuẩn bị sẵn bình luận và các tin nhắn trước khi bấm quay để video gọn.
