import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest

from hoanbao_bot.ai_bot import AiBot, KetQuaBinhLuan, KetQuaBot
from hoanbao_bot.kien_thuc import dung_he_thong
from hoanbao_bot.messenger import cat_tin
from hoanbao_bot.server import chu_ky_hop_le, tao_ung_dung
from hoanbao_bot.xu_ly import Bot, tim_sdt
from hoanbao_mkt.cau_hinh import CauHinh
from hoanbao_mkt.du_lieu import doc_du_lieu

PAGE = "999"


class MessGia:
    def __init__(self, lich_su=None):
        self.gui, self.hd, self.cong_khai, self.rieng = [], [], [], []
        self._ls = lich_su

    def hanh_dong(self, psid, a):
        self.hd.append((psid, a))

    def gui_chu(self, psid, text):
        self.gui.append((psid, text))

    def lich_su(self, psid):
        if self._ls is None:
            raise RuntimeError("không có lịch sử")
        return list(self._ls)

    def tra_loi_binh_luan(self, cid, text):
        self.cong_khai.append((cid, text))

    def nhan_rieng_binh_luan(self, cid, text):
        self.rieng.append((cid, text))


class AiGia:
    def __init__(self, bot=None, binh_luan=None, loi=False):
        self.bot, self.bl, self.loi, self.goi = bot, binh_luan, loi, []

    def tra_loi(self, ls):
        self.goi.append(ls)
        if self.loi:
            raise RuntimeError("hỏng")
        return self.bot

    def phan_loai_binh_luan(self, t):
        return self.bl


class SoGia:
    def __init__(self):
        self.dong = []

    def ghi(self, *a):
        self.dong.append(a)


def tin(mid, psid="u1", text="Keo nào dán mút sofa?", **kw):
    ev = {"sender": {"id": psid}, "recipient": {"id": PAGE}, "message": {"mid": mid, "text": text, **kw}}
    return {"object": "page", "entry": [{"messaging": [ev]}]}


def tao_bot(ai, mess=None, gio=lambda: 1000.0):
    mess = mess or MessGia()
    so, bao = SoGia(), []
    return Bot(PAGE, mess, ai, so, bao.append, gio=gio), mess, so, bao


def test_chu_ky_va_xac_minh():
    raw = b'{"object":"page"}'
    ky = "sha256=" + hmac.new(b"bi-mat", raw, hashlib.sha256).hexdigest()
    assert chu_ky_hop_le(raw, ky, "bi-mat")
    assert not chu_ky_hop_le(raw, ky, "sai") and not chu_ky_hop_le(raw, "", "bi-mat")

    da_goi = []
    app = tao_ung_dung(SimpleNamespace(xu_ly_su_kien=da_goi.append), "bi-mat", "tok", chay=lambda f, *a: f(*a))
    c = app.test_client()
    assert c.get("/webhook?hub.mode=subscribe&hub.verify_token=tok&hub.challenge=123").data == b"123"
    assert c.get("/webhook?hub.mode=subscribe&hub.verify_token=sai&hub.challenge=1").status_code == 403
    assert c.post("/webhook", data=raw, headers={"X-Hub-Signature-256": "sha256=00"}).status_code == 403 and not da_goi
    assert c.post("/webhook", data=raw, headers={"X-Hub-Signature-256": ky}).status_code == 200
    assert da_goi == [{"object": "page"}]
    assert c.get("/healthz").status_code == 200


def test_tra_loi_khach_va_bo_trung():
    ai = AiGia(KetQuaBot(tra_loi="Dạ dùng keo phun 228 ạ", chuyen_nhan_vien=False))
    bot, mess, so, bao = tao_bot(ai, MessGia([{"tu": "khach", "noi_dung": "Keo nào dán mút sofa?"}]))
    bot.xu_ly_su_kien(tin("m1"))
    bot.xu_ly_su_kien(tin("m1"))  # Meta gửi trùng
    assert mess.gui == [("u1", "Dạ dùng keo phun 228 ạ")] and len(ai.goi) == 1
    assert ("u1", "mark_seen") in mess.hd and not so.dong and not bao


def test_chuyen_nhan_vien_va_im_lang():
    t = [1000.0]
    ai = AiGia(KetQuaBot(tra_loi="Dạ em xin SĐT ạ", chuyen_nhan_vien=True, ly_do="Hỏi giá", nhu_cau="15kg HP-333"))
    bot, mess, so, bao = tao_bot(ai, MessGia([]), gio=lambda: t[0])
    bot.xu_ly_su_kien(tin("m1", text="Giá bao nhiêu? SĐT 0976 884 341"))
    assert so.dong[0][1:5] == ("u1", "", "0976884341", "15kg HP-333") and bao and "Hỏi giá" in bao[0]
    bot.xu_ly_su_kien(tin("m2", text="alo"))  # bot im lặng sau khi chuyển
    assert len(mess.gui) == 1
    t[0] += 13 * 3600
    bot.xu_ly_su_kien(tin("m3", text="alo?"))
    assert len(mess.gui) == 2


def test_nhan_vien_tra_loi_tay_thi_bot_nhuong():
    ai = AiGia(KetQuaBot(tra_loi="x", chuyen_nhan_vien=False))
    bot, mess, *_ = tao_bot(ai, MessGia([]))
    echo_nv = {"object": "page", "entry": [{"messaging": [
        {"sender": {"id": PAGE}, "recipient": {"id": "u1"}, "message": {"is_echo": True, "mid": "e1", "text": "Chào anh"}}]}]}
    echo_bot = {"object": "page", "entry": [{"messaging": [
        {"sender": {"id": PAGE}, "recipient": {"id": "u2"}, "message": {"is_echo": True, "mid": "e2", "metadata": "bot"}}]}]}
    bot.xu_ly_su_kien(echo_nv)
    bot.xu_ly_su_kien(echo_bot)
    bot.xu_ly_su_kien(tin("m1", psid="u1"))
    assert mess.gui == []
    bot.xu_ly_su_kien(tin("m2", psid="u2"))
    assert len(mess.gui) == 1


def test_ai_loi_va_hinh_anh():
    bot, mess, so, bao = tao_bot(AiGia(loi=True), MessGia([]))
    bot.xu_ly_su_kien(tin("m1", text="Keo bị bong"))
    assert "0976.884.341" in mess.gui[0][1] and so.dong and "AI lỗi" in so.dong[0][5]
    bot2, mess2, so2, _ = tao_bot(AiGia(), MessGia([]))
    bot2.xu_ly_su_kien(tin("m1", text="", attachments=[{"type": "image"}]))
    assert "hình" in mess2.gui[0][1] and so2.dong


def test_su_kien_hong_khong_lam_sap_bot():
    bot, mess, *_ = tao_bot(AiGia(KetQuaBot(tra_loi="ok", chuyen_nhan_vien=False)), MessGia([]))
    body = {"object": "page", "entry": [{"messaging": [{"sender": {}}, {"khac": 1}, tin("m9")["entry"][0]["messaging"][0]]}]}
    bot.xu_ly_su_kien(body)
    assert len(mess.gui) == 1


def cmt(cid, text, nguoi="u7", parent="p1", post="p1"):
    return {"object": "page", "entry": [{"changes": [{"field": "feed", "value": {
        "item": "comment", "verb": "add", "comment_id": cid, "post_id": post, "parent_id": parent,
        "from": {"id": nguoi, "name": "Anh Ba"}, "message": text}}]}]}


def test_binh_luan():
    ai = AiGia(binh_luan=KetQuaBinhLuan(loai="hoi_gia", tra_loi_cong_khai="Em đã nhắn tin ạ",
                                        tin_nhan_rieng="Dạ anh cho em xin SĐT ạ", chuyen_nhan_vien=True))
    bot, mess, so, bao = tao_bot(ai)
    bot.xu_ly_su_kien(cmt("c1", "Giá keo 228 sao shop?"))
    assert mess.cong_khai == [("c1", "Em đã nhắn tin ạ")] and mess.rieng == [("c1", "Dạ anh cho em xin SĐT ạ")]
    assert so.dong[0][0] == "Bình luận" and bao
    bot.xu_ly_su_kien(cmt("c1", "Giá keo 228 sao shop?"))  # trùng
    bot.xu_ly_su_kien(cmt("c2", "hỏi tiếp", parent="c1"))  # bình luận con
    bot.xu_ly_su_kien(cmt("c3", "của page", nguoi=PAGE))
    assert len(mess.cong_khai) == 1


def test_binh_luan_spam_khong_phan_hoi():
    ai = AiGia(binh_luan=KetQuaBinhLuan(loai="spam_hoac_xau", tra_loi_cong_khai="đừng gửi", tin_nhan_rieng="đừng gửi"))
    bot, mess, *_ = tao_bot(ai)
    bot.xu_ly_su_kien(cmt("c1", "mua follow giá rẻ"))
    assert not mess.cong_khai and not mess.rieng


def test_tien_ich():
    assert tim_sdt("gọi 0976.884.341 nhé") == "0976884341" and tim_sdt("+84 976 884 341") == "+84976884341"
    assert tim_sdt("lon 15kg, 3000 đồng") == ""
    ds = cat_tin(("Câu một. " * 400).strip(), 500)
    assert all(len(d) <= 500 for d in ds) and len(ds) > 1
    assert cat_tin("ngắn") == ["ngắn"]


def test_kien_thuc_va_goi_ai():
    cfg = CauHinh.doc()
    du_lieu = doc_du_lieu(cfg.file_du_lieu, cfg["cot_bo_qua"])
    he_thong = dung_he_thong(du_lieu)
    assert "Keo Phun 228" in he_thong and "Keo nào dán mút sofa" in he_thong and "0976.884.341" in he_thong
    assert "cần bổ sung" not in he_thong and "Giá tham khảo" not in he_thong

    thu = {}

    def parse(**kw):
        thu.update(kw)
        return SimpleNamespace(stop_reason="end_turn", parsed_output=KetQuaBot(tra_loi="ok", chuyen_nhan_vien=False))

    ai = AiBot("HT", "claude-sonnet-5-5", client=SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(parse=parse))))
    ai.tra_loi([{"tu": "page", "noi_dung": "Chào"}, {"tu": "khach", "noi_dung": "a"}, {"tu": "khach", "noi_dung": "b"}])
    assert thu["messages"] == [{"role": "user", "content": "a\nb"}]  # bỏ tin page đứng đầu, gộp tin liền nhau
    assert thu["system"][0]["cache_control"] == {"type": "ephemeral"} and thu["fallbacks"] == "default"


def test_khoa_claude_dan_nham(monkeypatch):
    from hoanbao_mkt.cau_hinh import CauHinh, ThieuCauHinh
    monkeypatch.setenv("ANTHROPIC_API_KEY", 'curl https://api.anthropic.com/v1/messages \\\n -H "x-api-key: $KEY" --data \'{"model": "x"}\'')
    with pytest.raises(ThieuCauHinh, match="sk-ant-"):
        CauHinh.khoa_claude()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-abc123\n")
    assert CauHinh.khoa_claude() == "sk-ant-api03-abc123"
