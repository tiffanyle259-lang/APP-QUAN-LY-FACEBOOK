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


def test_chuyen_nhan_vien_van_tiep_tuc_tra_loi_va_khong_ghi_trung():
    t = [1000.0]
    ai = AiGia(KetQuaBot(tra_loi="Dạ em xin SĐT ạ", chuyen_nhan_vien=True, ly_do="Hỏi giá", nhu_cau="15kg HP-333"))
    bot, mess, so, bao = tao_bot(ai, MessGia([]), gio=lambda: t[0])
    bot.xu_ly_su_kien(tin("m1", text="Giá bao nhiêu? SĐT 0976 884 341"))
    assert so.dong[0][1:5] == ("u1", "", "0976884341", "15kg HP-333") and bao and "Hỏi giá" in bao[0]
    # Bot không im lặng sau khi chuyển: khách hỏi tiếp vẫn được trả lời
    bot.xu_ly_su_kien(tin("m2", text="Keo nào dán đế giày?"))
    assert len(mess.gui) == 2
    # Nhưng không ghi trùng khách vào Sheet và không báo lại
    assert len(so.dong) == 1 and len(bao) == 1
    # Có SĐT mới thì ghi lại
    bot.xu_ly_su_kien(tin("m3", text="SĐT mới 0912 345 678"))
    assert len(so.dong) == 2
    # Sau 6 giờ thì được ghi lại
    t[0] += 7 * 3600
    bot.xu_ly_su_kien(tin("m4", text="alo"))
    assert len(so.dong) == 3


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


def test_dang_ky_webhook():
    from hoanbao_bot.dang_ky import LoiDangKy, chuan_hoa_url, dang_ky

    assert chuan_hoa_url("https://x.onrender.com/") == "https://x.onrender.com/webhook"
    with pytest.raises(LoiDangKy):
        chuan_hoa_url("http://x.com")

    class R:
        def __init__(self, code=200, body=None, text=""):
            self.status_code, self._b, self.text, self.content = code, body or {}, text, b"x"

        def json(self):
            return self._b

    class Http:
        def __init__(self, may_chu_ok=True):
            self.goi, self.ok = [], may_chu_ok

        def get(self, url, params=None, timeout=0):
            return R(200, text="kiem-tra-123" if self.ok else "forbidden") if self.ok else R(403, text="forbidden")

        def request(self, method, url, params=None, timeout=0):
            self.goi.append((method, url.split("v24.0/")[1], dict(params)))
            return R(200, {"data": [{"name": "Hoan Bao Marketing"}]} if method == "GET" else {"success": True})

    h = Http()
    ds = dang_ky("https://x.onrender.com", "APP", "SEC", "VT", "PAGE", "PTOKEN", http=h)
    assert len(ds) == 3 and "Hoan Bao Marketing" in ds[2]
    assert h.goi[0][1] == "APP/subscriptions" and h.goi[0][2]["access_token"] == "APP|SEC"
    assert h.goi[0][2]["callback_url"] == "https://x.onrender.com/webhook" and "feed" in h.goi[0][2]["fields"]
    assert h.goi[1][1] == "PAGE/subscribed_apps" and h.goi[1][2]["access_token"] == "PTOKEN"
    with pytest.raises(LoiDangKy, match="FB_VERIFY_TOKEN"):
        dang_ky("https://x.onrender.com", "APP", "SEC", "VT", "PAGE", "PT", http=Http(may_chu_ok=False))


def test_thong_ke_va_trang_thai():
    ai = AiGia(KetQuaBot(tra_loi="ok", chuyen_nhan_vien=False))
    bot, mess, *_ = tao_bot(ai, MessGia([]))
    bot.xu_ly_su_kien(tin("m1"))
    bot.xu_ly_su_kien({"object": "page", "entry": [{"messaging": [{"sender": {"id": "u"}, "message": {"mid": "x", "text": "a"}}]}]})
    t = bot.thong_ke
    assert t["goi_webhook"] == 2 and t["tin_nhan_khach"] == 2 and t["da_gui_tra_loi"] == 2 and t["lan_cuoi"]

    class Hong(MessGia):
        def gui_chu(self, psid, text):
            raise RuntimeError("Invalid OAuth access token EAAB12345secret")

    bot2, *_ = tao_bot(AiGia(KetQuaBot(tra_loi="ok", chuyen_nhan_vien=False)), Hong([]))
    bot2.xu_ly_su_kien(tin("m1"))
    assert bot2.thong_ke["loi"] == 1 and "secret" not in bot2.thong_ke["loi_cuoi"] and "EAA***" in bot2.thong_ke["loi_cuoi"]

    app = tao_ung_dung(bot, "s", "mat-khau", chay=lambda f, *a: f(*a), moi_truong=lambda: {"khoa_claude": "đúng dạng"})
    c = app.test_client()
    assert c.get("/trang-thai?k=sai").status_code == 403
    d = c.get("/trang-thai?k=mat-khau").get_json()
    assert d["bot"]["tin_nhan_khach"] == 2 and d["moi_truong"]["khoa_claude"] == "đúng dạng"


def test_trang_chinh_sach_va_xoa_du_lieu():
    app = tao_ung_dung(SimpleNamespace(), "s", "t")
    c = app.test_client()
    for duong_dan, chu in [("/chinh-sach-rieng-tu", "Chính sách quyền riêng tư"), ("/xoa-du-lieu", "Hướng dẫn xóa dữ liệu")]:
        r = c.get(duong_dan)
        assert r.status_code == 200 and chu in r.get_data(as_text=True) and "keodansutu@gmail.com" in r.get_data(as_text=True)
        assert "Privacy" in r.get_data(as_text=True) or "Deletion" in r.get_data(as_text=True)


def test_bang_dieu_khien_can_mat_khau():
    app = tao_ung_dung(SimpleNamespace(), "s", "mat-khau", bang_dieu_khien=lambda: "<html>ok</html>")
    c = app.test_client()
    assert c.get("/bang-dieu-khien").status_code == 403
    chua = c.get("/bang-dieu-khien")
    assert b'type="password"' in chua.data and "chưa đúng".encode() not in chua.data  # hiện ô nhập mật khẩu
    sai = c.get("/bang-dieu-khien?k=sai")
    assert sai.status_code == 403 and "chưa đúng".encode() in sai.data
    r = c.get("/bang-dieu-khien?k=mat-khau")  # đúng mật khẩu: đặt cookie rồi chuyển về địa chỉ không có mật khẩu
    assert r.status_code == 302 and r.headers["Location"].endswith("/bang-dieu-khien")
    r = c.get("/bang-dieu-khien")
    assert r.status_code == 200 and b"ok" in r.data


def test_api_thao_tac_can_dang_nhap_va_kiem_tra():
    from hoanbao_bot.server import LoiThaoTac

    def thao_tac(lenh):
        if lenh.get("hanh") == "hong":
            raise LoiThaoTac("Bài đã lên lịch")
        return {"ok": True}

    app = tao_ung_dung(SimpleNamespace(), "s", "mat-khau", bang_dieu_khien=lambda: "x", thao_tac=thao_tac)
    c = app.test_client()
    h = {"X-GL": "1"}
    assert c.post("/api/thao-tac", json={"hanh": "a"}, headers=h).status_code == 403  # chưa đăng nhập
    c.get("/bang-dieu-khien?k=mat-khau")
    assert c.post("/api/thao-tac", json={"hanh": "a"}).status_code == 403  # thiếu header chống giả mạo
    assert c.post("/api/thao-tac", json={"hanh": "a"}, headers=h).get_json() == {"ok": True}
    r = c.post("/api/thao-tac", json={"hanh": "hong"}, headers=h)
    assert r.status_code == 400 and r.get_json()["loi"] == "Bài đã lên lịch"
    assert c.post("/api/thao-tac", data="khong phai json", headers=h).status_code == 400


def test_bang_dieu_khien_co_nut_khi_duoc_sua():
    from hoanbao_mkt.bang_dieu_khien import dung_html

    d = {"cap_nhat": "x", "page": "KEO DÁN GIÀY", "che_do_duyet": True, "sheet_url": "", "kho": [],
         "bai": [{"ma_bai": "m1", "ngay": "2026-10-12", "gio": "08:00", "loai": "L", "noi_dung": "<i>nd</i>", "media": "",
                  "trang_thai": "Chờ duyệt", "ghi_chu": "", "facebook_id": ""},
                 {"ma_bai": "m2", "ngay": "2026-10-13", "gio": "08:00", "loai": "L", "noi_dung": "nd", "media": "",
                  "trang_thai": "Đã lên lịch", "ghi_chu": "", "facebook_id": "123"}],
         "khach": [["t", "Messenger", "1", "An", "09", "n", "l", "Mới", "", 7]]}
    xem = dung_html(d)
    assert "data-hanh" not in xem  # bản chỉ xem (xuất từ GitHub) không có nút
    d["sua_duoc"] = True
    sua = dung_html(d)
    assert "data-tt='Duyệt'" in sua and 'data-dong=\'7\'' in sua
    assert "&lt;i&gt;nd" in sua  # nội dung vẫn được escape
    assert sua.count("data-hanh='bai_trang_thai'") == 2  # chỉ bài m1 (Duyệt, Bỏ); bài đã lên lịch không có nút


def test_bang_dieu_khien_khong_co_kho():
    from hoanbao_mkt.bang_dieu_khien import dung_html

    html = dung_html({"cap_nhat": "08:00 09/10/2026", "page": "KEO DÁN GIÀY", "che_do_duyet": True,
                      "sheet_url": "https://docs.google.com/x", "bai": [], "kho": []})
    assert "<html" in html.lower()


def test_bang_dieu_khien_co_khach_va_tin_nhan():
    from hoanbao_mkt.bang_dieu_khien import dung_html

    html = dung_html({"cap_nhat": "x", "page": "P", "che_do_duyet": True, "sheet_url": "", "bai": [], "kho": [],
                      "bot": {"tin_nhan_khach": 5, "da_gui_tra_loi": 4, "binh_luan": 1, "bo_qua_im_lang": 0, "loi": 0,
                              "khoi_dong": "09/10 08:00"},
                      "khach": [["09/10/2026 08:01", "Messenger", "1", "An", "0912345678", "keo 228", "hỏi giá", "Mới", ""]],
                      "hoi_thoai": [{"ten": "An", "luc": "2026-10-09T01:00:00+0000",
                                     "tin": [{"tu": "khach", "noi_dung": "<b>giá</b>?", "luc": ""},
                                             {"tu": "page", "noi_dung": "Dạ cho em xin SĐT", "luc": ""}]}]})
    assert "0912345678" in html and "Dạ cho em xin SĐT" in html
    assert "&lt;b&gt;giá" in html  # nội dung khách luôn được escape


def test_hoi_thoai_gan_day_doc_tu_graph():
    from hoanbao_bot.messenger import Messenger

    class R:
        content = b"1"
        status_code = 200
        text = ""

        def json(self):
            return {"data": [{"updated_time": "2026-10-09T01:00:00+0000",
                              "participants": {"data": [{"id": "P", "name": "Page"}, {"id": "U", "name": "An"}]},
                              "messages": {"data": [{"message": "Dạ", "from": {"id": "P"}, "created_time": "t2"},
                                                    {"message": "giá?", "from": {"id": "U"}, "created_time": "t1"}]}}]}

    class S:
        def request(self, *a, **k):
            return R()

    cuoc = Messenger("P", "tok", session=S()).hoi_thoai_gan_day()
    assert cuoc[0]["ten"] == "An"
    assert [t["tu"] for t in cuoc[0]["tin"]] == ["khach", "page"]


def test_kho_xem_chi_cho_file_trong_kho():
    from hoanbao_bot.kho_xem import KhoXem

    cha = {"anh": "tm", "tm": "KHO0000000000", "ngoai": "xx", "xx": None}

    class Drive:
        def files(self):
            return self

        def get(self, fileId, **k):
            self.f = fileId
            return self

        def execute(self):
            return {"id": self.f, "parents": [cha[self.f]] if cha[self.f] else []}

    # id phải đủ dài và đúng dạng của Drive; dùng tên dài để qua kiểm tra dạng
    cha = {"a" * 12: "t" * 12, "t" * 12: "KHO0000000000", "n" * 12: "x" * 12, "x" * 12: None}
    k = KhoXem(Drive(), "KHO0000000000")
    assert k.hop_le("a" * 12) is True
    assert k.hop_le("n" * 12) is False
    assert k.hop_le("../etc/passwd") is False


def test_api_anh_can_dang_nhap_va_chan_file_ngoai_kho():
    from hoanbao_bot.kho_xem import NgoaiKho

    class Kho:
        def anh_nho(self, fid, canh=640):
            if fid == "ngoai":
                raise NgoaiKho("File không nằm trong Kho-Marketing.")
            return b"\xff\xd8\xff" + b"jpg"

        def danh_sach(self, ten):
            return [{"id": "x" * 12, "ten": "a.jpg", "video": False}]

    app = tao_ung_dung(SimpleNamespace(), "s", "mk", kho_xem=Kho())
    c = app.test_client()
    assert c.get("/api/anh/abc").status_code == 403
    assert c.get("/api/kho/keo-228").status_code == 403
    c.get("/bang-dieu-khien?k=mk")
    assert c.get("/api/anh/abc").data.startswith(b"\xff\xd8\xff")
    assert c.get("/api/anh/ngoai").status_code == 404
    assert c.get("/api/kho/keo-228").get_json()[0]["ten"] == "a.jpg"


def test_bang_dieu_khien_tab_he_thong():
    from hoanbao_mkt.bang_dieu_khien import dung_html

    d = {"cap_nhat": "x", "page": "P", "che_do_duyet": True, "sheet_url": "", "bai": [], "kho": [],
         "he_thong": [{"ten": "Claude (AI)", "ok": True, "chi_tiet": "Khóa dùng được", "huong_dan": ""},
                      {"ten": "Kho ảnh", "ok": False, "chi_tiet": "Chưa cấu hình DRIVE_KHO_ID", "huong_dan": "Thêm biến"}]}
    html = dung_html(d)
    assert "data-tab='he-thong'" in html and "1 bộ phận cần chú ý" in html and "Thêm biến" in html
    d["he_thong"] = []
    assert "data-tab='he-thong'" not in dung_html(d)


def test_gui_email_bao_khach_moi(monkeypatch):
    import hoanbao_bot.khach as k

    daGui = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=0):
            daGui.append(("ket_noi", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def login(self, u, p):
            daGui.append(("dang_nhap", u, p))

        def send_message(self, msg):
            daGui.append(("gui", msg["To"], msg["Subject"], msg.get_content()))

    monkeypatch.setattr(k.smtplib, "SMTP_SSL", FakeSMTP)
    for ten in ("SMTP_USER", "SMTP_PASSWORD", "NOTIFY_EMAIL"):
        monkeypatch.delenv(ten, raising=False)
    assert k.gui_email("Khách mới\nSĐT: 0912") is False and daGui == []  # chưa cấu hình thì không gửi
    monkeypatch.setenv("SMTP_USER", "a@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "abcd efgh ijkl mnop")  # mật khẩu ứng dụng Gmail thường có dấu cách
    monkeypatch.setenv("NOTIFY_EMAIL", "x@y.vn, z@y.vn")
    assert k.gui_email("Khách mới cần xử lý qua Messenger\nSĐT: 0912") is True
    gui = next(x for x in daGui if x[0] == "gui")
    assert gui[1] == "x@y.vn, z@y.vn" and "0912" in gui[3]
    assert ("dang_nhap", "a@gmail.com", "abcdefghijklmnop") in daGui


def test_he_thong_co_nut_gui_thu_email():
    from hoanbao_mkt.bang_dieu_khien import dung_html

    d = {"cap_nhat": "x", "page": "P", "che_do_duyet": True, "sheet_url": "", "bai": [], "kho": [], "sua_duoc": True,
         "he_thong": [{"ten": "Báo khách mới qua email", "ok": True, "chi_tiet": "Đã cấu hình", "huong_dan": "", "nut": "email_thu"}]}
    assert "data-hanh=email_thu" in dung_html(d)
    d["sua_duoc"] = False
    assert "email_thu" not in dung_html(d).split("<script>")[0]


def test_gui_email_qua_apps_script(monkeypatch):
    import hoanbao_bot.khach as k

    goi = []

    class R:
        status_code = 200
        text = "ok"

    monkeypatch.setattr(k.requests, "post", lambda url, json=None, timeout=0: goi.append((url, json)) or R())
    monkeypatch.setenv("EMAIL_WEBHOOK_URL", "https://script.google.com/macros/s/xxx/exec")
    monkeypatch.setenv("EMAIL_WEBHOOK_SECRET", "bi-mat")
    assert k.email_da_cau_hinh() is True
    assert k.gui_email("Khách mới\nSĐT: 0912") is True
    assert goi[0][1]["secret"] == "bi-mat" and "0912" in goi[0][1]["body"]
    R.text = "forbidden"  # sai mật khẩu bên Apps Script thì báo thất bại
    assert k.gui_email("x") is False


def test_gui_email_chi_tiet_noi_ro_ly_do(monkeypatch):
    import hoanbao_bot.khach as k

    class R:
        status_code = 200
        text = "forbidden"

    monkeypatch.setattr(k.requests, "post", lambda *a, **kw: R())
    monkeypatch.setenv("EMAIL_WEBHOOK_URL", "https://script.google.com/macros/s/x/exec")
    monkeypatch.setenv("EMAIL_WEBHOOK_SECRET", "s")
    ok, ly_do = k.gui_email_chi_tiet("x")
    assert not ok and "chuỗi bí mật" in ly_do
    R.text = "<!DOCTYPE html><html>dang nhap</html>"
    assert "Bất kỳ ai" in k.gui_email_chi_tiet("x")[1]
    R.text = "loi"
    assert "Cập nhật mã mới" in k.gui_email_chi_tiet("x")[1]


def test_gui_email_hien_chi_tiet_loi_tu_apps_script(monkeypatch):
    import hoanbao_bot.khach as k

    class R:
        status_code = 200
        text = "loi: Invalid argument: recipient"

    monkeypatch.setattr(k.requests, "post", lambda *a, **kw: R())
    monkeypatch.setenv("EMAIL_WEBHOOK_URL", "https://script.google.com/macros/s/x/exec")
    monkeypatch.setenv("EMAIL_WEBHOOK_SECRET", "s")
    ok, ly_do = k.gui_email_chi_tiet("x")
    assert not ok and "Invalid argument: recipient" in ly_do


def test_kho_xem_danh_sach_khong_hoi_lai_drive_tung_anh():
    from hoanbao_bot.kho_xem import KhoXem

    goi = {"get": 0}

    class Drive:
        def files(self):
            return self

        def list(self, q="", **k):
            self.q = q
            return self

        def get(self, **k):
            goi["get"] += 1
            return self

        def execute(self):
            if "mimeType = 'application/vnd.google-apps.folder'" in self.q:
                return {"files": [{"id": "T" * 12}]}
            return {"files": [{"id": "A" * 12, "name": "a.jpg", "mimeType": "image/jpeg", "size": "1000",
                               "thumbnailLink": "https://lh3.example/x=s220"}]}

    class Http:
        def get(self, url, headers=None, timeout=0):
            self.url = url

            class R:
                status_code = 200
                content = b"\xff\xd8\xff-anh"

            return R()

    http = Http()
    k = KhoXem(Drive(), "KHO0000000000", lambda: "tok", http)
    ds = k.danh_sach("keo-228")
    assert ds[0]["ten"] == "a.jpg"
    assert k.anh_nho("A" * 12, 320).startswith(b"\xff\xd8\xff")
    assert http.url.endswith("=s320") and goi["get"] == 0  # không gọi Drive thêm cho từng ảnh


def test_tieu_de_youtube_lay_dong_dau_co_chu():
    from hoanbao_mkt.youtube import tieu_de_tu_noi_dung

    assert tieu_de_tu_noi_dung("\n#tag\nDán đế giày <bền>\nchi tiết") == "Dán đế giày bền"
    assert len(tieu_de_tu_noi_dung("a" * 300)) == 100
    assert tieu_de_tu_noi_dung("") == "Keo dán Golden Lion"


def test_nhom_link_va_cho_giua_hai_lan_dang():
    from datetime import date

    import pytest

    from hoanbao_bot.nhom import LoiNhom, chuan_link, dong_thanh_nhom, tinh_trang

    assert chuan_link("https://www.facebook.com/groups/keo.dan.sofa/") .endswith("keo.dan.sofa/")
    for xau in ("http://facebook.com/groups/a", "https://evil.com/groups/a", "https://facebook.com/page/a", ""):
        with pytest.raises(LoiNhom):
            chuan_link(xau)
    n = dong_thanh_nhom(2, ["N", "https://facebook.com/groups/a", "Khác", "", "7", "10/10/2026", "2", ""])
    assert tinh_trang(n, date(2026, 10, 12)) == (False, 5)
    assert tinh_trang(n, date(2026, 10, 17)) == (True, 0)
    n["trang_thai"] = "Tạm dừng"
    assert tinh_trang(n, date(2026, 12, 1)) == (False, 0)
    moi = dong_thanh_nhom(3, ["M", "https://facebook.com/groups/b"])
    assert tinh_trang(moi, date(2026, 10, 12)) == (True, 0) and moi["cach"] == 7


def test_bang_dieu_khien_co_tab_nhom():
    from hoanbao_mkt.bang_dieu_khien import JS_NHOM, dung_html

    d = {"cap_nhat": "x", "page": "P", "che_do_duyet": True, "sheet_url": "", "kho": [], "sua_duoc": True,
         "bai": [{"ma_bai": "m1", "ngay": "2026-10-12", "gio": "08:00", "loai": "L", "noi_dung": "bài", "media": "",
                  "trang_thai": "Chờ duyệt", "ghi_chu": "", "facebook_id": ""}],
         "nhom": [{"dong": 2, "ten": "Nhóm <sofa>", "link": "https://www.facebook.com/groups/a", "nganh": "Khác", "luat": "",
                   "cach": 7, "lan_cuoi": "", "so_lan": "0", "trang_thai": "Đang dùng"}]}
    h = dung_html(d)
    assert "id='p-nhom'" in h and "Nhóm &lt;sofa&gt;" in h and "hop-nhom" in h and "nhom_trang_thai" in h
    assert "id='p-nhom'" not in dung_html({**d, "nhom": None})
    assert "nhom_soan_bai" in JS_NHOM


def test_nhap_nhom_tu_van_ban():
    from hoanbao_bot.nhom import doc_van_ban

    rows, bo = doc_van_ban(
        "HỘI THỢ SOFA | https://www.facebook.com/groups/1 | Sofa, nệm, mút xốp, nội thất\n"
        "Xưởng giày | https://www.facebook.com/groups/2 | Giày dép, xưởng giày | không dán link\n"
        "Trùng | https://www.facebook.com/groups/1/ | Khác\n"
        "Sai | https://example.com/x | Khác\n"
        "Thiếu link\n\n"
        "Gỗ | https://www.facebook.com/groups/3 | Gỗ, mộc, nội thất\n")
    assert [r[2] for r in rows] == ["Sofa, nệm, nội thất", "Giày dép, túi da", "Đồ gỗ, tủ bếp"]
    assert rows[1][3] == "không dán link" and rows[0][3].startswith("Chưa kiểm tra nội quy")
    assert len(bo) == 3


def test_bao_cao_tuan_tinh_so_lieu():
    from datetime import datetime

    from hoanbao_mkt.bao_cao import dem_khach_moi, tinh

    bai = [{"id": "1", "created_time": "t", "message": "Bài A\nchi tiết", "permalink_url": "https://fb/a",
            "reactions": {"summary": {"total_count": 10}}, "comments": {"summary": {"total_count": 2}}, "shares": {"count": 1}},
           {"id": "2", "message": "Bài B", "reactions": {"summary": {"total_count": 3}}}]
    dong = tinh(bai, 120, 100, 4, datetime(2026, 10, 19))
    assert dong[:8] == ["19/10/2026", "120", "+20", "2", "13", "2", "1", "4"]
    assert dong[8].startswith("Bài A (cảm xúc 10, bình luận 2, chia sẻ 1) https://fb/a")
    assert tinh([], 5, None, 0, datetime(2026, 10, 19))[2] == ""
    assert dem_khach_moi([["15/10/2026 10:00"], ["01/09/2026 10:00"], ["hỏng"]], datetime(2026, 10, 12)) == 1


def test_bang_dieu_khien_co_tab_bao_cao():
    from hoanbao_mkt.bang_dieu_khien import dung_html

    d = {"cap_nhat": "x", "page": "P", "che_do_duyet": True, "sheet_url": "", "kho": [], "bai": [], "sua_duoc": True,
         "bao_cao": [{"ngay": "19/10/2026", "nguoi": "120", "doi": "+20", "bai": "2", "cam_xuc": "13", "binh_luan": "2",
                      "chia_se": "1", "khach": "4", "top": "Bài <A> | Bài B"}]}
    h = dung_html(d)
    assert "id='p-bao-cao'" in h and "Bài &lt;A&gt;" in h
    assert "id='p-bao-cao'" not in dung_html({**d, "bao_cao": None})


def test_nhap_khach_quang_cao_tu_csv_meta():
    from hoanbao_mkt.nhap_khach import chuan_sdt, doc_csv_quang_cao

    assert chuan_sdt("+84912345678") == "0912345678" and chuan_sdt("0912 345 678") == "0912345678"
    csv_text = ("id,created_time,form_name,campaign_name,full_name,phone_number,lead_status\\n"
                "L1,2026-10-10T00:30:00-07:00,Form A,Camp,Nguyễn An,+84912345678,complete\\n"
                ",2026-10-10T00:30:00-07:00,Form A,Camp,Thiếu mã,+84900000000,complete\\n").replace("\\n", "\n")
    rows = doc_csv_quang_cao(csv_text)
    assert len(rows) == 1
    assert rows[0] == ["10/10/2026 14:30", "Quảng cáo Facebook", "lead:L1", "Nguyễn An", "0912345678",
                       "Quảng cáo: Form A", "Để lại thông tin qua biểu mẫu quảng cáo", "Mới", ""]


def test_nhom_co_nut_da_dang_ngoai_dong_nhom():
    from hoanbao_mkt.bang_dieu_khien import dung_html

    n = {"dong": 2, "ten": "N1", "link": "https://www.facebook.com/groups/a", "nganh": "Khác", "luat": "", "cach": 7,
         "lan_cuoi": "", "so_lan": "0", "trang_thai": "Đang dùng"}
    d = {"cap_nhat": "x", "page": "P", "che_do_duyet": True, "sheet_url": "", "kho": [], "bai": [], "sua_duoc": True,
         "nhom": [n, {**n, "dong": 3, "trang_thai": "Tạm dừng"}]}
    assert dung_html(d).count("data-hanh='nhom_da_dang'") == 1  # nhóm tạm dừng không có nút


def test_nut_chia_se_chi_hien_khi_bai_da_dang():
    from hoanbao_mkt.bang_dieu_khien import dung_html

    bai = lambda ma, ngay, tt, fid: {"ma_bai": ma, "ngay": ngay, "gio": "08:00", "loai": "L", "noi_dung": "nd", "media": "",
                                      "trang_thai": tt, "ghi_chu": "", "facebook_id": fid}
    d = {"cap_nhat": "x", "page": "P", "che_do_duyet": True, "sheet_url": "", "kho": [], "khong_loc_thang": True,
         "bai": [bai("a", "2020-01-01", "Đã lên lịch", "123_456"),   # đã đăng từ lâu
                 bai("b", "2099-01-01", "Đã lên lịch", "789"),       # chưa tới giờ
                 bai("c", "2020-01-01", "Chờ duyệt", "")]}
    h = dung_html(d)
    assert h.count("Chia sẻ lên trang cá nhân</a>") == 1
    assert "sharer.php?u=https%3A%2F%2Fwww.facebook.com%2F123_456" in h
    assert "Chưa đến giờ đăng" in h



def test_chia_se_co_ca_nut_chia_se_va_nut_sao_chep_loi_dan_tuy_chon():
    from hoanbao_mkt.bang_dieu_khien import dung_html

    b = {"ma_bai": "a", "ngay": "2020-01-01", "gio": "08:00", "loai": "L", "media": "", "trang_thai": "Đã lên lịch",
         "ghi_chu": "", "facebook_id": "1_2", "noi_dung": "#tag\nXưởng sofa <dán> bị bong?\nchi tiết"}
    d = {"cap_nhat": "x", "page": "P", "che_do_duyet": True, "sheet_url": "", "kho": [], "khong_loc_thang": True, "bai": [b]}
    xem = dung_html(d)
    assert "Chia sẻ lên trang cá nhân</a>" in xem and "chep-loi" not in xem   # bản chỉ xem: chỉ có nút chia sẻ
    h = dung_html({**d, "sua_duoc": True})
    assert "Chia sẻ lên trang cá nhân</a>" in h
    assert "class='bt chep-loi'" in h and "Xưởng sofa &lt;dán&gt; bị bong?" in h and "0976.884.341" in h
    assert "#tag" not in h.split("data-loi=")[1].split("'")[1]


def test_danh_dau_da_chia_se_tren_bai():
    from hoanbao_mkt.bang_dieu_khien import dung_html

    b = {"ma_bai": "a", "ngay": "2020-01-01", "gio": "08:00", "loai": "L", "media": "", "trang_thai": "Đã lên lịch",
         "ghi_chu": "", "facebook_id": "1_2", "noi_dung": "nd", "da_chia_se": ""}
    d = {"cap_nhat": "x", "page": "P", "che_do_duyet": True, "sheet_url": "", "kho": [], "khong_loc_thang": True, "sua_duoc": True, "bai": [b]}
    h = dung_html(d)
    assert "data-hanh='bai_da_chia_se'" in h and "Đánh dấu đã chia sẻ" in h
    h2 = dung_html({**d, "bai": [{**b, "da_chia_se": "17/10/2026"}]})
    assert "✓ Đã chia sẻ 17/10/2026" in h2 and "data-hanh='bai_da_chia_se'" not in h2 and "Chia sẻ lại" in h2


def test_bai_da_qua_gio_hien_da_dang_con_bai_chua_toi_gio_van_da_len_lich():
    from hoanbao_mkt.bang_dieu_khien import dung_html

    def bai(ma, ngay):
        return {"ma_bai": ma, "ngay": ngay, "gio": "08:00", "loai": "Mẹo", "noi_dung": "x", "media": "",
                "trang_thai": "Đã lên lịch", "ghi_chu": "", "facebook_id": "123", "da_chia_se": ""}

    html = dung_html({"cap_nhat": "x", "page": "P", "che_do_duyet": False, "sheet_url": "", "kho": [], "khong_loc_thang": True,
                      "bai": [bai("cu", "2020-01-01"), bai("moi", "2099-01-01")]})
    assert "<span class='badge s-ok'>Đã đăng</span>" in html
    assert "data-tt='Đã đăng'" in html and "data-tt='Đã lên lịch'" in html


def test_trang_ket_noi_dang_nhap_chon_page_va_bat_tro_ly():
    from hoanbao_bot.server import tao_ung_dung

    class R:
        def __init__(self, body): self.body, self.status_code, self.content = body, 200, b"x"
        def json(self): return self.body

    goi = []

    class Http:
        def request(self, method, url, params=None, timeout=0):
            goi.append((method, url.split("/", 3)[-1], params))
            if "oauth/access_token" in url: return R({"access_token": "UT"})
            if url.endswith("/me"): return R({"name": "Boss"})
            if url.endswith("/me/accounts"): return R({"data": [{"id": "P1", "name": "Trang A", "access_token": "PT"}]})
            if url.endswith("/subscribed_apps"): return R({"data": [{"name": "Hoan Bao Marketing"}], "success": True})
            return R({})

    app = tao_ung_dung(object(), "sec", "vt")
    import hoanbao_bot.ket_noi as kn
    app2 = __import__("flask").Flask(__name__)
    kn.dang_ky_route(app2, "123", "sec", "vt", http=Http())
    c = app2.test_client()
    trang = c.get("/ket-noi").get_data(as_text=True)
    assert "pages_show_list" in trang and "dialog/oauth" in trang and "client_id=123" in trang
    import re
    state = re.search(r"state=([^&\"']+)", trang).group(1).replace("%2E", ".")
    cb = c.get(f"/ket-noi/callback?code=abc&state={state}").get_data(as_text=True)
    assert "Trang A" in cb and "Enable assistant" in cb
    assert c.get("/ket-noi/callback?code=abc&state=sai.sai").status_code == 400
    ok = c.post("/ket-noi/bat", data={"state": state, "page_id": "P1", "page_name": "Trang A", "t": "PT"}).get_data(as_text=True)
    assert "Assistant enabled" in ok and "Hoan Bao Marketing" in ok
    assert any(m == "POST" and p.endswith("subscribed_apps") for m, p, _ in goi)
    assert "PT" not in c.get("/ket-noi").get_data(as_text=True)


def test_bang_dieu_khien_chi_hien_bai_cua_thang_hien_tai():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from hoanbao_mkt.bang_dieu_khien import dung_html

    hn = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    thang_truoc = f"{hn.year - 1}-12-15" if hn.month == 1 else f"{hn.year}-{hn.month - 1:02d}-15"

    def bai(ma, ngay):
        return {"ma_bai": ma, "ngay": ngay, "gio": "08:00", "loai": "Mẹo", "noi_dung": f"noi dung {ma}", "media": "",
                "trang_thai": "Đã lên lịch", "ghi_chu": "", "facebook_id": "1", "da_chia_se": ""}

    html = dung_html({"cap_nhat": "x", "page": "P", "che_do_duyet": False, "sheet_url": "", "kho": [],
                      "bai": [bai("cu", thang_truoc), bai("moi", f"{hn.year}-{hn.month:02d}-28")]})
    assert "noi dung moi" in html and "noi dung cu" not in html
