// Dán toàn bộ vào Google Apps Script. Đổi MAT_KHAU cho trùng EMAIL_WEBHOOK_SECRET trên Render.
const MAT_KHAU = 'DOI-CHUOI-BI-MAT-DAI-O-DAY';
const EMAIL_THEM = ''; // gửi thêm cho người khác: ghi email, ngăn bằng dấu phẩy

function doPost(e) {
  try {
    const d = JSON.parse(e.postData.contents);
    if (d.secret !== MAT_KHAU) return ContentService.createTextOutput('forbidden');
    const chinh = Session.getEffectiveUser().getEmail() || Session.getActiveUser().getEmail();
    const nhan = [chinh, EMAIL_THEM].filter(String).join(',');
    if (!nhan) return ContentService.createTextOutput('loi: khong xac dinh duoc email nguoi nhan, hay ghi email vao EMAIL_THEM');
    MailApp.sendEmail(nhan, String(d.subject || 'Thong bao').slice(0, 150), String(d.body || '').slice(0, 5000));
    return ContentService.createTextOutput('ok');
  } catch (err) {
    return ContentService.createTextOutput('loi: ' + err.message);
  }
}
