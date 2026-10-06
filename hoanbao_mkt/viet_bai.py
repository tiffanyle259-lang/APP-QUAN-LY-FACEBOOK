"""Dùng Claude viết nội dung bài cho cả tuần, chỉ dựa trên dữ liệu trong file Excel."""

from __future__ import annotations

import re

import anthropic
from pydantic import BaseModel, Field

from .du_lieu import DuLieuNen, NhomKhach, SanPham
from .ke_hoach import BaiKeHoach

HUONG_DAN_HE_THONG = """Bạn là người viết nội dung fanpage Facebook cho thương hiệu keo dán Golden Lion (Sư Tử Vàng) của Công ty TNHH Hoàn Bảo, TP.HCM. Khách đọc là chủ xưởng, thợ và đại lý trong ngành giày dép, sofa–nệm, đồ gỗ, nội thất ô tô.

QUY TẮC BẮT BUỘC
1. Chỉ dùng thông tin có trong phần DỮ LIỆU của từng bài. Không thêm thông số, con số, chứng nhận, giá, quy cách, tên khách hàng, lời chứng thực hay chính sách nào không có trong DỮ LIỆU. Không chắc thì không viết.
2. Không nêu giá. Muốn biết giá thì mời khách nhắn tin hoặc gọi.
3. Bài "khách hàng thật": không bịa tên xưởng, câu nói hay số liệu của khách; chỉ dùng số liệu có sẵn (ví dụ "hơn 500 khách hàng sản xuất") và mời khách chia sẻ trải nghiệm.
4. Tiếng Việt tự nhiên, gần gũi, xưng "Golden Lion" hoặc "bên em", gọi khách là "anh/chị". Dài 80–180 chữ, câu ngắn, xuống dòng dễ đọc, tối đa 4 emoji.
5. Cuối bài có lời kêu gọi: Hotline/Zalo và website lấy đúng từ DỮ LIỆU công ty (nếu có link sản phẩm thì dùng link đó). Sau đó 3–5 hashtag, luôn có #GoldenLion.
6. Các bài trong tuần không lặp mở bài hay câu kêu gọi giống nhau.
7. tu_khoa_media: 3–6 từ khóa không dấu, viết thường (ví dụ "sofa", "phun", "de giay") mô tả ảnh/video hợp với bài, để chọn file trong kho."""


class BaiViet(BaseModel):
    ma_bai: str
    noi_dung: str = Field(description="Toàn bộ nội dung bài, gồm cả lời kêu gọi và hashtag")
    tu_khoa_media: list[str]


class BaiVietTuan(BaseModel):
    bai: list[BaiViet]


def _khoi_san_pham(sp: SanPham) -> str:
    dong = [f"- Sản phẩm {sp.ma}:"] + [f"    {k}: {v}" for k, v in sp.thong_tin.items()]
    return "\n".join(dong)


# Thông tin nội bộ, không cần cho bài đăng.
_COT_NOI_BO = {"Kênh tiếp cận", "Mua qua", "Ưu tiên"}


def _khoi_nhom_khach(nk: NhomKhach) -> str:
    dong = [f"    {k}: {v}" for k, v in nk.thong_tin.items() if k not in _COT_NOI_BO]
    return "\n".join(["- Nhóm khách:", *dong])


def du_lieu_cua_bai(bai: BaiKeHoach, du_lieu: DuLieuNen) -> str:
    phan = ["Công ty:", *(f"- {d}" for d in du_lieu.cong_ty)]
    phan += [_khoi_san_pham(sp) for sp in bai.san_pham]
    if bai.nhom_khach:
        phan.append(_khoi_nhom_khach(bai.nhom_khach))
    return "\n".join(phan)


def tao_yeu_cau(ds_bai: list[BaiKeHoach], du_lieu: DuLieuNen) -> str:
    khoi = []
    for bai in ds_bai:
        k = bai.khung
        khoi.append(
            f"### BÀI {bai.ma_bai} ({k.ten_thu} {bai.ngay:%d/%m}, đăng {k.gio_dang})\n"
            f"Loại bài: {k.loai_bai}\nMục tiêu: {k.muc_tieu}\nGợi ý: {k.goi_y}\n"
            f"Kèm {'video' if bai.uu_tien_video else 'ảnh'} lấy từ kho.\n"
            f"DỮ LIỆU:\n{du_lieu_cua_bai(bai, du_lieu)}"
        )
    return "Viết nội dung cho các bài sau, mỗi bài một mục, giữ nguyên ma_bai.\n\n" + "\n\n".join(khoi)


_SO = re.compile(r"\d+(?:[.,]\d+)*")


def so_lieu_la(noi_dung: str, nguon: str) -> list[str]:
    """Các con số trong bài mà không xuất hiện trong dữ liệu nguồn (dấu hiệu bịa)."""
    def gon(so: str) -> str:
        return so.replace(".", "").replace(",", "")

    nguon_so = {gon(so) for so in _SO.findall(nguon)}
    la = []
    for so in _SO.findall(noi_dung):
        if gon(so) not in nguon_so and so not in la:
            la.append(so)
    return la


def viet_ca_tuan(ds_bai: list[BaiKeHoach], du_lieu: DuLieuNen, model: str, effort: str) -> dict[str, BaiViet]:
    client = anthropic.Anthropic()
    phan_hoi = client.beta.messages.parse(
        model=model,
        max_tokens=16000,
        system=HUONG_DAN_HE_THONG,
        messages=[{"role": "user", "content": tao_yeu_cau(ds_bai, du_lieu)}],
        output_format=BaiVietTuan,
        output_config={"effort": effort},
        # Nếu model chính từ chối, máy chủ tự chuyển sang model dự phòng.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if phan_hoi.stop_reason == "refusal":
        raise RuntimeError("AI từ chối viết bài tuần này.")
    if phan_hoi.stop_reason == "max_tokens" or phan_hoi.parsed_output is None:
        raise RuntimeError(f"AI trả kết quả không đầy đủ (stop_reason={phan_hoi.stop_reason}).")
    return {b.ma_bai: b for b in phan_hoi.parsed_output.bai}
