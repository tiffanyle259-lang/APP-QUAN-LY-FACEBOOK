"""Xử lý sự kiện webhook của Meta: tin nhắn Messenger và bình luận trên Fanpage."""

from __future__ import annotations

import logging
import re
import time
from collections import OrderedDict
from datetime import datetime
from zoneinfo import ZoneInfo

from .ai_bot import LOI_AI

log = logging.getLogger("hoanbao_bot")

IM_LANG_SAU_NV_TRA_LOI = 12 * 3600  # nhân viên tự trả lời trong hộp thư thì bot nhường
GHI_LAI_KHACH_SAU = 6 * 3600  # không ghi trùng cùng một khách vào Sheet trong khoảng này (trừ khi có SĐT mới)
_SDT = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.\-]?\d){9}(?!\d)")
TIN_HINH = ("Dạ em đã nhận được hình/tệp của anh/chị ạ. Em chuyển nhân viên kỹ thuật xem và phản hồi sớm nhất. "
            "Anh/chị có thể nhắn thêm vật liệu đang dán và loại keo đang dùng để bên em hỗ trợ nhanh hơn ạ.")


def tim_sdt(text: str) -> str:
    m = _SDT.search(text or "")
    return re.sub(r"[\s.\-]", "", m.group(0)) if m else ""


class Bot:
    def __init__(self, page_id: str, mess, ai, so_khach=None, bao=None, mui_gio: str = "Asia/Ho_Chi_Minh",
                 gio=time.time):
        self.page_id, self.mess, self.ai, self.so_khach, self.bao = page_id, mess, ai, so_khach, bao
        self.mui_gio, self.gio = ZoneInfo(mui_gio), gio
        self.da_xu_ly: OrderedDict[str, float] = OrderedDict()
        self.im_lang: dict[str, float] = {}
        self.da_ghi: dict[str, tuple[float, str]] = {}  # psid -> (lúc ghi, sdt đã ghi)
        # Số liệu để chẩn đoán từ xa (không chứa nội dung khách hay khóa).
        self.thong_ke = {"goi_webhook": 0, "su_kien": 0, "tin_nhan_khach": 0, "binh_luan": 0,
                         "da_gui_tra_loi": 0, "bo_qua_im_lang": 0, "loi": 0, "lan_cuoi": "", "loi_cuoi": "",
                         "khoi_dong": datetime.fromtimestamp(self.gio(), self.mui_gio).strftime("%d/%m %H:%M:%S")}

    # ---- điểm vào ----
    def xu_ly_su_kien(self, body: dict) -> None:
        self.thong_ke["goi_webhook"] += 1
        self.thong_ke["lan_cuoi"] = datetime.fromtimestamp(self.gio(), self.mui_gio).strftime("%d/%m %H:%M:%S")
        if body.get("object") != "page":
            return
        for entry in body.get("entry", []):
            for ev in entry.get("messaging", []):
                self._an_toan(self._tin_nhan, ev)
            for ch in entry.get("changes", []):
                self._an_toan(self._thay_doi, ch)

    def _an_toan(self, ham, doi_tuong) -> None:
        self.thong_ke["su_kien"] += 1
        try:
            ham(doi_tuong)
        except Exception as e:  # một sự kiện lỗi không được làm sập cả bot
            log.exception("Lỗi xử lý sự kiện")
            self.ghi_loi(e)

    def ghi_loi(self, e: Exception) -> None:
        self.thong_ke["loi"] += 1
        # Che mọi chuỗi giống token trước khi lưu.
        self.thong_ke["loi_cuoi"] = re.sub(r"(EAA|sk-ant-)\w+", r"\1***", f"{type(e).__name__}: {e}")[:300]

    def _moi(self, khoa: str) -> bool:
        """True nếu chưa xử lý khoá này (Meta có thể gửi trùng)."""
        if khoa in self.da_xu_ly:
            return False
        self.da_xu_ly[khoa] = self.gio()
        while len(self.da_xu_ly) > 5000:
            self.da_xu_ly.popitem(last=False)
        return True

    # ---- Messenger ----
    def _tin_nhan(self, ev: dict) -> None:
        msg = ev.get("message")
        if msg and msg.get("is_echo"):
            # Tin do Page gửi. Không phải của bot (không có metadata "bot") nghĩa là nhân viên trả lời tay.
            if msg.get("metadata") != "bot" and ev.get("recipient", {}).get("id"):
                self.im_lang[ev["recipient"]["id"]] = self.gio() + IM_LANG_SAU_NV_TRA_LOI
            return
        psid = ev.get("sender", {}).get("id")
        if not psid or psid == self.page_id:
            return
        if msg:
            if not self._moi("m:" + str(msg.get("mid", ""))):
                return
            text = (msg.get("text") or "").strip()
            co_tep = bool(msg.get("attachments"))
        elif ev.get("postback"):
            text, co_tep = "Xin chào", False
        else:
            return
        self.thong_ke["tin_nhan_khach"] += 1
        if self.gio() < self.im_lang.get(psid, 0):
            log.info("Bỏ qua %s: nhân viên đang xử lý", psid)
            self.thong_ke["bo_qua_im_lang"] += 1
            return
        self.mess.hanh_dong(psid, "mark_seen")
        self.mess.hanh_dong(psid, "typing_on")
        if not text:
            if co_tep:
                self.mess.gui_chu(psid, TIN_HINH)
                self._chuyen(psid, "", "", "Khách gửi hình/tệp", "")
            return
        self._tra_loi(psid, text)

    def _tra_loi(self, psid: str, text: str) -> None:
        try:
            lich_su = self.mess.lich_su(psid)
        except Exception:
            log.warning("Không lấy được lịch sử, dùng tin hiện tại")
            lich_su = []
        if not lich_su or lich_su[-1]["tu"] != "khach":
            lich_su.append({"tu": "khach", "noi_dung": text})
        try:
            kq = self.ai.tra_loi(lich_su)
        except Exception as e:
            log.exception("AI lỗi")
            self.ghi_loi(e)
            self.mess.gui_chu(psid, LOI_AI)
            self._chuyen(psid, "", tim_sdt(text), "AI lỗi, cần nhân viên", text[:200])
            return
        self.mess.gui_chu(psid, kq.tra_loi)
        self.thong_ke["da_gui_tra_loi"] += 1
        sdt = tim_sdt(kq.sdt) or tim_sdt(text)
        if kq.chuyen_nhan_vien or sdt:
            self._chuyen(psid, kq.ten, sdt, kq.ly_do if kq.chuyen_nhan_vien else "Khách để lại SĐT", kq.nhu_cau)

    def _chuyen(self, psid: str, ten: str, sdt: str, ly_do: str, nhu_cau: str, kenh: str = "Messenger") -> None:
        """Ghi khách vào Sheet và báo nhân viên. Bot vẫn tiếp tục trả lời khách; chỉ nhường khi nhân viên trả lời tay."""
        truoc = self.da_ghi.get(psid)
        if truoc and self.gio() - truoc[0] < GHI_LAI_KHACH_SAU and (not sdt or sdt == truoc[1]):
            return  # đã ghi gần đây, không tạo dòng trùng
        self.da_ghi[psid] = (self.gio(), sdt or (truoc[1] if truoc else ""))
        luc = datetime.fromtimestamp(self.gio(), self.mui_gio)
        if self.so_khach:
            try:
                self.so_khach.ghi(kenh, psid, ten, sdt, nhu_cau, ly_do, luc)
            except Exception:
                log.exception("Không ghi được Sheet khách hàng")
        if self.bao:
            self.bao(f"Khách mới cần xử lý qua {kenh} ({ly_do})\nSĐT: {sdt or 'chưa có'}\nTên: {ten or 'chưa rõ'}\n"
                     f"Nhu cầu: {nhu_cau or '-'}\nMở hộp thư: https://business.facebook.com/latest/inbox")

    # ---- Bình luận ----
    def _thay_doi(self, ch: dict) -> None:
        v = ch.get("value", {})
        if ch.get("field") != "feed" or v.get("item") != "comment" or v.get("verb") != "add":
            return
        cid, nguoi = v.get("comment_id"), v.get("from", {}).get("id")
        # Chỉ bình luận cấp 1 (parent là bài đăng), không phải bình luận của chính Page.
        if not cid or nguoi == self.page_id or v.get("parent_id") != v.get("post_id"):
            return
        if not self._moi("c:" + str(cid)):
            return
        text = (v.get("message") or "").strip()
        if not text:
            return
        self.thong_ke["binh_luan"] += 1
        kq = self.ai.phan_loai_binh_luan(text)
        if kq.tra_loi_cong_khai.strip() and kq.loai not in ("spam_hoac_xau", "khac"):
            self.mess.tra_loi_binh_luan(cid, kq.tra_loi_cong_khai.strip())
        if kq.tin_nhan_rieng.strip() and kq.loai in ("hoi_san_pham", "hoi_gia", "muon_mua"):
            self.mess.nhan_rieng_binh_luan(cid, kq.tin_nhan_rieng.strip())
        if kq.chuyen_nhan_vien and nguoi:
            self._chuyen(nguoi, v.get("from", {}).get("name", ""), tim_sdt(text), f"Bình luận: {kq.loai}", text[:200],
                         kenh="Bình luận")
