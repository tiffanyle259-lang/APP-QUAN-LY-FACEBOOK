"""Ghi khách quan tâm vào tab 'Khách hàng' của Google Sheet và báo nhân viên qua Telegram (nếu cấu hình)."""

from __future__ import annotations

import os
from datetime import datetime

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


def bao_nhan_vien(noi_dung: str) -> None:
    """Gửi tin Telegram nếu có TELEGRAM_BOT_TOKEN và TELEGRAM_CHAT_ID; không có thì bỏ qua."""
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(), os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not (token and chat):
        return
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat, "text": noi_dung[:3500]}, timeout=15)
    except requests.RequestException:
        pass
