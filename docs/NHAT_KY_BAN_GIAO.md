# NHẬT KÝ BÀN GIAO: hệ thống marketing tự động Golden Lion

Cập nhật: **21/11/2026**. Người viết: trợ lý kỹ thuật (Claude). Người giao việc: **sếp** (chủ Công ty TNHH Thương Mại Sản Xuất Xuất Nhập Khẩu Hoàn Bảo, thương hiệu Golden Lion / Sư Tử Vàng, keodan.net, TP.HCM).

Mục đích file này: nếu phiên làm việc của trợ lý bị giới hạn hoặc đổi người, **người tiếp quản đọc file này là làm tiếp được ngay**. File **không chứa mật khẩu hay khóa**. Hướng dẫn vận hành chung nằm ở `docs/HUONG_DAN_VAN_HANH.md` (đọc kèm).

---

## 1. Cách làm việc với sếp (bắt buộc đọc)

- Sếp giao **toàn bộ phần kỹ thuật** cho trợ lý: lỗi, workflow, Render, Meta/YouTube API. Sếp rất bận, **báo sự cố là trợ lý tự điều tra và sửa**, không nhờ sếp làm việc kỹ thuật.
- Chỉ **sếp** làm được: chi tiền (nạp quảng cáo, nâng gói Render), nhập mật khẩu/khóa bí mật, đăng nhập tài khoản Meta/Google, chia sẻ thư mục Drive, quay video xin quyền Meta. Gặp việc này thì gộp thành **một yêu cầu ngắn** kèm đúng thao tác phải bấm.
- **Trả lời ngắn, tiếng Việt, gọi "sếp"** (không gọi "anh"). Mỗi lần một bước nhỏ, nói rõ mục đích. Sếp ghét nhiều bước và tin nhắn dài.
- **Không dán khóa/token vào chat hay mã nguồn.** Khóa lộ thì tạo khóa mới.
- **Thật thà:** việc chưa kiểm chứng thì nói chưa kiểm chứng. Đã có lần trợ lý kết luận sai (xem mục 9), sếp rất coi trọng việc này.
- Việc **không được tự làm khi chưa có lệnh**: xóa bài đã đăng trên Page, xóa/di chuyển file của công ty trên Drive, hủy lịch đã hẹn không do lỗi của app.
- Phòng **Marketing** lo: trả lời bình luận/tin nhắn, chạy quảng cáo Facebook, sửa các bài sai do họ đăng (kể cả bài ghi giá cũ). Trợ lý không đụng vào phần của họ trừ khi sếp bảo.
- Git: chỉ làm trên nhánh **`claude/laughing-edison-thd2m4`** (nhánh duy nhất, kho riêng tư `tiffanyle259-lang/APP-QUAN-LY-FACEBOOK`). **Không tạo Pull Request** nếu sếp không yêu cầu. Mỗi lần đẩy code Render dựng lại 3–4 phút (trang 502), nên gom nhiều sửa vào ít lần đẩy.

## 2. Các thành phần và mã định danh (không bí mật)

| Thứ | Giá trị |
|---|---|
| Fanpage chính | Golden Lion – Keo Dán Sư Tử Vàng – Keo Phun Công Nghiệp, id `130442487542312`. Marketing đang gom 3 page về page này. **App chỉ đăng lên đúng một page này.** |
| Ứng dụng Meta | "Hoan Bao Marketing", id `1570474760979317` |
| Tài khoản quảng cáo | "Keo Dán Siêu Dính", id `6181660138559444` (nạp trả trước bằng MoMo, thẻ dự phòng dùng thẻ ảo) |
| Máy chủ chatbot/bảng điều khiển | Render gói miễn phí, `https://hoanbao-bot.onrender.com` (UptimeRobot gọi `/healthz` mỗi 5 phút) |
| Tài khoản dịch vụ Google | `fanpage-bot@hoanbao-marketing.iam.gserviceaccount.com` (cần được chia sẻ quyền Biên tập viên cho mọi thư mục/Sheet app dùng) |
| Thư mục Drive nguồn media (chỉ đọc) | **TÀI NGUYÊN CHUNG** (`CÔNG TY HOÀN BẢO / TÀI NGUYÊN CHUNG`), id `1FCeoSgiWdNWMQm7BhGGj8ZqmR6Z93gFL` |
| Kho cũ | `Kho-Marketing` (id trong secret `DRIVE_KHO_ID`). **Đã tắt khỏi việc chọn ảnh** (`chi_dung_nguon_chung: true`), sếp có thể xóa. Việc xếp ảnh tự bỏ qua khi kho không còn |
| Google Sheet "Duyệt bài" | id trong secret `SHEET_DUYET_ID`. Tab: `Bài viết`, `Cài đặt`, `Khách hàng`, `Nhóm`, `Báo cáo tuần`, `Kiểm tra giá` |
| YouTube | kênh của sếp, tải video qua OAuth (`YT_*`), dự án Google Cloud "HoanBao-YouTube" |
| Mã nguồn | `hoanbao_mkt/` (đăng bài, Sheet, Drive, Facebook, YouTube), `hoanbao_bot/` (chatbot + bảng điều khiển trên Render), `config.yaml`, `data/DuLieuNen_Marketing_HoanBao.xlsx` (dữ liệu sản phẩm cho AI), `tests/` |

Tên các khóa bí mật (GitHub Secrets và Render Environment) liệt kê ở `docs/HUONG_DAN_VAN_HANH.md` mục 2. Đổi khóa nào thì đổi **cả hai nơi**.

## 3. Hệ thống đang làm gì (luồng)

1. **Thứ Sáu 09:07 (giờ VN)**, workflow *Tạo bài cả tuần*: AI (Claude `claude-sonnet-5-5`) viết bài cho **tuần sau** từ file Excel + `config.yaml`, chọn ảnh/video, ghi vào tab `Bài viết`. Chế độ duyệt đang **TẮT** (tự duyệt): bài sạch tự trạng thái "Duyệt"; bài có cảnh báo (số liệu lạ, thiếu ảnh/video, có ghi giá) vào "Chờ duyệt".
2. **Mỗi giờ**, workflow *Lên lịch bài đã duyệt*: hẹn giờ trên Facebook cho bài "Duyệt" (Facebook chỉ nhận hẹn giờ **cách ≥ 15 phút và ≤ 29 ngày**; bài xa hơn giữ "Duyệt", tự lên khi tới hạn). Bài có video: đăng **Reel** (nếu Meta từ chối thì đăng video thường, ghi lý do vào ghi chú) và tải lên **YouTube** (riêng tư, tự công khai đúng giờ).
3. Facebook tự đăng đúng giờ. Bảng điều khiển hiển thị bài quá giờ là "Đã đăng" (suy ra từ giờ, không đọc trực tiếp Facebook).
4. **Mỗi 2 giờ**, *Xếp ảnh vào kho*: AI xếp ảnh thả vào `_chua-phan-loai` (chỉ còn tác dụng nếu Kho-Marketing còn).
5. **Hằng ngày 01:30**, *Đẩy bù video lên YouTube*: tối đa 5 video mỗi lần (hạn mức YouTube ~6 video/ngày).
6. **Thứ Hai 08:07**, *Báo cáo tuần*: số liệu tương tác, lưu tab `Báo cáo tuần`, gửi email (nhắc sếp thả thêm ảnh/video).
7. **Chatbot** (Render): nhận tin nhắn/bình luận qua webhook, trả lời bằng AI từ dữ liệu sản phẩm, xin SĐT khi khách hỏi giá, ghi tab `Khách hàng`, báo nhân viên. Khi nhân viên trả lời tay thì bot im lặng với cuộc chat đó. Bot **không báo giá**.

Cron (UTC) và giờ VN: tạo bài `7 2 * * 5` (T6 09:07), lên lịch `23 23,0-15 * * *` (mỗi giờ 06:23–22:23), xếp ảnh `17 */2 * * *`, báo cáo `7 1 * * 1`, YouTube bù `30 18 * * *`, bảng điều khiển `11 14 * * *`.

## 4. Cấu hình hiện tại (`config.yaml`)

- **Lịch đăng: 16 bài/ngày, cả Chủ nhật** (112 bài/tuần). Mỗi ngày Thứ 2 đến Thứ 7: 1 bài gốc theo Excel + 15 khung phụ (06:30, 07:30, 08:30, 09:45, 10:15, 12:00, 13:00, 14:00, 15:30, 16:30, 17:30, 18:30, 20:30, 21:30, 22:30). Chủ nhật: 16 khung riêng (`khung_chu_nhat`, thêm 08:00). **Khung 15:30 là video Reel** (1 Reel/ngày). Loại bài xoay vòng: Giới thiệu sản phẩm, Mẹo dùng keo, Theo ngành, Hậu trường nhà máy/chính sách. Mã bài (`ma_bai`) dạng `2026-11-24_thu3_1530`, bài gốc không có hậu tố giờ.
  - Sếp từng được tư vấn mức tối đa an toàn khoảng 12–16 bài/ngày (giới hạn Facebook ~25/ngày/page). Sếp chọn **giữ 16 bài/ngày** (đã thử đề xuất 10 bài dồn vào giờ cao điểm, sếp bảo "cứ như cũ").
- **Nguồn media:** `nguon_chung` = TÀI NGUYÊN CHUNG, `chi_dung_nguon_chung: true`.
  - **Ảnh chỉ lấy trong thư mục `ANH-SACH-AI`** (`nguon_chung_anh_tu`), gồm các thư mục con theo mã hàng (405A, SPRO, PHU-GIA…), hàng trăm ảnh.
  - **Video chỉ lấy trong `VIDEO-SACH-AI` và `VIDEO-DANG-REEL`** (`nguon_chung_video_tu`). Video trong VIDEO-DANG-REEL được **ưu tiên**. Video ở `VIDEO CLIP THẬT`, `VẬT LIỆU GHÉP VIDEO` **không dùng**.
  - Loại trừ thư mục: `seo`, `vat lieu ghep video`, `banner display`, `video clip that` (`nguon_chung_loai_tru`).
  - `ma_phu`: SUPERPRO còn gọi SPRO/S-PRO trên tên file.
- **Không lặp:** `khong_lap_lai_trong_ngay: 28`. Chọn file chưa dùng trong 28 ngày và không nằm trong bài nào khác của Sheet; hết mới dùng lại.
- **Bảng giá chính thức** (`bang_gia`, Marketing cập nhật **19/10/2026**, chưa VAT): 228 can 450k / thùng 15kg 1,6tr; S-PRO và 339 can 600k / thùng 10kg 1,6tr; 405A, HP-333, X66 can 450k / thùng 15kg 1,6tr; Super Pro can 400k / thùng 15kg 1,4tr; Chất xử lý PU&PVC can 740k / thùng 10kg 1,8tr; S383 chai 800ml 550k. Hotline trong bảng giá: 0976.884.341 – 0938.292.538 – 0903.831.913. **App chỉ dùng bảng giá này để kiểm tra, không đưa giá vào bài.**
- AI: model `claude-sonnet-5-5`, effort medium. Facebook Graph API `v24.0`.

## 5. Luật chọn ảnh/video (quan trọng, đã sửa sau sự cố)

Khi viết bài tuần/tháng và khi gán ảnh (`hoanbao_mkt/kho_anh.py`, `chon_file`):
1. File nguồn chung **bắt buộc ghi đúng mã sản phẩm của bài** (trong tên file hoặc tên thư mục chứa; HP-333 khớp HP333, S-PRO khớp spro). Không lấy "tạm" ảnh sản phẩm khác.
2. **Bài loại "Video demo thật" chỉ được gắn video.** Không có video đúng mã thì bài vào "Chờ duyệt" kèm cảnh báo, **không** lấy ảnh thay. Lớp chặn thứ hai ở bước lên lịch: bài video mà gắn ảnh thì không hẹn giờ.
3. Bài không gắn với sản phẩm (hậu trường, chính sách đại lý): lấy ảnh bất kỳ trong ANH-SACH-AI.
4. Ưu tiên file chưa dùng, rồi mới dùng lại.
Công cụ kiểm tra/sửa bài chưa đăng gán sai: `don-bai` → `kiem-anh` (chỉ xem) và `sua-anh` (hủy lịch cũ trên Facebook, gán lại, bài tự hẹn giờ lại).

## 6. Công cụ chạy tay (GitHub → Actions → workflow → Run workflow)

Workflow **Dọn bài trong Sheet** (`don-bai.yml`), ô `viec` (và `ma`, `thu` = chỉ xem trước, mặc định **true**):

| viec | Làm gì |
|---|---|
| `duyet` / `bo-qua-gio` / `dinh-dang` | Duyệt hàng loạt bài "Chờ duyệt" còn hạn (trừ bài AI cảnh báo) / chuyển bài quá giờ sang "Bỏ" / tô màu theo trạng thái |
| `xem` | In nội dung các bài đang "Chờ duyệt" vào nhật ký |
| `duyet-ma` | Duyệt đúng một bài theo `ma` (mã bài) |
| `doi-chieu-fb` | So bài thật trên Facebook với Sheet (bài đã đăng 9 ngày, bài hẹn giờ) |
| `youtube` / `youtube-bu` | Liệt kê video đã lên YouTube và công khai chưa / đẩy bù các video chưa có (tối đa 5) |
| `thu-muc-drive` | Liệt kê thư mục Drive app thấy; `ma` = `top:<id>` xem thư mục cấp 1, hoặc `<id>` xem bên trong 2 cấp |
| `phan-tich` | Phân tích 4 tuần: loại bài và khung giờ tương tác tốt nhất (điểm = cảm xúc + 2×bình luận + 3×chia sẻ) |
| `ra-gia` | Đối chiếu giá trong bài (Sheet và Page 120 ngày) với `bang_gia`, ghi tab `Kiểm tra giá` |
| `kiem-anh` / `sua-anh` | Kiểm tra / sửa bài chưa đăng gán sai ảnh-video (xem mục 5). `sua-anh` cần `thu=false` |
| `xoa-dang-lai` | Xóa **một** bài sai đã đăng (nhận theo đầu nội dung `ma`) và đăng lại bằng video đúng. **Chưa từng chạy thật, chỉ chạy khi sếp ra lệnh** |
| `bo-khung` | Bỏ bài chưa đăng ở các khung giờ chỉ định (`ma` = `07:30,08:30`), hủy lịch Facebook. **Chưa chạy thật** (lần chạy thử bị lỗi ngay đầu, lỗi đã sửa 21/11) |

Workflow khác chạy tay: **Tạo bài cả tuần** (ô `tuan` = ngày Thứ 2, hoặc `thang` = `2026-12` tạo cả tháng, bài đã có thì bỏ qua), **Gán ảnh cho bài viết** (có ô `doi_kho`), **Chẩn đoán chatbot** (nhập `https://hoanbao-bot.onrender.com`), **Kiểm tra kết nối**, **Nhập danh sách nhóm**, **Nhập khách từ quảng cáo**, **Đặt chế độ duyệt bài**, **Nối Facebook với chatbot**.

Các workflow dùng chung nhóm chạy `fanpage`: chạy lần lượt, có thể phải chờ nhau.

## 7. Trạng thái hiện tại (21/11/2026)

- **Đăng bài chạy bình thường.** Đã đối chiếu với Facebook (30/10 và 20/11): bài đăng đúng giờ, bài tháng 11 đã được tạo đủ đến 30/11 (các bài còn trong cửa sổ 29 ngày đã hẹn giờ, bài xa hơn chờ tự lên lịch). Tháng 12 tạo dần mỗi sáng thứ Sáu. 16 bài/ngày áp dụng cho các tuần tạo từ 11/11 (trước đó 3 bài/ngày, không đăng Chủ nhật).
- **Meta:** hồ sơ bị **từ chối ngày 22/10** cho 3 quyền `pages_show_list`, `pages_manage_metadata`, `pages_messaging` (lý do: video quay màn hình không trình bày đủ đăng nhập Meta, cấp quyền, trải nghiệm đầy đủ, giao diện tiếng Anh có chú thích). Sếp **không gửi lại**. Quyền bình luận (`pages_read_user_content`, `pages_manage_engagement`) và `leads_retrieval` chưa xin. Hệ quả: **bot chưa trả lời được khách thật** (chỉ tài khoản có vai trò trên app). **Nhân viên đang dùng trả lời tự động/mẫu của Meta Business Suite** (đã chỉnh đúng bảng giá). Thông báo "duyệt" sếp thấy ngày 20/11 nhiều khả năng là thông báo cũ. Kịch bản quay video lần 2 đã soạn: `ho-so-meta/kich-ban-quay-video.md` (dùng trang Messenger API Settings của Meta, nút "Thêm trang" để quay cảnh đăng nhập và cấp quyền; thêm trang dự phòng `/ket-noi` của app).
- **YouTube:** hoạt động. Video hẹn giờ qua lượt tạo tuần từng bị sót (thiếu khóa YouTube trong workflow), đã sửa 20/11, đang đẩy bù mỗi ngày.
- **Bảng điều khiển** trên Render (miễn phí): chỉ để xem, hay chậm. Bài quá giờ hiện "Đã đăng", bài lỗi ẩn khỏi tab Bài đăng, sang tháng mới tự ẩn bài tháng cũ, thanh tab cố định. Sếp **không nâng Render** ("quá mắc chỉ để điều khiển thao tác").
- **Quảng cáo Facebook** (Marketing làm): 3 chiến dịch chạy. Chi phí/lead theo báo cáo ngày 21/11: 228+SPRO ~31,5k, PU-PVC+S383 ~43,7k, HP333+405A ~67,4k; chiến dịch tắt "228 và 339 – Copy" ~85k. Khách quảng cáo nhập bằng file CSV (mở bằng Excel sẽ lỗi font, app đọc UTF-8).
- **Giá trong bài:** bài do app đăng **không có giá**. Trên Page có **36 bài ghi giá sai** so với bảng 19/10 (HP333/405A ghi 600k thay 450k, X66 500k thay 450k, S383 600k thay 550k…), **không do app đăng** (do Marketing/công cụ khác). Danh sách trong tab `Kiểm tra giá`. Giá có VAT 8% (486.000đ, 648.000đ) là đúng. Marketing đang xử lý; đang có một bài HP-333 sai ảnh sếp bảo "để Marketing sửa", trợ lý **chưa xóa**.
- **Vòng học tự động:** mỗi sáng thứ Sáu app lấy bài tương tác cao 4 tuần qua làm mẫu giọng văn cho AI. Số liệu 20/11 (127 bài): **Video demo thật 6,0 điểm/bài (cao nhất)**, Hậu trường/chính sách 4,2, Theo ngành 1,7, Mẹo dùng keo 1,4, Giới thiệu sản phẩm 1,4, Công trình/khách hàng thật 0,2. Giờ tốt: 09:00, 15:30, 08:00, 12:00; giờ kém: 19:30, 10:00, 17:30. Tương tác chung của trang **thấp**. Gợi ý đã nói với sếp: làm nhiều video thật hơn, kết bài bằng câu hỏi, nhờ Marketing đẩy quảng cáo cho bài TOP.

## 8. Việc đang chờ / đề xuất

1. **Sếp chưa trả lời 2 câu:** (a) ngưỡng "miễn phí vận chuyển đơn từ 5.000.000đ tại TP.HCM" trong bài còn đúng không; (b) có thêm 2 số điện thoại 0938.292.538 và 0903.831.913 vào bài không (app đang chỉ ghi 0976.884.341).
2. **Meta:** nếu sếp muốn bot trả lời khách thật thì phải gửi lại hồ sơ kèm video quay mới (nhân viên quay theo kịch bản). Chưa quyết.
3. Xem lại **bảng xếp hạng tương tác sau 2–3 tuần** rồi đề xuất tăng/cắt khung giờ (cắt khung kém là quyết định của sếp, sếp từng không đồng ý bỏ).
4. **Kiểm chứng Reel thật:** chưa tận mắt thấy một Reel đã lên Page (mới thấy video lên YouTube). Xem ghi chú bài video trong Sheet (có chữ "Reel" hay "không đăng Reel được: …").
5. Bộ phận sản xuất đang làm Reel, bỏ vào `VIDEO-DANG-REEL`. **Quy ước tên file:** `REEL_<số>_<mã sản phẩm>_<mô tả>_9x16_<giây>.mp4` để app ghép đúng sản phẩm. Kho video ~28 video, 1 Reel/ngày, 28 ngày sau mới lặp.
6. Nhập file khách mới từ quảng cáo (CSV) khi sếp gửi.
7. Giữ **số dư tiền quảng cáo** và thẻ dự phòng (việc của sếp/Marketing).
8. Tạo bài tháng 12: tự động qua lượt thứ Sáu hằng tuần; nếu cần chạy cả tháng thì Run workflow *Tạo bài cả tuần* với `thang = 2026-12`.

## 9. Lỗi đã gặp và bài học (đừng lặp lại)

- **11/11, bài sai ảnh và nội dung:** bài "Video demo thật" về HP-333 đăng kèm **ảnh 228**. Nguyên nhân: luật chọn media lúc đó chưa đọc thư mục video, không tìm được video thì lấy ảnh khác, và tôi đã nới lỏng luật khớp sản phẩm. Hậu quả: 22 bài chưa đăng bị nghi sai, kiểm tra kỹ còn 7 bài sai thật (đã sửa bằng `sua-anh`). **Bài học:** sai nội dung công khai là lỗi nặng, sếp rất bực. Luôn bắt buộc đúng mã sản phẩm, bài video không thay bằng ảnh; kiểm tra bằng `kiem-anh` sau mỗi thay đổi luật chọn media.
- **20/11, kết luận sai về bot:** từ việc "tin cuối trong chat là của Page" suy ra bot đang trả lời khách thật. Thực ra có thể là tin tự động của Meta Inbox hay nhân viên. **Bài học:** không suy diễn từ gián tiếp, cần bằng chứng trực tiếp (số liệu `chan-doan`, báo cáo từ tài khoản Meta).
- **Đọc nhầm số liệu:** "ANH-SACH-AI có 8 mục" là 8 thư mục con (hàng trăm ảnh), không phải 8 ảnh. Kiểm tra cấu trúc trước khi kết luận.
- **Giá 486.000đ/648.000đ** từng bị nghi là gõ nhầm, thực ra là giá đã cộng VAT 8%.
- **Ghi đè ghi chú:** chuyển bài sang "Bỏ" hoặc đổi ảnh ghi đè cột Ghi chú nên mất link YouTube. Lưu mã video trước khi thao tác nếu cần.
- **Lỗi phạm vi biến Python:** trong hàm `don_bai`, `from .duyet_bai import DUYET` ở một nhánh làm `DUYET` thành biến cục bộ cả hàm, nhánh khác dùng bị `UnboundLocalError`. Đã sửa; khi thêm nhánh mới chỉ import cái cần, tránh trùng tên hằng đã import ở đầu file.
- **Xếp hàng workflow:** nhóm `fanpage` chạy lần lượt; một lượt tạo bài dài có thể làm lệnh khác chờ nhiều phút.
- **Giới hạn khác:** YouTube ~6 video/ngày; Facebook hẹn giờ ≤ 29 ngày; Render miễn phí hay ngủ/hết RAM; các tool GitHub MCP đôi khi timeout, thử lại.
- **Bị chặn bởi kiểm soát an toàn** khi định in nội dung file hướng dẫn của công ty ra nhật ký chạy: **không lách**, hỏi sếp dán nội dung hoặc cho phép.
- **Phiên đám mây không truy cập máy của sếp** và không gắn được thư mục máy tính; mọi media đi qua Google Drive. File trên máy sếp: sếp đính kèm từng file (nút +, Ctrl+U) hoặc dán nội dung.

## 10. Nhật ký các mốc chính

- **Đầu 10/2026:** dựng hệ thống: AI viết bài tuần từ Excel, Sheet duyệt, đăng Facebook, chatbot Messenger (Render), báo cáo tuần, email Apps Script; xin duyệt quyền Meta (gửi ~8–9/10).
- **10/2026:** thêm tab Nhóm (94 nhóm, nút soạn bài cho nhân viên đăng tay), tab Báo cáo, nhập khách từ CSV quảng cáo, đồng bộ YouTube (OAuth, video riêng tư hẹn công khai), đổi tên Page, thêm đánh dấu "Đã chia sẻ", tô màu Sheet, tự duyệt (B1 = TẮT).
- **Sự cố bảng điều khiển** (treo, 502, hết RAM trên Render miễn phí): sửa deadlock nạp thư viện, trả lời tức thì, cập nhật lạc quan, giảm RAM; sếp quyết giữ gói miễn phí, bảng điều khiển chỉ để xem.
- **Quảng cáo:** thêm quảng cáo S-PRO (được duyệt), hướng dẫn thẻ ảo dự phòng, nạp bằng MoMo.
- **22/10:** Meta từ chối 3 quyền (xem mục 7). Tạo trang `/ket-noi`, kịch bản quay mới.
- **14/10:** đổi khóa Anthropic sang loại không hết hạn.
- **19/10:** lên 3 bài/ngày; **ảnh không trùng** (luật 28 ngày); tạo bài giữa tuần.
- **20/10–30/10:** ẩn bài lỗi khỏi tab Bài đăng, nhãn "Đã đăng", sửa ngày sai, Drive tự thử lại khi lỗi 500, đối chiếu Facebook.
- **30/10:** tạo cả tháng 11 một lượt (`thang`), bài quá xa chờ tự lên lịch, bảng điều khiển chỉ hiện tháng hiện tại.
- **11/11:** nối thư mục TÀI NGUYÊN CHUNG (chỉ đọc), video đăng Reel, 6 rồi 16 bài/ngày, đăng cả Chủ nhật, vòng học, sự cố sai ảnh/video và cách sửa, chặn bài video gắn ảnh.
- **20/11:** kiểm tra Meta (còn bị từ chối), YouTube (hoạt động, bù hằng ngày), kiểm tra giá theo bảng 19/10, gỡ giá cũ khỏi câu mẫu của bot, 16 bài/ngày giữ nguyên.
- **21/11:** viết file bàn giao này; sửa lỗi nhánh `bo-khung`.

## 11. Cách làm các việc thường gặp (playbook)

- **"App có đăng bài không?"** → Run *Dọn bài trong Sheet* `viec = doi-chieu-fb` (thu = true), đọc nhật ký. Hoặc xem tab `Bài viết` trong Sheet.
- **"Bài nào sai ảnh/video?"** → `kiem-anh`; sửa bằng `sua-anh` với `thu = false` (chỉ động tới bài chưa đăng, cách giờ ≥ 30 phút).
- **"Bot có trả lời không?"** → Run *Chẩn đoán chatbot* với địa chỉ Render; đọc số webhook, tin nhận/trả lời, lỗi, vai trò trên app, các cuộc chat gần nhất. Nhớ: chưa chắc tin cuối của Page là bot.
- **Bài có giá?** → `ra-gia`, xem tab `Kiểm tra giá`.
- **Video đã lên YouTube chưa?** → `youtube`; thiếu thì `youtube-bu` (giới hạn 5/lần).
- **Thêm ảnh/video:** bỏ vào `ANH-SACH-AI/<mã hàng>/` hoặc `VIDEO-DANG-REEL`; app tự thấy lần chạy sau, không cần báo.
- **Đổi số bài/giờ đăng:** sửa `khung_them` / `khung_chu_nhat` trong `config.yaml`, đẩy lên; từ lượt tạo tuần/tháng sau áp dụng. Muốn áp dụng cho phần còn lại của tháng: Run *Tạo bài cả tuần* với `thang`. (Bài đã tạo không tự đổi, muốn bỏ thì `bo-khung`.)
- **Đổi nguồn thư mục media:** chia sẻ thư mục cho tài khoản dịch vụ Google (quyền Biên tập viên), sửa `nguon_chung*` trong `config.yaml`.
- **Chạy kiểm tra trước khi đẩy code:** `python -m venv v && v/bin/pip install -r requirements.txt pytest && v/bin/python -m pytest -q` (hiện ~77 bài kiểm tra, phải qua hết).
- **Đẩy code:** `git push -u origin claude/laughing-edison-thd2m4`. Commit kèm dòng `Co-Authored-By` theo quy ước phiên làm việc. Không tạo PR nếu chưa được yêu cầu.

## 12. Bản đồ mã nguồn

- `hoanbao_mkt/__main__.py`: mọi lệnh (`tao-tuan`, `len-lich`, `gan-anh`, `don-bai` và các `viec`…), hàm `_kho`, `_doc_du_lieu`.
- `ke_hoach.py`: lập kế hoạch bài từng tuần; `du_lieu.py` đọc Excel, `khung_phu` thêm khung phụ/Chủ nhật; `viet_bai.py` gọi AI (chia nhóm 6 bài/lần, nhận bài mẫu từ vòng học).
- `kho_anh.py`: đọc Drive, chọn ảnh/video (`chon_file`, `khop_ma`, `KhoDrive.file_nguon_chung`); `sua_anh.py` kiểm tra/sửa bài sai media.
- `facebook.py`: hẹn giờ Facebook, đăng Reel (`_len_lich_reel`), bài đã đăng/hẹn giờ, xóa; `youtube.py` tải lên YouTube.
- `duyet_bai.py`: tab `Bài viết` (cột A–J), trạng thái (Chờ duyệt, Duyệt, Đã lên lịch, Lỗi, Bỏ), màu, danh sách chọn.
- `hoc.py` (vòng học), `gia.py` (kiểm tra giá), `bao_cao.py`, `nhap_khach.py`, `phan_loai.py`, `don_bai.py`, `bang_dieu_khien.py`.
- `hoanbao_bot/`: `xu_ly.py` (xử lý tin/bình luận), `ai_bot.py`, `kien_thuc.py` (luật của bot: không báo giá), `messenger.py`, `server.py` + `wsgi.py` (Flask/gunicorn trên Render, bảng điều khiển, `/ket-noi`), `chan_doan.py`.
- `tests/`: `test_giai_doan_1.py` (đăng bài, chọn ảnh, giá, vòng học…), `test_bot.py` (bot, bảng điều khiển), `test_duyet_bai.py`.
