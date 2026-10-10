// Dán toàn bộ đoạn này vào Google Apps Script (script.google.com), tài khoản Gmail sẽ GỬI thư.
// Đổi 2 dòng đầu, rồi Triển khai > Ứng dụng web.
const MAT_KHAU = 'DOI-CHUOI-BI-MAT-DAI-O-DAY';   // tự đặt một chuỗi dài, trùng với EMAIL_WEBHOOK_SECRET trên Render
const EMAIL_NHAN = 'dia-chi-nhan-thong-bao@gmail.com'; // thư báo khách mới sẽ gửi tới đây (nhiều địa chỉ: ngăn bằng dấu phẩy)

function doPost(e) {
  try {
    const d = JSON.parse(e.postData.contents);
    if (d.secret !== MAT_KHAU) return ContentService.createTextOutput('forbidden');
    MailApp.sendEmail(EMAIL_NHAN, String(d.subject || 'Thông báo').slice(0, 150), String(d.body || '').slice(0, 5000));
    return ContentService.createTextOutput('ok');
  } catch (err) {
    return ContentService.createTextOutput('loi');
  }
}
