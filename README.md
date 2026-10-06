# Marketing Facebook tự động – Golden Lion (Công ty TNHH Hoàn Bảo)

**Giai đoạn 1: Tự động nội dung fanpage.** Chạy trên GitHub Actions (máy chủ của GitHub), không cần mở laptop. Chỉ dùng API chính thức của Meta (Graph API).

## Cách hoạt động

```
Thứ 6, 9h sáng      AI viết 6 bài cho tuần sau (T2–T7) theo sheet "Lịch chủ đề"
                    + tự chọn ảnh/video trong Drive "Kho-Marketing"
                    → ghi vào Google Sheet "Duyệt bài"
Chế độ duyệt BẬT    Bạn đọc/sửa nội dung trong Sheet, đổi trạng thái thành "Duyệt"
Chế độ duyệt TẮT    App tự chuyển "Duyệt" (trừ bài có cảnh báo)
Mỗi giờ (6h–22h)    App hẹn giờ đăng các bài "Duyệt" lên Fanpage → "Đã lên lịch"
```

**Nguyên tắc nội dung**
- AI chỉ dùng thông tin trong file `data/DuLieuNen_Marketing_HoanBao.xlsx`.
- Ô ghi `[cần bổ sung]` bị bỏ. Ý nào ghi "xác nhận" cũng bị bỏ (ví dụ "web ghi 10kg, 180kg – xác nhận"). Ghi chú "(theo nhãn)" không đưa vào bài.
- Không nêu giá (cột giá chưa xác nhận). Muốn dùng giá thì xóa dòng đó trong `config.yaml` → `cot_bo_qua`.
- Bài có con số không tìm thấy trong file sẽ bị giữ ở trạng thái "Chờ duyệt", kèm cảnh báo, kể cả khi tắt chế độ duyệt.

**Xoay vòng nội dung**
- Thứ 2: mỗi tuần một sản phẩm chủ lực. Sản phẩm chủ lực là sản phẩm ghi "Có" ở cột "Chủ lực?". Nếu chưa đánh dấu sản phẩm nào, app xoay 7 loại keo.
- Thứ 3: mỗi tuần mẹo về một sản phẩm.
- Thứ 5: mỗi tuần một ngành.
- Thứ 4 và Thứ 6: đi theo sản phẩm của tuần và ngành dùng sản phẩm đó.
- Chủ nhật: không đăng.

## Chi phí GitHub Actions (repo Private, gói Free: 2.000 phút/tháng)

| Việc | Số lần/tháng | Phút/lần (làm tròn lên) | Phút/tháng |
|---|---|---|---|
| Lên lịch bài đã duyệt (17 lần/ngày) | ~510 | 1–2 | 510–1.020 |
| Tạo bài cả tuần | ~4 | 1–3 | 4–12 |
| Kiểm tra kết nối (chạy tay) | vài lần | 1–2 | ~10 |

Tổng khoảng **530–1.050 phút**, bằng 27–53% mức miễn phí. Xem số phút đã dùng ở *Settings → Billing and plans*. Nếu gần hết, sửa dòng `cron` trong `.github/workflows/len-lich.yml` (ví dụ chỉ chạy 3 giờ một lần).

## Google Sheet "Duyệt bài"

| Cột | Ý nghĩa |
|---|---|
| Nội dung | Sửa trực tiếp. App đăng đúng nội dung trong ô. |
| Ảnh/Video | Link Drive của file đã chọn. Muốn đổi thì dán link file khác. Để trống thì đăng chỉ chữ. |
| Ngày đăng / Giờ | Có thể sửa trước khi duyệt. |
| Trạng thái | `Chờ duyệt` → `Duyệt` (app lên lịch) hoặc `Bỏ`. App ghi `Đã lên lịch` / `Lỗi`. |

Muốn đổi bài **đã lên lịch** thì sửa trong Meta Business Suite, vì app không đồng bộ ngược.

Tab **Cài đặt**, ô B1: `BẬT` / `TẮT` chế độ duyệt.

## Kho ảnh/video trên Google Drive

Chỉ cần tự tạo thư mục `Kho-Marketing`. Các thư mục con dưới đây sẽ được app tự tạo khi chạy workflow **Kiểm tra kết nối**. Danh sách:

- **Theo sản phẩm** (cột "Thư mục ảnh/video trong kho"): `keo-phun-228`, `keo-phun-339`, `keo-phun-spro`, `keo-405a`, `keo-pu-hp333`, `keo-x66`, `keo-go-superpro`, `chat-xu-ly`, `chat-dong-ran-s383`, `chat-dong-ran-w838`, `chat-dong-ran-h638`
- **Theo lịch:** `video-demo`, `khach-hang`, `nha-may`, `anh-minh-hoa-chung`
- **Theo ngành:** `nganh-giay-dep`, `nganh-sofa-nem`, `nganh-do-go`, `nganh-o-to`, `nganh-dai-ly`

Muốn đổi tên các thư mục theo ngành hoặc ảnh chung thì sửa trong `config.yaml`.

**Đặt tên file có từ khóa** để app chọn đúng, ví dụ `phun-mut-sofa-01.mp4`, `dan-de-giay-eva.jpg`, `tran-xe-339.jpg`. App ưu tiên file khớp từ khóa của bài, đúng loại (bài Thứ 4 lấy video) và lâu chưa dùng. App không dùng lại một file trong 28 ngày nếu kho còn file khác.

## Cài đặt một lần

### 1. Google (Drive + Sheet)
1. Vào https://console.cloud.google.com, tạo project, rồi bật **Google Drive API** và **Google Sheets API**.
2. Vào *IAM & Admin → Service Accounts*, tạo service account, rồi vào tab *Keys → Add key → JSON* để tải file khóa về.
3. Chia sẻ thư mục `Kho-Marketing` cho email của service account (dạng `...@...iam.gserviceaccount.com`) với quyền **Người chỉnh sửa**. Cần quyền này để app ghi lại ngày dùng ảnh.
4. Tạo một Google Sheet trống tên "Duyệt bài" và chia sẻ cho email đó với quyền **Người chỉnh sửa**.
5. Lấy ID:
   - Thư mục: phần cuối link `drive.google.com/drive/folders/<ID>`
   - Sheet: phần giữa link `docs.google.com/spreadsheets/d/<ID>/edit`

### 2. Facebook (Graph API)
1. Vào https://developers.facebook.com, tạo App loại **Business** và gắn với Business Manager có Fanpage.
2. Nên dùng **System User** vì token không hết hạn: vào *Business Settings → Users → System users*, tạo user (Admin), giao Fanpage cho user với quyền đầy đủ, rồi bấm *Generate token* và chọn app. Chọn các quyền `pages_manage_posts`, `pages_read_engagement`, `pages_show_list`.
3. Gọi `GET /me/accounts` bằng token vừa tạo (thử trong Graph API Explorer) để lấy **Page access token** và **Page ID**.

### 3. Claude API
Tạo API key tại https://console.anthropic.com. Mỗi tuần chỉ 1 lần gọi AI, chi phí rất thấp.

### 4. GitHub Secrets
Vào repo → *Settings → Secrets and variables → Actions → New repository secret*:

| Tên | Giá trị |
|---|---|
| `ANTHROPIC_API_KEY` | API key Claude |
| `FB_PAGE_ID` | ID Fanpage |
| `FB_PAGE_TOKEN` | Page access token |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Toàn bộ nội dung file JSON khóa service account |
| `DRIVE_KHO_ID` | ID thư mục `Kho-Marketing` |
| `SHEET_DUYET_ID` | ID Google Sheet "Duyệt bài" |
| `DATA_DRIVE_FILE_ID` | *(Không bắt buộc)* ID file Excel dữ liệu nền trên Drive. Có giá trị này thì app đọc bản trên Drive, sửa file ở đó là xong, không cần up lại GitHub. |

### 5. Chạy thử
1. Vào tab **Actions → Kiểm tra kết nối → Run workflow**. Mọi dòng phải có dấu ✓. Dòng "Kho Drive" báo các thư mục còn trống.
2. Vào **Actions → Tạo bài cả tuần → Run workflow**, rồi mở Sheet xem bản nháp.
3. Đổi một bài thành "Duyệt", rồi chạy **Lên lịch bài đã duyệt**. Kiểm tra trong Meta Business Suite → *Bài viết đã lên lịch*.

## Chạy trên laptop (tùy chọn)

```bash
pip install -r requirements.txt
python -m hoanbao_mkt xem-ke-hoach               # xem kế hoạch tuần sau, không cần khóa nào
python -m hoanbao_mkt xem-ke-hoach --ai          # AI viết thử (cần ANTHROPIC_API_KEY)
python -m pytest -q                              # chạy kiểm thử
```
