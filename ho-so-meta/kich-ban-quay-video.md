# Kịch bản quay video LẦN 2 cho Meta (khoảng 3 phút)

Meta từ chối lần 1 vì video thiếu: (1) toàn bộ quy trình **đăng nhập Meta**, (2) cảnh **người dùng cấp quyền**,
(3) **trải nghiệm toàn diện** khi dùng quyền, (4) **giao diện tiếng Anh + chú thích**. App đã có trang mới
`https://hoanbao-bot.onrender.com/ket-noi` (giao diện tiếng Anh) để quay đủ các cảnh này liền một mạch.

Quay màn hình máy tính (Windows: Win+G) ở **một lần quay liên tục**, dùng tài khoản **"Keo Dán Siêu Dính"** (có vai trò trên ứng dụng).
Trình duyệt đặt **ngôn ngữ Facebook = English (US)** trước khi quay (Facebook → Settings → Language). Chú thích bằng chữ tiếng Anh ghi sẵn bên dưới (chèn bằng CapCut/Clipchamp, hoặc đọc to).

## Cảnh 1 (CÁCH ĐƠN GIẢN, dùng trang Meta, không cần /ket-noi): Messenger → Cài đặt API Messenger
1. Vào developers.facebook.com → app Hoan Bao Marketing → **Messenger → Cài đặt API Messenger**. Dừng 3 giây ở mục "1. Đặt cấu hình webhook".
   *Chú thích: "Step 1: our server receives Page messages through this webhook."*
2. Mở mục **"2. Tạo mã truy cập"** → bấm **"Thêm trang" (Add Page)** → hộp thoại Meta: tiếp tục, **bấm "Chỉnh sửa cài đặt" để thấy từng quyền**, chọn Page Golden Lion, bấm Tiếp/Xong.
   *Chú thích: "The Page admin logs in with Meta and grants pages_show_list, pages_manage_metadata and pages_messaging."*
3. Quay về bảng Page: dòng Page hiện **"messages, messaging_postbacks và feed"** (đã đăng ký webhook).
   *Chú thích: "pages_manage_metadata: the Page is subscribed to our webhook."*
4. Sang Cảnh 2.

## Cảnh 1 (CÁCH DỰ PHÒNG, dùng trang của app): Đăng nhập Meta và cấp quyền (pages_show_list, pages_manage_metadata)
1. Đăng xuất Facebook trước khi quay để thấy cả màn hình đăng nhập.
2. Mở `https://hoanbao-bot.onrender.com/ket-noi`. Dừng 3 giây để người xem đọc danh sách quyền.
   *Chú thích: "Step 1: the Page admin opens our app and clicks Continue with Facebook."*
3. Bấm **Continue with Facebook** → màn hình đăng nhập Facebook → nhập tài khoản (che mật khẩu hoặc cắt khi gõ).
4. Màn hình hộp thoại cấp quyền hiện ra: **dừng 5 giây, bấm "Edit settings" để lộ từng quyền**, chọn đúng Page, rồi bấm **Continue/Done**.
   *Chú thích: "The admin grants the permissions the app requests and selects the Page."*
5. Trang "Step 2 · Choose a Page" hiện tên Page. Dừng 3 giây.
   *Chú thích: "pages_show_list: the app lists the Pages the admin manages."*
6. Bấm **Enable assistant for this Page** → trang "Assistant enabled" hiện.
   *Chú thích: "pages_manage_metadata: the app subscribes the Page to our webhook (messages and comments)."*

## Cảnh 2: Khách nhắn tin, trợ lý trả lời (pages_messaging, pages_read_engagement)
1. Mở Messenger (tab khác, tài khoản khách thử), vào Fanpage.
2. Gõ: `Which adhesive bonds sofa foam without a strong smell?` → gửi. Chờ trợ lý trả lời, dừng 3 giây.
   *Chú thích: "pages_messaging: the customer messages the Page and the assistant replies from our product catalog."*
3. Gõ: `How much does it cost?` → trợ lý xin số điện thoại (không báo giá). Gõ số điện thoại mẫu.
   *Chú thích: "For prices the assistant collects a phone number and our staff follows up. Staff can take over anytime."*
4. Mở **Google Sheet "Duyệt bài" → tab Khách hàng** (che số điện thoại thật) để thấy dòng mới.
   *Chú thích: "pages_read_engagement: the assistant reads the conversation to keep replies consistent."*

## Cảnh 3: Chính sách quyền riêng tư và xóa dữ liệu
1. Mở `https://hoanbao-bot.onrender.com/chinh-sach-rieng-tu` rồi `https://hoanbao-bot.onrender.com/xoa-du-lieu`.
   *Chú thích: "Privacy policy and data deletion instructions."*

## Khi nộp lại
- Trong ô ghi chú từng quyền, thêm câu: "Please start the video at /ket-noi: it shows the complete Meta Login flow, the permission grant, and the full use case. The app is server-to-server: customers message the Page; Page admins connect through /ket-noi."
- Nếu Meta hỏi mã người dùng hệ thống (câu 5 trong thông báo): ghi "The app is a server app; the Meta Login flow for the Page admin is shown at /ket-noi."
- Quyền bình luận (pages_read_user_content, pages_manage_engagement) xin sau, khi 3 quyền này đã được duyệt.

## Mẹo
- Không để lộ khóa, token, mật khẩu trong video. Che số điện thoại thật.
- Chuẩn bị sẵn tin nhắn trước khi bấm quay để video gọn.
