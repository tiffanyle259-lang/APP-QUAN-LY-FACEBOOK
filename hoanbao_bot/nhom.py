"""Danh sách nhóm Facebook để nhân viên đăng bài tay: lưu trong tab 'Nhóm' của Google Sheet.

App không tự đăng vào nhóm (Meta không cho). App chỉ nhớ nhóm, gợi ý nhóm sẵn sàng, soạn bài và ghi ngày đã đăng."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

TAB = "Nhóm"
TIEU_DE = ["Tên nhóm", "Link", "Ngành", "Luật nhóm", "Cách nhau (ngày)", "Lần đăng cuối", "Số lần đăng", "Trạng thái"]
NGANH = ["Giày dép, túi da", "Sofa, nệm, nội thất", "Đồ gỗ, tủ bếp", "Nội thất ô tô", "Đại lý, vật tư", "Khác"]
DANG_DUNG, TAM_DUNG = "Đang dùng", "Tạm dừng"
CACH_MAC_DINH = 7
_LINK = re.compile(r"^https://(?:www\.|m\.|web\.|mbasic\.)?(?:facebook\.com|fb\.com)/groups/[\w.\-%]+/?(?:\?[^\s]*)?$", re.I)


class LoiNhom(ValueError):
    pass


def chuan_link(link: str) -> str:
    link = (link or "").strip()
    if not _LINK.match(link):
        raise LoiNhom("Link nhóm phải có dạng https://www.facebook.com/groups/… (mở nhóm rồi sao chép từ thanh địa chỉ).")
    return link


def doc_ngay(text: str) -> date | None:
    for dinh_dang in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime((text or "").strip(), dinh_dang).date()
        except ValueError:
            continue
    return None


def tinh_trang(nhom: dict, hom_nay: date) -> tuple[bool, int]:
    """(sẵn sàng đăng không, số ngày còn phải chờ)."""
    if nhom["trang_thai"] == TAM_DUNG:
        return False, 0
    cuoi = doc_ngay(nhom["lan_cuoi"])
    if not cuoi:
        return True, 0
    con = (cuoi + timedelta(days=nhom["cach"])) - hom_nay
    return con.days <= 0, max(con.days, 0)


def dong_thanh_nhom(i: int, r: list) -> dict:
    r = (list(r) + [""] * 8)[:8]
    try:
        cach = max(0, int(str(r[4]).strip() or CACH_MAC_DINH))
    except ValueError:
        cach = CACH_MAC_DINH
    return {"dong": i, "ten": str(r[0]).strip(), "link": str(r[1]).strip(), "nganh": str(r[2]).strip() or "Khác",
            "luat": str(r[3]).strip(), "cach": cach, "lan_cuoi": str(r[5]).strip(),
            "so_lan": str(r[6]).strip() or "0", "trang_thai": str(r[7]).strip() or DANG_DUNG}


def doc_nhom(svc, sheet_id: str) -> list[dict]:
    """Đọc danh sách nhóm (svc là sheets.spreadsheets()). Tab chưa có thì trả về [] (tạo khi thêm nhóm đầu tiên)."""
    try:
        dong = svc.values().get(
            spreadsheetId=sheet_id, range=f"'{TAB}'!A2:H500").execute().get("values", [])
    except Exception as e:  # tab chưa tồn tại: Google trả lỗi 400 "Unable to parse range"
        if "Unable to parse range" in str(e) or "400" in str(e):
            return []
        raise
    return [dong_thanh_nhom(i, r) for i, r in enumerate(dong, start=2) if r and str(r[0]).strip()]


LUAT_CHUA_KIEM = "Chưa kiểm tra nội quy: xem mục Quy tắc của nhóm trước khi đăng."


def doan_nganh(text: str) -> str:
    t = (text or "").lower()
    if any(k in t for k in ("sofa", "nệm", "mút")):
        return "Sofa, nệm, nội thất"
    if any(k in t for k in ("giày", "dép", "túi")):
        return "Giày dép, túi da"
    if any(k in t for k in ("gỗ", "mộc", "tủ bếp")):
        return "Đồ gỗ, tủ bếp"
    if "nội thất" in t:
        return "Sofa, nệm, nội thất"
    if "ô tô" in t or "xe" in t.split():
        return "Nội thất ô tô"
    return "Khác"


def doc_van_ban(van_ban: str) -> tuple[list[list[str]], list[str]]:
    """Mỗi dòng 'Tên | link | ngành (tùy chọn) | luật (tùy chọn)' thành dòng Sheet. Trả về (dòng hợp lệ, lý do dòng bị bỏ)."""
    rows, bo, thay = [], [], set()
    for i, dong in enumerate(van_ban.splitlines(), start=1):
        if not dong.strip():
            continue
        cot = [c.strip() for c in dong.split("|")]
        if len(cot) < 2 or not cot[0]:
            bo.append(f"Dòng {i}: thiếu tên hoặc link")
            continue
        try:
            link = chuan_link(cot[1])
        except LoiNhom:
            bo.append(f"Dòng {i} ({cot[0][:30]}): link không đúng dạng")
            continue
        khoa = link.rstrip("/").lower()
        if khoa in thay:
            bo.append(f"Dòng {i} ({cot[0][:30]}): trùng link trong danh sách")
            continue
        thay.add(khoa)
        nganh = cot[2] if len(cot) > 2 and cot[2] in NGANH else doan_nganh((cot[2] if len(cot) > 2 else "") or cot[0])
        luat = (cot[3] if len(cot) > 3 and cot[3] else LUAT_CHUA_KIEM)[:500]
        tt = cot[4] if len(cot) > 4 and cot[4] in (DANG_DUNG, TAM_DUNG) else DANG_DUNG
        rows.append([cot[0][:120], link, nganh, luat, str(CACH_MAC_DINH), "", "0", tt])
    return rows, bo


class SoNhom:
    def __init__(self, sheets_service, sheet_id: str):
        self.svc = sheets_service.spreadsheets()
        self.id = sheet_id

    def _dam_bao(self) -> None:
        info = self.svc.get(spreadsheetId=self.id, fields="sheets.properties").execute()
        tab_id = next((s["properties"]["sheetId"] for s in info["sheets"] if s["properties"]["title"] == TAB), None)
        if tab_id is None:
            r = self.svc.batchUpdate(spreadsheetId=self.id,
                                     body={"requests": [{"addSheet": {"properties": {"title": TAB}}}]}).execute()
            tab_id = r["replies"][0]["addSheet"]["properties"]["sheetId"]
        co = self.svc.values().get(spreadsheetId=self.id, range=f"'{TAB}'!A1:H1").execute().get("values")
        if not co:
            self.svc.values().update(spreadsheetId=self.id, range=f"'{TAB}'!A1", valueInputOption="RAW",
                                     body={"values": [TIEU_DE]}).execute()

    def doc(self) -> list[dict]:
        return doc_nhom(self.svc, self.id)

    def them(self, ten: str, link: str, nganh: str, luat: str, cach: int) -> None:
        ten = (ten or "").strip()
        if not ten or len(ten) > 120:
            raise LoiNhom("Cần nhập tên nhóm (tối đa 120 ký tự).")
        link = chuan_link(link)
        if nganh not in NGANH:
            raise LoiNhom("Ngành không hợp lệ.")
        if not 0 <= cach <= 90:
            raise LoiNhom("Số ngày giữa hai lần đăng phải từ 0 đến 90.")
        self._dam_bao()
        da_co = {n["link"].rstrip("/").lower() for n in self.doc()}
        if link.rstrip("/").lower() in da_co:
            raise LoiNhom("Nhóm này đã có trong danh sách.")
        self.svc.values().append(
            spreadsheetId=self.id, range=f"'{TAB}'!A1", valueInputOption="RAW", insertDataOption="INSERT_ROWS",
            body={"values": [[ten, link, nganh, (luat or "").strip()[:500], str(cach), "", "0", DANG_DUNG]]}).execute()

    def nhap(self, rows: list[list[str]]) -> tuple[int, int]:
        """Nhập nhiều nhóm một lần. Nhóm mới thì thêm; nhóm đã có (cùng link) thì cập nhật ngành, luật, trạng thái
        (giữ nguyên ngày đăng và số lần đăng). Trả về (số thêm, số cập nhật)."""
        self._dam_bao()
        co = {n["link"].rstrip("/").lower(): n["dong"] for n in self.doc()}
        moi = [r for r in rows if r[1].rstrip("/").lower() not in co]
        cu = [(co[r[1].rstrip("/").lower()], r) for r in rows if r[1].rstrip("/").lower() in co]
        for i in range(0, len(moi), 100):
            self.svc.values().append(
                spreadsheetId=self.id, range=f"'{TAB}'!A1", valueInputOption="RAW", insertDataOption="INSERT_ROWS",
                body={"values": moi[i:i + 100]}).execute()
        if cu:
            data = []
            for dong, r in cu:
                data.append({"range": f"'{TAB}'!C{dong}:D{dong}", "values": [[r[2], r[3]]]})
                data.append({"range": f"'{TAB}'!H{dong}", "values": [[r[7]]]})
            self.svc.values().batchUpdate(spreadsheetId=self.id,
                                          body={"valueInputOption": "RAW", "data": data}).execute()
        return len(moi), len(cu)

    def da_dang(self, dong: int, hom_nay: date) -> None:
        n = self._nhom(dong)
        try:
            so = int(n["so_lan"]) + 1
        except ValueError:
            so = 1
        self.svc.values().update(spreadsheetId=self.id, range=f"'{TAB}'!F{dong}:G{dong}", valueInputOption="RAW",
                                 body={"values": [[hom_nay.strftime("%d/%m/%Y"), str(so)]]}).execute()

    def dat_trang_thai(self, dong: int, trang_thai: str) -> None:
        if trang_thai not in (DANG_DUNG, TAM_DUNG):
            raise LoiNhom("Trạng thái không hợp lệ.")
        self._nhom(dong)
        self.svc.values().update(spreadsheetId=self.id, range=f"'{TAB}'!H{dong}", valueInputOption="RAW",
                                 body={"values": [[trang_thai]]}).execute()

    def _nhom(self, dong: int) -> dict:
        if not 2 <= dong <= 500:
            raise LoiNhom("Dòng nhóm không hợp lệ.")
        n = next((x for x in self.doc() if x["dong"] == dong), None)
        if not n:
            raise LoiNhom("Không tìm thấy nhóm này trong Sheet.")
        return n

    def lay(self, dong: int) -> dict:
        return self._nhom(dong)

