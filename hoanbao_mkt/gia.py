"""Đối chiếu giá ghi trong bài đăng với bảng giá chính thức (config.yaml, mục bang_gia)."""

from __future__ import annotations

import re

from .ke_hoach import bo_dau

VAT = 1.08
# Cách nhận ra sản phẩm trong nội dung bài (đã bỏ dấu, chữ thường).
NHAN_DIEN = {
    "228": [r"\b228\b"],
    "S-PRO": [r"\bs ?-? ?pro\b", r"\bspro\b"],
    "339": [r"\b339\b"],
    "405A": [r"\b405 ?a?\b"],
    "HP-333": [r"\bhp ?-? ?333\b"],
    "SUPER PRO": [r"\bsuper ?-? ?pro\b", r"\bsuperpro\b"],
    "X66": [r"\bx ?-? ?66\b"],
    "XU LY PU PVC": [r"chat xu ly (?:pu|be mat)", r"\bxl ?-? ?pu\b"],
    "S383": [r"\bs ?-? ?383\b", r"dong ran"],
}
_SO = re.compile(r"(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s*(k\b|tr\b|triệu|nghìn|ngàn|đ\b|₫|vnđ|vnd)", re.I)
# Các số tiền không phải giá sản phẩm (ngưỡng miễn phí vận chuyển).
SO_KHAC = {5_000_000}


def tim_gia(noi_dung: str) -> list[int]:
    """Các số tiền ghi trong bài, đổi ra đồng."""
    ra = []
    for m in _SO.finditer(noi_dung or ""):
        so, dv = m.group(1), m.group(2).lower()
        try:
            if dv in ("tr", "triệu"):
                v = float(so.replace(",", ".")) * 1_000_000
            elif dv in ("k", "nghìn", "ngàn"):
                v = float(so.replace(".", "").replace(",", ".")) * 1000
            else:
                v = float(so.replace(".", "").replace(",", ""))
        except ValueError:
            continue
        if v >= 10_000:
            ra.append(int(round(v)))
    return ra


def san_pham_trong_bai(noi_dung: str) -> list[str]:
    t = bo_dau(noi_dung or "")
    return [ma for ma, mau in NHAN_DIEN.items() if any(re.search(p, t) for p in mau)]


def gia_hop_le(bang_gia: dict, ma: str) -> set[int]:
    g = bang_gia.get(ma) or {}
    goc = {int(v) for v in g.values() if isinstance(v, (int, float))}
    return goc | {int(round(v * VAT)) for v in goc}  # giá niêm yết và giá đã gồm VAT 8%


def kiem_tra(noi_dung: str, bang_gia: dict) -> list[str]:
    """Danh sách lỗi giá trong bài ([] nếu đúng hoặc bài không ghi giá)."""
    gia = [g for g in tim_gia(noi_dung) if g not in SO_KHAC]
    if not gia:
        return []
    sp = san_pham_trong_bai(noi_dung)
    if not sp:
        return [f"ghi giá {g:,}đ nhưng không rõ sản phẩm".replace(",", ".") for g in gia]
    hop_le = set().union(*(gia_hop_le(bang_gia, ma) for ma in sp))
    return [f"giá {g:,}đ không có trong bảng giá của {'/'.join(sp)}".replace(",", ".") for g in gia if g not in hop_le]


# --- Câu cấm (sếp chốt 25/11): chỉ 228 và S-PRO được nói không Toluene; không ghi giá sỉ ---
_CAU_TOLUENE = re.compile(r"[^\n.!?]*(?:cả nhà|mọi dòng|tất cả (?:các )?(?:dòng|loại|sản phẩm))[^\n.!?]*(?:toluene|benzene)[^\n.!?]*[.!?]?[ \t]*", re.I)
_DONG_GIA_SI = re.compile(r"^[^\n]*giá sỉ[^\n]*\n?", re.I | re.M)


def co_cau_cam(noi_dung: str) -> bool:
    t = noi_dung or ""
    return bool(_CAU_TOLUENE.search(t) or _DONG_GIA_SI.search(t))


def lam_sach(noi_dung: str) -> str:
    """Bỏ câu 'cả nhà đều không chứa Toluene/Benzene' và dòng 'giá sỉ ...'; giữ nguyên phần còn lại."""
    t = _CAU_TOLUENE.sub("", noi_dung or "")
    t = _DONG_GIA_SI.sub("", t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()
