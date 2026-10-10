"""Ghi khách quan tâm vào tab 'Khách hàng' của Google Sheet và báo nhân viên qua Telegram (nếu cấu hình)."""

from __future__ import annotations

import os
import smtplib
from datetime import datetime
from email.message import EmailMessage

import requests

TAB = "Khách hàng"
TIEU_DE = ["Thời gian", "Kênh", "ID Messenger", "Tên", "SĐT", "Nhu cầu", "Lý do chuyển", "Trạng thái", "Hộp thư"]
TRANG_THAI_KHACH = ["Mới", "Đã gọi", "Báo giá", "Chốt đơn", "Không mua"]
LINK_HOP_THU = "https://business.facebook.com/latest/inbox"


class SoKhach:
    def __init__(self, sheets_service, sheet_id: str):
        self.svc = sheets_service.spreadsheets()
        self.id = sheet_id
        self._san_sang = False

    def _dam_bao(self) -> None:
        if self._san_sang:
            return
        info = self.svc.get(spreadsheetId=self.id, fields="sheets.properties").execute()
        tab_id = next((s["properties"]["sheetId"] for s in info["sheets"] if s["properties"]["title"] == TAB), None)
        if tab_id is None:
            r = self.svc.batchUpdate(spreadsheetId=self.id,
                                     body={"requests": [{"addSheet": {"properties": {"title": TAB}}}]}).execute()
            tab_id = r["replies"][0]["addSheet"]["properties"]["sheetId"]
        # Cột Trạng thái (H) là danh sách chọn để nhân viên theo dõi khách đến lúc chốt đơn.
        self.svc.batchUpdate(spreadsheetId=self.id, body={"requests": [{"setDataValidation": {
            "range": {"sheetId": tab_id, "startRowIndex": 1, "endRowIndex": 2000, "startColumnIndex": 7, "endColumnIndex": 8},
            "rule": {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": v} for v in TRANG_THAI_KHACH]},
                     "showCustomUi": True, "strict": False}}}]}).execute()
        co = self.svc.values().get(spreadsheetId=self.id, range=f"'{TAB}'!A1:I1").execute().get("values")
        if not co:
            self.svc.values().update(spreadsheetId=self.id, range=f"'{TAB}'!A1", valueInputOption="RAW",
                                     body={"values": [TIEU_DE]}).execute()
        self._san_sang = True

    def ghi(self, kenh: str, psid: str, ten: str, sdt: str, nhu_cau: str, ly_do: str, luc: datetime) -> None:
        self._dam_bao()
        self.svc.values().append(
            spreadsheetId=self.id, range=f"'{TAB}'!A1", valueInputOption="RAW", insertDataOption="INSERT_ROWS",
            body={"values": [[luc.strftime("%d/%m/%Y %H:%M"), kenh, psid, ten, sdt, nhu_cau, ly_do, "Mới", LINK_HOP_THU]]},
        ).execute()


def gui_email(noi_dung: str) -> bool:
    return gui_email_chi_tiet(noi_dung)[0]


def gui_email_chi_tiet(noi_dung: str) -> tuple[bool, str]:
    """Gửi email báo nhân viên. Trả về (thành công, lý do nếu lỗi).

    Ưu tiên Google Apps Script (EMAIL_WEBHOOK_URL + EMAIL_WEBHOOK_SECRET): đi qua HTTPS nên chạy được trên Render miễn phí,
    vì gói miễn phí của Render chặn cổng SMTP. Nếu không có thì thử SMTP (SMTP_USER, SMTP_PASSWORD, NOTIFY_EMAIL).
    """
    tieu_de = "Khách mới cần xử lý: " + (noi_dung.splitlines()[0] if noi_dung else "")[:80]
    url, bi_mat = os.environ.get("EMAIL_WEBHOOK_URL", "").strip(), os.environ.get("EMAIL_WEBHOOK_SECRET", "").strip()
    if url and bi_mat:
        try:
            r = requests.post(url, json={"secret": bi_mat, "subject": tieu_de, "body": noi_dung[:5000]}, timeout=30)
        except requests.RequestException as e:
            return False, f"Không gọi được địa chỉ Apps Script ({type(e).__name__}). Kiểm tra EMAIL_WEBHOOK_URL có đúng và đủ không."
        kq = r.text.strip()
        if r.status_code == 200 and kq == "ok":
            return True, ""
        if kq == "forbidden":
            return False, "Apps Script từ chối: chuỗi bí mật không trùng. EMAIL_WEBHOOK_SECRET trên Render phải giống hệt dòng MAT_KHAU trong mã."
        if kq.startswith("loi"):
            chi_tiet = kq[3:].lstrip(": ").strip()[:200]
            return False, ("Apps Script chạy nhưng gửi thư lỗi" + (f": {chi_tiet}" if chi_tiet else
                           ". Cập nhật mã mới trong Apps Script để thấy chi tiết lỗi.") )
        if kq.lower().startswith(("<!doctype", "<html")):
            return False, ("Google trả về trang web thay vì kết quả. Thường do triển khai chưa chọn 'Người có quyền truy cập: Bất kỳ ai', "
                           "hoặc chưa cấp quyền, hoặc dùng địa chỉ /dev thay vì /exec. Triển khai lại cho đúng.")
        return False, f"Apps Script trả về mã {r.status_code}. Kiểm tra lại địa chỉ EMAIL_WEBHOOK_URL."
    user, mat_khau = os.environ.get("SMTP_USER", "").strip(), os.environ.get("SMTP_PASSWORD", "").replace(" ", "")
    nguoi_nhan = [e.strip() for e in (os.environ.get("NOTIFY_EMAIL", "") or user).split(",") if e.strip()]
    if not (user and mat_khau and nguoi_nhan):
        return False, "Chưa cấu hình email."
    msg = EmailMessage()
    msg["Subject"] = tieu_de
    msg["From"], msg["To"] = user, ", ".join(nguoi_nhan)
    msg.set_content(noi_dung[:5000])
    try:
        with smtplib.SMTP_SSL(os.environ.get("SMTP_HOST", "smtp.gmail.com"), 465, timeout=20) as smtp:
            smtp.login(user, mat_khau)
            smtp.send_message(msg)
        return True, ""
    except (smtplib.SMTPException, OSError) as e:
        return False, f"SMTP lỗi ({type(e).__name__}). Gói Render miễn phí chặn SMTP, hãy dùng Google Apps Script."


def email_da_cau_hinh() -> bool:
    kieu_web = os.environ.get("EMAIL_WEBHOOK_URL", "").strip() and os.environ.get("EMAIL_WEBHOOK_SECRET", "").strip()
    return bool(kieu_web or (os.environ.get("SMTP_USER", "").strip() and os.environ.get("SMTP_PASSWORD", "").strip()))


def bao_nhan_vien(noi_dung: str) -> None:
    """Báo nhân viên qua email và/hoặc Telegram, tùy cái nào đã cấu hình. Không cấu hình gì thì bỏ qua."""
    gui_email(noi_dung)
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(), os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not (token and chat):
        return
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat, "text": noi_dung[:3500]}, timeout=15)
    except requests.RequestException:
        pass
