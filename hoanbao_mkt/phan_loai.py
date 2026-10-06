"""Tự xếp ảnh/video thả vào '_chua-phan-loai' về đúng thư mục con trong Kho-Marketing."""

from __future__ import annotations

import base64
import io
import re
import uuid
from typing import Callable

import anthropic
from pydantic import BaseModel, Field

from .du_lieu import DuLieuNen
from .ke_hoach import bo_dau, tu_khoa
from .kho_anh import KhoDrive

THU_MUC_CHO = "_chua-phan-loai"
THU_MUC_XEM_LAI = "_can-xem-lai"
ANH_HOP_LE = {"image/jpeg", "image/png", "image/webp", "image/gif"}

_MO_TA_CO_DINH = {
    "khach-hang": "xưởng/khách hàng thật đang dùng keo, thợ của khách, phản hồi hoặc công trình của khách",
    "nha-may": "nhà máy, dây chuyền sản xuất, đóng gói, kho hàng, giao hàng, xe giao",
    "anh-minh-hoa-chung": "ảnh minh họa chung: thợ đang thi công, mẫu vật liệu, bề mặt, dụng cụ, không rõ sản phẩm keo nào",
}
_MO_TA_NGANH = {
    "Xưởng giày dép, túi da": "xưởng giày dép, túi xách, đồ da, đế giày",
    "Xưởng sofa, nệm, nội thất bọc": "xưởng sofa, nệm, ghế bọc mút vải",
    "Xưởng đồ gỗ, tủ bếp, laminate": "xưởng đồ gỗ, tủ bếp, dán veneer laminate",
    "Nội thất ô tô": "nội thất ô tô, bọc trần xe, bọc ghế xe",
    "Đại lý, cửa hàng vật tư": "cửa hàng, đại lý vật tư keo hóa chất",
}


class KetQuaAnh(BaseModel):
    thu_muc: str = Field(description="Tên đúng một thư mục trong danh sách")
    tu_khoa: list[str] = Field(description="3-6 từ khóa tiếng Việt không dấu, viết thường, mô tả nội dung ảnh")
    chac_chan: bool = Field(description="false nếu không chắc ảnh thuộc thư mục nào")


def mo_ta_thu_muc(du_lieu: DuLieuNen, thu_muc_cfg: dict) -> dict[str, str]:
    """Danh sách thư mục dành cho ảnh (không gồm video-demo) kèm mô tả để AI chọn."""
    mo_ta = {}
    for sp in du_lieu.san_pham:
        if sp.thu_muc:
            chi_tiet = "; ".join(sp.thong_tin[k] for k in ("Dán được vật liệu", "Ứng dụng / ngành dùng")
                                 if k in sp.thong_tin)
            mo_ta[sp.thu_muc] = f"sản phẩm {sp.ten}, bao bì/lon/sản phẩm hoặc cảnh dùng nó. {chi_tiet}"
    for ten_nganh, thu_muc in thu_muc_cfg.get("theo_nganh", {}).items():
        mo_ta[thu_muc] = f"cảnh theo ngành: {_MO_TA_NGANH.get(ten_nganh, ten_nganh)} (không rõ sản phẩm)"
    mo_ta.update(_MO_TA_CO_DINH)
    if thu_muc_cfg.get("anh_chung"):
        mo_ta[thu_muc_cfg["anh_chung"]] = _MO_TA_CO_DINH["anh-minh-hoa-chung"]
    return mo_ta


def thu_nho(noi_dung: bytes, canh_toi_da: int = 1568) -> str:
    """Thu nhỏ ảnh về JPEG ≤1568px để gửi AI (rẻ hơn, không vượt giới hạn dung lượng)."""
    from PIL import Image

    img = Image.open(io.BytesIO(noi_dung))
    img.thumbnail((canh_toi_da, canh_toi_da))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=85)
    return base64.standard_b64encode(buf.getvalue()).decode()


def hoi_ai(client: anthropic.Anthropic, model: str, anh_b64: str, mo_ta: dict[str, str]) -> KetQuaAnh:
    danh_sach = "\n".join(f"- {k}: {v}" for k, v in mo_ta.items())
    r = client.beta.messages.parse(
        model=model,
        max_tokens=1000,
        system="Bạn xếp ảnh marketing của công ty keo dán Golden Lion vào đúng thư mục. "
               "Chỉ chọn một thư mục có trong danh sách. Không đoán: nếu ảnh không rõ thì chac_chan=false.",
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": anh_b64}},
            {"type": "text", "text": f"Các thư mục:\n{danh_sach}"},
        ]}],
        output_format=KetQuaAnh,
        output_config={"effort": "low"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if r.stop_reason in ("refusal", "max_tokens") or r.parsed_output is None:
        raise RuntimeError(f"AI không trả kết quả (stop_reason={r.stop_reason})")
    return r.parsed_output


def ten_moi(tu_khoa_ai: list[str], ten_cu: str) -> str:
    """Đặt tên file có từ khóa để bước chọn ảnh khớp được: 'phun-mut-sofa-3fa9c1.jpg'."""
    duoi = ten_cu.rsplit(".", 1)[1].lower() if "." in ten_cu else "jpg"
    phan = [re.sub(r"[^a-z0-9]+", "-", bo_dau(t)).strip("-") for t in tu_khoa_ai[:6]]
    goc = "-".join(p for p in phan if p)[:60].strip("-") or "anh"
    return f"{goc}-{uuid.uuid4().hex[:6]}.{duoi}"


def thu_muc_cho_video(ten_file: str, du_lieu: DuLieuNen) -> str:
    """Video không xem nội dung được: khớp mã/tên sản phẩm trong tên file, không thì vào video-demo."""
    tu_ten = set(bo_dau(ten_file.rsplit(".", 1)[0]).split())
    for sp in du_lieu.san_pham:
        if sp.thu_muc and (bo_dau(sp.ma) in tu_ten or set(tu_khoa(sp.ma, sp.ten)) & tu_ten - {"phun", "gio", "pro"}):
            return sp.thu_muc
    return "video-demo"


def chay(kho: KhoDrive, du_lieu: DuLieuNen, thu_muc_cfg: dict,
         hoi: Callable[[str, dict[str, str]], KetQuaAnh], toi_da: int = 100) -> list[str]:
    cho_id = kho.id_thu_muc(THU_MUC_CHO, tao=True)
    xem_lai_id = kho.id_thu_muc(THU_MUC_XEM_LAI, tao=True)
    mo_ta = mo_ta_thu_muc(du_lieu, thu_muc_cfg)
    bao_cao = []
    files = kho.liet_ke_de_quy(cho_id)  # gồm cả thư mục con người dùng thả vào
    for f in files[:toi_da]:
        mime, ten = f["mimeType"], f["name"]
        tu_id = (f.get("parents") or [cho_id])[0]
        try:
            if mime.startswith("video/"):
                dich = thu_muc_cho_video(ten, du_lieu)
                moi = None
            elif mime in ANH_HOP_LE:
                kq = hoi(thu_nho(kho.tai_bytes(f["id"])), mo_ta)
                if kq.thu_muc not in mo_ta or not kq.chac_chan:
                    kho.chuyen(f["id"], tu_id, xem_lai_id, ten_moi(kq.tu_khoa, ten))
                    bao_cao.append(f"{ten} → {THU_MUC_XEM_LAI} (AI không chắc)")
                    continue
                dich, moi = kq.thu_muc, ten_moi(kq.tu_khoa, ten)
            else:
                bao_cao.append(f"{ten}: bỏ qua (loại file {mime})")
                continue
            kho.chuyen(f["id"], tu_id, kho.id_thu_muc(dich, tao=True), moi)
            bao_cao.append(f"{ten} → {dich}")
        except Exception as e:  # một file lỗi không làm dừng cả mẻ
            bao_cao.append(f"{ten}: lỗi – {e}")
    con_lai = len(files) - toi_da
    if con_lai > 0:
        bao_cao.append(f"Còn {con_lai} file, sẽ xử lý ở lần chạy sau.")
    return bao_cao
