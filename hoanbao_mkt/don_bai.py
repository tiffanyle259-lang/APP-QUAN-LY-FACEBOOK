"""Dọn bài trong Google Sheet bằng một lệnh: duyệt hàng loạt bài còn hạn, bỏ hàng loạt bài đã quá giờ."""

from __future__ import annotations

from datetime import datetime, timedelta

from .duyet_bai import BO, CHO_DUYET, DUYET, DongBai, doc_gio, doc_ngay

CAN_KIEM_TRA = ("Kiểm tra số liệu", "Không có ảnh/video")  # bài AI đã cảnh báo thì không tự duyệt hàng loạt
GAN_NHAT_PHUT = 20  # Facebook chỉ nhận giờ hẹn cách hiện tại ít nhất 15 phút, chừa dư 5 phút


def gio_dang(b: DongBai, mui_gio) -> datetime | None:
    try:
        return datetime.combine(doc_ngay(b.ngay), doc_gio(b.gio), tzinfo=mui_gio)
    except Exception:
        return None


def chon_bai(ds: list[DongBai], viec: str, bay_gio: datetime, mui_gio) -> tuple[list[DongBai], list[tuple[DongBai, str]]]:
    """viec: 'duyet' (Chờ duyệt còn hạn -> Duyệt) hoặc 'bo-qua-gio' (Chờ duyệt đã quá giờ -> Bỏ).
    Trả về (bài sẽ đổi, bài bỏ qua kèm lý do)."""
    doi, bo_qua = [], []
    for b in ds:
        if b.trang_thai != CHO_DUYET:
            continue
        luc = gio_dang(b, mui_gio)
        if luc is None:
            bo_qua.append((b, "không đọc được ngày giờ"))
        elif viec == "bo-qua-gio":
            (doi if luc < bay_gio else bo_qua).append(b if luc < bay_gio else (b, "còn hạn, giữ nguyên"))
        elif luc < bay_gio + timedelta(minutes=GAN_NHAT_PHUT):
            bo_qua.append((b, "đã quá giờ hoặc quá gần giờ đăng"))
        elif not b.noi_dung.strip():
            bo_qua.append((b, "nội dung trống"))
        elif any(k in (b.ghi_chu or "") for k in CAN_KIEM_TRA):
            bo_qua.append((b, "AI cảnh báo, cần xem tay"))
        else:
            doi.append(b)
    return doi, bo_qua


def trang_thai_moi(viec: str) -> str:
    return BO if viec == "bo-qua-gio" else DUYET
