# Hướng dẫn vận hành hệ thống Golden Lion

Tài liệu cho người phụ trách kỹ thuật. **Không ghi mật khẩu hay khóa ở đây.** Khóa nằm trong GitHub Secrets và biến môi trường Render.

## 1. Hệ thống làm gì

| Phần | Việc | Chạy ở đâu |
|---|---|---|
| Đăng bài Fanpage | AI viết bài cả tuần từ file Excel, chọn ảnh/video từ Google Drive, ghi vào Google Sheet; bài "Duyệt" được hẹn giờ trên Facebook | GitHub Actions |
| YouTube | Bài có video được tải lên YouTube, hẹn công khai đúng giờ Facebook | GitHub Actions (cùng bước lên lịch) |
| Chatbot | Trả lời tin nhắn Messenger, ghi khách vào Sheet, báo email | Máy chủ Render (`hoanbao-bot`) |
| Bảng điều khiển | Xem bài, khách, tin nhắn, nhóm, báo cáo; duyệt/sửa bài, đổi ảnh, hủy lịch | Máy chủ Render, đường `/bang-dieu-khien` |
| Báo cáo tuần | Số liệu tương tác 7 ngày, lưu tab "Báo cáo tuần" | GitHub Actions |
| Quảng cáo Facebook | Chạy trong Ads Manager (làm tay). Khách quảng cáo nhập bằng file CSV vào tab "Khách hàng" | Meta + GitHub Actions |
| Tab Nhóm | Danh sách nhóm Facebook để nhân viên đăng tay | Google Sheet + bảng điều khiển |

Meta không cho đăng nhóm hoặc trang cá nhân bằng API. Nhóm và chia sẻ trang cá nhân do người làm tay.

## 2. Các thành phần và nơi cất

- **Mã nguồn:** GitHub, nhánh `claude/laughing-edison-thd2m4` (nhánh duy nhất, kho riêng tư).
- **Google Sheet** (id trong secret `SHEET_DUYET_ID`): tab `Bài viết`, `Cài đặt`, `Khách hàng`, `Nhóm`, `Báo cáo tuần`.
- **Google Drive kho ảnh** (`DRIVE_KHO_ID`): thư mục `Kho-Marketing` và các thư mục con theo sản phẩm. Ảnh mới thả vào `_chua-phan-loai`, AI tự xếp mỗi sáng. **Việc định kỳ của sếp: mỗi tuần thả thêm ảnh/video mới** (lịch 3 bài/ngày dùng nhiều ảnh; email báo cáo tuần có nhắc việc này).
- **Máy chủ Render:** dịch vụ `hoanbao-bot`, gói **miễn phí** (512 MB RAM, CPU yếu, tự ngủ khi lâu không có truy cập). Địa chỉ `https://hoanbao-bot.onrender.com`. UptimeRobot gọi `/healthz` mỗi 5 phút để giữ máy chủ thức.
- **Email báo khách mới:** Google Apps Script (`cong-cu/apps-script-gui-email.gs`) vì Render miễn phí chặn SMTP.
- **Facebook:** ứng dụng "Hoan Bao Marketing" (id trong `config.yaml`), Page, webhook về `/webhook`.
- **Anthropic (Claude):** khóa API, đặt trong GitHub Secret và biến Render `ANTHROPIC_API_KEY`.

### Khóa bí mật (chỉ liệt kê tên, giá trị không ghi ở đâu cả)

- **GitHub Secrets:** `ANTHROPIC_API_KEY`, `FB_PAGE_ID`, `FB_PAGE_TOKEN`, `FB_APP_SECRET`, `FB_VERIFY_TOKEN`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `DRIVE_KHO_ID`, `SHEET_DUYET_ID`, `DATA_DRIVE_FILE_ID`, `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`, `EMAIL_WEBHOOK_URL`, `EMAIL_WEBHOOK_SECRET` (hai khóa email chỉ cần nếu muốn gửi email báo cáo).
- **Render (Environment):** `ANTHROPIC_API_KEY`, `FB_PAGE_ID`, `FB_PAGE_TOKEN`, `FB_APP_SECRET`, `FB_VERIFY_TOKEN` (cũng là mật khẩu bảng điều khiển), `GOOGLE_SERVICE_ACCOUNT_JSON`, `SHEET_DUYET_ID`, `DRIVE_KHO_ID`, `EMAIL_WEBHOOK_URL`, `EMAIL_WEBHOOK_SECRET`.
- Đổi khóa nào thì đổi **cả hai nơi** (GitHub và Render). Khóa Claude hiện **không hết hạn** (đã đổi ngày 14/10/2026).

## 3. Lịch chạy tự động (GitHub Actions)

| Workflow | Khi nào | Việc |
|---|---|---|
| Tạo bài cả tuần | Thứ 6, 09:07 giờ VN | AI viết bài tuần sau, ghi vào Sheet |
| Lên lịch bài đã duyệt | Mỗi giờ, 06:23–22:23 | Hẹn giờ Facebook (và YouTube) cho bài trạng thái "Duyệt" |
| Xếp ảnh vào kho | Mỗi 2 giờ | AI xếp ảnh mới vào thư mục |
| Báo cáo tuần | Thứ 2, 08:07 | Lưu số liệu tương tác vào Sheet |
| Bảng điều khiển | Hằng ngày | Xuất bản xem tĩnh |

Chạy tay: GitHub → Actions → chọn workflow → Run workflow. Các workflow chạy tay: Chẩn đoán chatbot (nhập địa chỉ máy chủ), Kiểm tra kết nối, Nhập danh sách nhóm, Nhập khách từ quảng cáo.

## 4. Chế độ duyệt bài

Tab `Cài đặt`, ô `B1`: **BẬT** = bài mới "Chờ duyệt", người duyệt đổi sang "Duyệt"; **TẮT** = bài sạch tự lên lịch (bài có số liệu lạ hoặc thiếu ảnh vẫn "Chờ duyệt"). Điều kiện giờ hẹn Facebook: cách hiện tại **ít nhất 15 phút**, **không quá 29 ngày**.

## 5. Xử lý sự cố thường gặp

| Hiện tượng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Bảng điều khiển trắng, "Đang chuẩn bị…" | Máy chủ vừa ngủ dậy hoặc vừa khởi động lại; CPU yếu | Chờ 1–3 phút, mở một tab, không bấm F5 liên tục. Chạy workflow **Chẩn đoán chatbot** xem `bang_dieu_khien` và `ram_mb` |
| Lỗi 502 | Máy chủ đang khởi động lại (mỗi lần đẩy code Render dựng lại 3–4 phút) hoặc hết RAM | Chờ 5 phút. Gom nhiều sửa thành ít lần đẩy |
| Email "vượt giới hạn bộ nhớ" từ Render | Gói miễn phí 512 MB | Xem tab Metrics → Memory. Giải pháp chắc chắn là gói Starter/Standard |
| Bot không trả lời khách | Ứng dụng Meta chưa qua xét duyệt (chỉ phục vụ người có vai trò) | Chờ Meta duyệt; xem mục Xem xét ứng dụng. Trong lúc chờ dùng trả lời tự động của Meta Business Suite |
| Bài báo "Lỗi", ghi chú giờ đã qua | Giờ hẹn dưới 15 phút hoặc đã qua | Đổi lại Ngày/Giờ trong Sheet rồi chọn "Duyệt" |
| Dòng Claude trong tab Hệ thống đỏ | Khóa Anthropic sai hoặc hết hạn | Tạo khóa mới, dán vào GitHub và Render |
| Quảng cáo dừng "Lỗi thanh toán" | Thẻ hết hạn hoặc quỹ hết | Nạp tiền hoặc đổi thẻ trong Cài đặt thanh toán của Ads Manager |
| Tên Page đổi nhưng bảng điều khiển hiện tên cũ | Tên được nhớ | Chờ Render khởi động lại |

Chẩn đoán nhanh: workflow **Chẩn đoán chatbot** cho biết giờ khởi động máy chủ, số tin nhận được, RAM đang dùng, bước đang dựng bảng điều khiển.

## 6. Giới hạn đã biết

- **Máy chủ Render miễn phí là điểm yếu nhất:** hay ngủ, chậm, hết RAM. Nâng **Starter** (~7 USD/tháng) hết ngủ và nhanh hơn; vẫn 512 MB RAM. **Standard** (~25 USD/tháng) có 2 GB RAM.
- **Mỗi lần đẩy code Render dựng lại máy chủ**, trang báo 502 trong 3–4 phút. Trong thời gian này khách nhắn có thể bị chậm.
- **Meta:** chưa duyệt quyền nhắn tin cho khách ngoài; quyền đọc/trả lời bình luận (`pages_read_user_content`, `pages_manage_engagement`) chưa xin, vì Meta không cho nộp khi hồ sơ cũ còn đang xét. Quyền đọc khách quảng cáo tự động (`leads_retrieval`) cũng chưa xin.
- **YouTube:** dự án Google Cloud chưa qua kiểm duyệt của YouTube, video có thể bị giữ riêng tư. Phần đăng YouTube chưa thử với video thật.
- **Nhóm Facebook và trang cá nhân:** không có API chính thức, làm tay.

## 7. Nguyên tắc an toàn

- Không dán khóa, token, mật khẩu vào chat hay vào mã nguồn. Tự nhập vào GitHub Secrets hoặc Render.
- Khóa nào bị lộ (ví dụ lộ trong ảnh chụp màn hình) thì **tạo khóa mới và xóa khóa cũ**.
- File chứa số điện thoại khách (CSV quảng cáo) không đưa vào kho mã (đã có trong `.gitignore`).
- Việc tốn tiền (nâng gói Render, nạp quảng cáo) do chủ doanh nghiệp quyết định.
