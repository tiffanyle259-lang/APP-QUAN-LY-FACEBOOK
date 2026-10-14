"""Báo cáo tương tác hằng tuần của Fanpage: số liệu từ Facebook, lưu vào tab 'Báo cáo tuần' của Google Sheet."""

from __future__ import annotations

from datetime import datetime, timedelta

TAB = "Báo cáo tuần"
TIEU_DE = ["Ngày chạy", "Người theo dõi", "Thay đổi so với tuần trước", "Số bài", "Cảm xúc", "Bình luận", "Chia sẻ",
           "Khách mới trong tuần", "Bài nổi bật"]


def diem_bai(b: dict) -> int:
    """Điểm tương tác: bình luận và chia sẻ quý hơn lượt cảm xúc."""
    return b["cam_xuc"] + 2 * b["binh_luan"] + 3 * b["chia_se"]


def chuan_bai(raw: dict) -> dict:
    return {"id": raw.get("id", ""), "luc": raw.get("created_time", ""), "noi_dung": (raw.get("message") or "").strip(),
            "link": raw.get("permalink_url", ""),
            "cam_xuc": int(((raw.get("reactions") or {}).get("summary") or {}).get("total_count") or 0),
            "binh_luan": int(((raw.get("comments") or {}).get("summary") or {}).get("total_count") or 0),
            "chia_se": int((raw.get("shares") or {}).get("count") or 0)}


def tinh(bai_tho: list[dict], nguoi_theo_doi: int, nguoi_tuan_truoc: int | None, khach_moi: int,
         hom_nay: datetime) -> list[str]:
    """Dòng báo cáo (theo TIEU_DE)."""
    bai = [chuan_bai(b) for b in bai_tho]
    top = sorted(bai, key=diem_bai, reverse=True)[:3]
    top_text = " | ".join(
        f"{(b['noi_dung'].splitlines() or [''])[0][:60]} (cảm xúc {b['cam_xuc']}, bình luận {b['binh_luan']}, "
        f"chia sẻ {b['chia_se']}) {b['link']}" for b in top if diem_bai(b) > 0) or "Chưa có bài nào có tương tác"
    doi = "" if nguoi_tuan_truoc is None else f"{nguoi_theo_doi - nguoi_tuan_truoc:+d}"
    return [hom_nay.strftime("%d/%m/%Y"), str(nguoi_theo_doi), doi, str(len(bai)),
            str(sum(b["cam_xuc"] for b in bai)), str(sum(b["binh_luan"] for b in bai)),
            str(sum(b["chia_se"] for b in bai)), str(khach_moi), top_text]


def dem_khach_moi(dong_khach: list[list[str]], tu_ngay: datetime) -> int:
    n = 0
    for r in dong_khach:
        try:
            if datetime.strptime(str(r[0]).strip(), "%d/%m/%Y %H:%M") >= tu_ngay.replace(tzinfo=None):
                n += 1
        except (ValueError, IndexError):
            continue
    return n


def doc_bao_cao(svc, sheet_id: str) -> list[dict]:
    """Các dòng báo cáo đã lưu (svc = sheets.spreadsheets()). Tab chưa có thì []."""
    try:
        dong = svc.values().get(spreadsheetId=sheet_id, range=f"'{TAB}'!A2:I200").execute().get("values", [])
    except Exception as e:
        if "Unable to parse range" in str(e) or "400" in str(e):
            return []
        raise
    ket_qua = []
    for r in dong:
        r = (list(r) + [""] * 9)[:9]
        if r[0]:
            ket_qua.append(dict(zip(["ngay", "nguoi", "doi", "bai", "cam_xuc", "binh_luan", "chia_se", "khach", "top"], r)))
    return ket_qua[::-1][:12]  # mới nhất trước


class SoBaoCao:
    def __init__(self, sheets_service, sheet_id: str):
        self.svc = sheets_service.spreadsheets()
        self.id = sheet_id

    def _dam_bao(self) -> None:
        info = self.svc.get(spreadsheetId=self.id, fields="sheets.properties").execute()
        if not any(s["properties"]["title"] == TAB for s in info["sheets"]):
            self.svc.batchUpdate(spreadsheetId=self.id,
                                 body={"requests": [{"addSheet": {"properties": {"title": TAB}}}]}).execute()
        co = self.svc.values().get(spreadsheetId=self.id, range=f"'{TAB}'!A1:I1").execute().get("values")
        if not co:
            self.svc.values().update(spreadsheetId=self.id, range=f"'{TAB}'!A1", valueInputOption="RAW",
                                     body={"values": [TIEU_DE]}).execute()

    def nguoi_theo_doi_cuoi(self) -> int | None:
        cu = doc_bao_cao(self.svc, self.id)
        try:
            return int(cu[0]["nguoi"]) if cu else None
        except ValueError:
            return None

    def ghi(self, dong: list[str]) -> None:
        self._dam_bao()
        self.svc.values().append(spreadsheetId=self.id, range=f"'{TAB}'!A1", valueInputOption="RAW",
                                 insertDataOption="INSERT_ROWS", body={"values": [dong]}).execute()


def noi_dung_email(dong: list[str], ten_page: str) -> str:
    doi = f" ({dong[2]} so với tuần trước)" if dong[2] else ""
    return (f"Báo cáo tuần {dong[0]} - {ten_page}\n\n"
            f"Người theo dõi: {dong[1]}{doi}\nSố bài đã đăng: {dong[3]}\n"
            f"Cảm xúc: {dong[4]} | Bình luận: {dong[5]} | Chia sẻ: {dong[6]}\n"
            f"Khách mới để lại thông tin trong tuần: {dong[7]}\n\nBài nổi bật:\n"
            + "\n".join(f"- {t.strip()}" for t in dong[8].split(" | ")))
