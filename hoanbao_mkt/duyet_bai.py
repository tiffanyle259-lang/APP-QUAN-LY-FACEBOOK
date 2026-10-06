"""Google Sheet duyệt bài: nơi xem/sửa bản nháp, bật/tắt chế độ duyệt, và nhật ký đăng."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time

TAB_BAI = "Bài viết"
TAB_CAI_DAT = "Cài đặt"
TIEU_DE = ["Mã bài", "Ngày đăng", "Giờ", "Loại bài", "Nội dung (sửa trực tiếp)",
           "Ảnh/Video (dán link Drive khác để đổi)", "Trạng thái", "Ghi chú", "Facebook ID"]

CHO_DUYET = "Chờ duyệt"
DUYET = "Duyệt"
BO = "Bỏ"
DA_LEN_LICH = "Đã lên lịch"
LOI = "Lỗi"
TRANG_THAI = [CHO_DUYET, DUYET, BO, DA_LEN_LICH, LOI]

_DRIVE_ID = re.compile(r"(?:/d/|[?&]id=)([A-Za-z0-9_-]{10,})")


def drive_id_tu_link(link: str) -> str | None:
    link = (link or "").strip()
    if not link:
        return None
    m = _DRIVE_ID.search(link)
    if m:
        return m.group(1)
    return link if re.fullmatch(r"[A-Za-z0-9_-]{20,}", link) else None


def doc_ngay(text: str) -> date:
    text = text.strip()
    for dang in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(text, dang).date()
        except ValueError:
            pass
    raise ValueError(f"Không hiểu ngày '{text}' (dùng dạng 2026-10-12 hoặc 12/10/2026)")


def doc_gio(text: str) -> time:
    m = re.match(r"^\s*(\d{1,2})[:h](\d{2})", text or "")
    if not m:
        raise ValueError(f"Không hiểu giờ '{text}' (dùng dạng 08:00)")
    return time(int(m.group(1)), int(m.group(2)))


@dataclass
class DongBai:
    dong: int  # số dòng trong Sheet (1-based)
    ma_bai: str
    ngay: str
    gio: str
    loai_bai: str
    noi_dung: str
    media: str
    trang_thai: str
    ghi_chu: str
    facebook_id: str


class SheetDuyet:
    def __init__(self, sheets_service, sheet_id: str):
        self.svc = sheets_service.spreadsheets()
        self.id = sheet_id

    def dam_bao_cau_truc(self, che_do_duyet_mac_dinh: bool) -> None:
        """Tạo tab và tiêu đề nếu Sheet còn trống."""
        info = self.svc.get(spreadsheetId=self.id, fields="sheets.properties").execute()
        co_san = {s["properties"]["title"]: s["properties"]["sheetId"] for s in info["sheets"]}
        yeu_cau = [{"addSheet": {"properties": {"title": t}}} for t in (TAB_BAI, TAB_CAI_DAT) if t not in co_san]
        if yeu_cau:
            r = self.svc.batchUpdate(spreadsheetId=self.id, body={"requests": yeu_cau}).execute()
            for rep in r["replies"]:
                p = rep["addSheet"]["properties"]
                co_san[p["title"]] = p["sheetId"]

        if not self._lay(f"'{TAB_BAI}'!A1:I1"):
            self._ghi(f"'{TAB_BAI}'!A1", [TIEU_DE])
            self._dropdown(co_san[TAB_BAI], 1, 1000, 6, TRANG_THAI)
        if not self._lay(f"'{TAB_CAI_DAT}'!A1:B1"):
            self._ghi(f"'{TAB_CAI_DAT}'!A1", [
                ["Chế độ duyệt", "BẬT" if che_do_duyet_mac_dinh else "TẮT"],
                ["Giải thích", "BẬT: bài mới ở trạng thái 'Chờ duyệt', đổi thành 'Duyệt' thì app mới lên lịch. "
                               "TẮT: app tự lên lịch luôn (trừ bài có cảnh báo)."],
            ])
            self._dropdown(co_san[TAB_CAI_DAT], 0, 1, 1, ["BẬT", "TẮT"])

    def che_do_duyet(self, mac_dinh: bool) -> bool:
        gia_tri = self._lay(f"'{TAB_CAI_DAT}'!B1")
        if not gia_tri or not gia_tri[0]:
            return mac_dinh
        return gia_tri[0][0].strip().upper() not in {"TẮT", "TAT", "OFF", "KHÔNG"}

    def doc_tat_ca(self) -> list[DongBai]:
        ds = []
        for i, dong in enumerate(self._lay(f"'{TAB_BAI}'!A2:I"), start=2):
            dong = list(dong) + [""] * (9 - len(dong))
            if dong[0].strip():
                ds.append(DongBai(i, *[str(c) for c in dong[:9]]))
        return ds

    def them(self, dong_moi: list[list[str]]) -> int:
        """Thêm bài mới, bỏ qua mã bài đã có (chạy lại không bị trùng)."""
        da_co = {d.ma_bai for d in self.doc_tat_ca()}
        moi = [d for d in dong_moi if d[0] not in da_co]
        if moi:
            self.svc.values().append(
                spreadsheetId=self.id, range=f"'{TAB_BAI}'!A1", valueInputOption="RAW",
                insertDataOption="INSERT_ROWS", body={"values": moi},
            ).execute()
        return len(moi)

    def cap_nhat(self, dong: int, trang_thai: str, ghi_chu: str, facebook_id: str = "") -> None:
        self._ghi(f"'{TAB_BAI}'!G{dong}:I{dong}", [[trang_thai, ghi_chu, facebook_id]])

    def _lay(self, vung: str) -> list[list[str]]:
        return self.svc.values().get(spreadsheetId=self.id, range=vung).execute().get("values", [])

    def _ghi(self, vung: str, gia_tri: list[list[str]]) -> None:
        self.svc.values().update(
            spreadsheetId=self.id, range=vung, valueInputOption="RAW", body={"values": gia_tri}
        ).execute()

    def _dropdown(self, tab_id: int, dong_dau: int, dong_cuoi: int, cot: int, lua_chon: list[str]) -> None:
        self.svc.batchUpdate(spreadsheetId=self.id, body={"requests": [{"setDataValidation": {
            "range": {"sheetId": tab_id, "startRowIndex": dong_dau, "endRowIndex": dong_cuoi,
                      "startColumnIndex": cot, "endColumnIndex": cot + 1},
            "rule": {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": v} for v in lua_chon]},
                     "showCustomUi": True, "strict": False},
        }}]}).execute()
