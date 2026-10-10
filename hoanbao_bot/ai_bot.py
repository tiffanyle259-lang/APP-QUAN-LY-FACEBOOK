"""Gọi Claude để trả lời khách và phân loại bình luận."""

from __future__ import annotations

from typing import Literal

import anthropic
from pydantic import BaseModel, Field

LOI_AI = ("Dạ em đã nhận được tin nhắn của anh/chị. Nhân viên Golden Lion sẽ liên hệ lại sớm nhất ạ. "
          "Anh/chị có thể gọi hoặc nhắn Zalo 0976.884.341 để được hỗ trợ ngay.")


class KetQuaBot(BaseModel):
    tra_loi: str = Field(description="Câu trả lời gửi cho khách")
    chuyen_nhan_vien: bool = Field(description="true nếu cần nhân viên thật tiếp nhận")
    ly_do: str = Field(default="", description="Lý do chuyển nhân viên, ngắn gọn")
    ten: str = ""
    sdt: str = ""
    nhu_cau: str = ""


class KetQuaBinhLuan(BaseModel):
    loai: Literal["hoi_san_pham", "hoi_gia", "muon_mua", "khen", "spam_hoac_xau", "khac"]
    tra_loi_cong_khai: str = Field(default="", description="Câu trả lời ngắn dưới bình luận; để trống nếu không cần")
    tin_nhan_rieng: str = Field(default="", description="Nội dung nhắn riêng cho khách; để trống nếu không cần")
    chuyen_nhan_vien: bool = False


LUAT_BINH_LUAN = """

NHIỆM VỤ HIỆN TẠI: phân loại một bình luận dưới bài đăng của Fanpage rồi soạn phản hồi.
- hoi_san_pham, hoi_gia, muon_mua: tra_loi_cong_khai ngắn (1 câu, mời khách xem tin nhắn hoặc gọi Zalo 0976.884.341, không báo giá), và tin_nhan_rieng là câu trả lời đầy đủ theo các luật trên. hoi_gia và muon_mua thì chuyen_nhan_vien = true.
- khen: tra_loi_cong_khai là lời cảm ơn ngắn; không nhắn riêng.
- spam_hoac_xau, khac: để trống cả hai, không phản hồi."""


class KetQuaNhom(BaseModel):
    noi_dung: str = Field(description="Bài đăng hoàn chỉnh để dán vào nhóm")


LUAT_NHOM = """

NHIỆM VỤ HIỆN TẠI: viết lại một bài Fanpage thành bài đăng để nhân viên dán vào một nhóm Facebook (không phải chat).
- CHỈ dùng thông tin có trong BÀI GỐC và DỮ LIỆU sản phẩm ở trên. Không thêm thông số, giá, chứng nhận hay lời hứa nào không có.
- Không nêu giá. Giữ nguyên số điện thoại/Zalo/website có trong bài gốc.
- Viết như thành viên chia sẻ hữu ích cho ngành của nhóm, giọng gần gũi, bớt quảng cáo; tôn trọng LUẬT NHÓM (vd nhóm cấm link hay cấm quảng cáo thì bỏ link, nói nhẹ nhàng).
- Khác bài gốc về mở bài và cách diễn đạt (nhiều nhóm xóa bài trùng nội dung), 60-150 chữ, tối đa 3 emoji, 3-4 hashtag cuối bài."""


class AiBot:
    def __init__(self, he_thong: str, model: str, effort: str = "low", client: anthropic.Anthropic | None = None):
        self.he_thong, self.model, self.effort = he_thong, model, effort
        self.client = client or anthropic.Anthropic()

    def _goi(self, extra_system: str, messages: list[dict], schema, client=None):
        # Phần dữ liệu dài được lưu đệm (cache) để các lần gọi sau rẻ hơn.
        he_thong = [{"type": "text", "text": self.he_thong, "cache_control": {"type": "ephemeral"}}]
        if extra_system:
            he_thong.append({"type": "text", "text": extra_system})
        r = (client or self.client).beta.messages.parse(
            model=self.model, max_tokens=1500, system=he_thong, messages=messages, output_format=schema,
            output_config={"effort": self.effort},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        )
        if r.stop_reason in ("refusal", "max_tokens") or r.parsed_output is None:
            raise RuntimeError(f"AI không trả kết quả (stop_reason={r.stop_reason})")
        return r.parsed_output

    def tra_loi(self, lich_su: list[dict]) -> KetQuaBot:
        """lich_su: [{'tu': 'khach'|'page', 'noi_dung': str}], cũ trước mới sau, kết thúc bằng tin của khách."""
        msgs: list[dict] = []
        for m in lich_su:
            role = "user" if m["tu"] == "khach" else "assistant"
            if msgs and msgs[-1]["role"] == role:
                msgs[-1]["content"] += "\n" + m["noi_dung"]
            else:
                msgs.append({"role": role, "content": m["noi_dung"]})
        while msgs and msgs[0]["role"] != "user":
            msgs.pop(0)
        return self._goi("", msgs, KetQuaBot)

    def phan_loai_binh_luan(self, noi_dung: str) -> KetQuaBinhLuan:
        return self._goi(LUAT_BINH_LUAN, [{"role": "user", "content": f"Bình luận: {noi_dung}"}], KetQuaBinhLuan)

    def viet_cho_nhom(self, bai_goc: str, ten_nhom: str, nganh: str, luat: str) -> str:
        yeu_cau = (f"BÀI GỐC:\n{bai_goc}\n\nNHÓM: {ten_nhom}\nNGÀNH CỦA NHÓM: {nganh}\n"
                   f"LUẬT NHÓM: {luat or 'không có ghi chú'}")
        client = self.client.with_options(timeout=80.0, max_retries=1) if hasattr(self.client, "with_options") else None
        kq = self._goi(LUAT_NHOM, [{"role": "user", "content": yeu_cau}], KetQuaNhom, client)
        if not kq.noi_dung.strip():
            raise RuntimeError("AI trả về bài trống")
        return kq.noi_dung.strip()
