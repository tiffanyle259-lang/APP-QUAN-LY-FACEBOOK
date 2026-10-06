"""Lập kế hoạch bài đăng cho 1 tuần theo sheet "Lịch chủ đề"."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .du_lieu import DuLieuNen, KhungLich, NhomKhach, SanPham

_SLUG = re.compile(r"thư mục ([a-z0-9]+(?:-[a-z0-9]+)+)")


def bo_dau(text: str) -> str:
    """'Keo dán Giày' -> 'keo dan giay' (để so khớp tên file)."""
    text = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def tu_khoa(*texts: str) -> list[str]:
    tu = []
    for t in texts:
        for w in bo_dau(t).split():
            if len(w) >= 3 and w not in tu and w not in {"keo", "dan", "cao", "cap", "xuong", "cho"}:
                tu.append(w)
    return tu


@dataclass
class BaiKeHoach:
    ma_bai: str
    ngay: date
    thoi_diem: datetime
    khung: KhungLich
    san_pham: list[SanPham] = field(default_factory=list)
    nhom_khach: NhomKhach | None = None
    thu_muc: list[str] = field(default_factory=list)  # theo thứ tự ưu tiên
    uu_tien_video: bool = False
    tu_khoa_media: list[str] = field(default_factory=list)


def thu_hai_tuan_sau(hom_nay: date) -> date:
    return hom_nay + timedelta(days=7 - hom_nay.weekday())


def _xoay(ds: list, so_tuan: int, lech: int = 0):
    return ds[(so_tuan + lech) % len(ds)] if ds else None


def lap_ke_hoach(du_lieu: DuLieuNen, thu_hai: date, cau_hinh_thu_muc: dict, mui_gio: ZoneInfo) -> list[BaiKeHoach]:
    if thu_hai.weekday() != 0:
        raise ValueError(f"{thu_hai} không phải Thứ 2")
    so_tuan = thu_hai.toordinal() // 7

    # Sản phẩm giới thiệu trong tuần: ưu tiên cột "Chủ lực?" = Có; nếu chưa chọn thì
    # xoay vòng các loại keo (không tính phụ gia) có đủ ứng dụng + ưu điểm.
    chu_luc = [sp for sp in du_lieu.san_pham if sp.chu_luc] or [
        sp for sp in du_lieu.san_pham
        if not sp.la_phu_gia and {"Ứng dụng / ngành dùng", "Ưu điểm nổi bật"} <= sp.thong_tin.keys()
    ]
    co_cach_dung = [
        sp for sp in du_lieu.san_pham
        if {"Thời gian khô / cách dùng", "Lưu ý khi dùng"} & sp.thong_tin.keys() and "Ưu điểm nổi bật" in sp.thong_tin
    ]
    nganh = [nk for nk in du_lieu.nhom_khach if nk.mua_qua.lower() != "đại lý"]
    dai_ly = next((nk for nk in du_lieu.nhom_khach if nk.mua_qua.lower() == "đại lý"), None)

    sp_tuan = _xoay(chu_luc, so_tuan)
    sp_meo = _xoay(co_cach_dung, so_tuan, lech=3)
    nganh_tuan = _xoay(nganh, so_tuan)
    # Bài xoay quanh sản phẩm của tuần thì đi với nhóm khách dùng sản phẩm đó.
    nganh_cua_sp = next((nk for nk in nganh if sp_tuan and sp_tuan.ma in nk.ma_san_pham), nganh_tuan)
    theo_nganh = cau_hinh_thu_muc.get("theo_nganh", {})

    ds = []
    for khung in du_lieu.lich:
        ngay = thu_hai + timedelta(days=khung.thu)
        gio, phut = map(int, khung.gio_dang.split(":"))
        loai = khung.loai_bai.lower()
        nguon = khung.nguon_media.lower()

        if "mẹo" in loai:
            san_pham, nhom = [sp_meo], None
        elif "chính sách" in loai or "nhà máy" in loai:
            san_pham, nhom = [], dai_ly
        elif "ngành" in loai:
            nhom = nganh_tuan
            san_pham = [sp for m in nhom.ma_san_pham if (sp := du_lieu.tim_san_pham(m))] if nhom else []
        else:
            san_pham, nhom = [sp_tuan], nganh_cua_sp
        san_pham = [sp for sp in san_pham if sp]

        thu_muc: list[str] = []
        if "sản phẩm" in nguon:
            thu_muc += [sp.thu_muc for sp in san_pham if sp.thu_muc]
        elif "ngành" in nguon and nhom and nhom.ten in theo_nganh:
            thu_muc.append(theo_nganh[nhom.ten])
        elif "chung" in nguon and cau_hinh_thu_muc.get("anh_chung"):
            thu_muc.append(cau_hinh_thu_muc["anh_chung"])
        elif m := _SLUG.search(nguon):
            thu_muc.append(m.group(1))
        # Dự phòng: thư mục của sản phẩm liên quan.
        thu_muc += [sp.thu_muc for sp in san_pham if sp.thu_muc and sp.thu_muc not in thu_muc]

        ds.append(BaiKeHoach(
            ma_bai=f"{ngay.isoformat()}_{bo_dau(khung.ten_thu).replace(' ', '')}",
            ngay=ngay,
            thoi_diem=datetime.combine(ngay, time(gio, phut), tzinfo=mui_gio),
            khung=khung,
            san_pham=san_pham,
            nhom_khach=nhom,
            thu_muc=thu_muc,
            uu_tien_video="video" in loai or "video" in nguon,
            tu_khoa_media=tu_khoa(*(f"{sp.ma} {sp.ten}" for sp in san_pham), nhom.ten if nhom else ""),
        ))
    return ds
