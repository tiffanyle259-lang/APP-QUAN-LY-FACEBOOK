from datetime import date, datetime, timedelta, timezone

import pytest

from hoanbao_mkt.cau_hinh import CauHinh
from hoanbao_mkt.du_lieu import doc_du_lieu, lam_sach
from hoanbao_mkt.duyet_bai import doc_gio, doc_ngay, drive_id_tu_link
from hoanbao_mkt.facebook import Fanpage, LoiFacebook
from hoanbao_mkt.ke_hoach import lap_ke_hoach
from hoanbao_mkt.kho_anh import FileMedia, chon_file
from hoanbao_mkt.viet_bai import du_lieu_cua_bai, so_lieu_la, tao_yeu_cau

CFG = CauHinh.doc()


@pytest.fixture(scope="module")
def du_lieu():
    return doc_du_lieu(CFG.file_du_lieu, CFG["cot_bo_qua"])


def ke_hoach(du_lieu, thu_hai=date(2026, 10, 12)):
    return lap_ke_hoach(du_lieu, thu_hai, CFG["thu_muc"], CFG.mui_gio)


@pytest.mark.parametrize("vao, ra", [
    ("[cần bổ sung]", None),
    ("—", None),
    (None, None),
    ("Pha vào keo theo tỉ lệ: [cần bổ sung]", None),
    ("Pha vào keo theo tỉ lệ trước khi dùng; tỉ lệ pha: [cần bổ sung]", "Pha vào keo theo tỉ lệ trước khi dùng"),
    ("3kg, 15kg (theo nhãn); web ghi 10kg, 180kg – xác nhận", "3kg, 15kg"),
    ("Chống vàng hóa (theo nhãn)", "Chống vàng hóa"),
    ("Chịu nhiệt tốt", "Chịu nhiệt tốt"),
])
def test_lam_sach(vao, ra):
    assert lam_sach(vao) == ra


def test_doc_file_khong_con_thong_tin_chua_chac(du_lieu):
    assert len(du_lieu.lich) == 6  # Chủ nhật không đăng
    toan_bo = str([sp.thong_tin for sp in du_lieu.san_pham]) + str(du_lieu.cong_ty)
    assert "cần bổ sung" not in toan_bo
    assert "xác nhận" not in toan_bo
    assert "Giá tham khảo trên web (VNĐ)" not in toan_bo  # cột bị bỏ qua theo config
    assert not any("LƯU Ý" in d for d in du_lieu.cong_ty)
    assert du_lieu.tim_san_pham("228").thong_tin["Quy cách đóng gói"] == "3kg, 15kg"


def test_ke_hoach_tuan(du_lieu):
    ds = ke_hoach(du_lieu)
    assert [b.ngay.weekday() for b in ds] == [0, 1, 2, 3, 4, 5]
    thu2, thu3, thu4, thu5, thu6, thu7 = ds
    assert thu2.thu_muc[0] == thu2.san_pham[0].thu_muc
    assert thu2.thoi_diem.hour == 8 and thu2.thoi_diem.utcoffset() == timedelta(hours=7)
    assert thu3.thu_muc[0] == "anh-minh-hoa-chung"
    assert thu4.thu_muc[0] == "video-demo" and thu4.uu_tien_video
    assert thu5.thu_muc[0].startswith("nganh-")
    assert thu6.thu_muc[0] == "khach-hang"
    assert thu7.thu_muc[0] == "nha-may" and thu7.nhom_khach.mua_qua == "Đại lý"
    # Sản phẩm của tuần đi cùng nhóm khách dùng sản phẩm đó
    assert thu2.san_pham[0].ma in thu4.nhom_khach.ma_san_pham


def test_xoay_vong_san_pham_moi_tuan(du_lieu):
    ma = [ke_hoach(du_lieu, date(2026, 10, 12) + timedelta(weeks=i))[0].san_pham[0].ma for i in range(7)]
    assert len(set(ma)) == 7
    assert all(not du_lieu.tim_san_pham(m).la_phu_gia for m in ma)


def test_yeu_cau_ai_chi_chua_du_lieu_cua_bai(du_lieu):
    ds = ke_hoach(du_lieu)
    yeu_cau = tao_yeu_cau(ds, du_lieu)
    assert all(b.ma_bai in yeu_cau for b in ds)
    assert "Kênh tiếp cận" not in yeu_cau


def test_phat_hien_so_lieu_bia(du_lieu):
    bai = ke_hoach(du_lieu)[0]
    nguon = du_lieu_cua_bai(bai, du_lieu)
    assert so_lieu_la("Tiết kiệm khoảng 50% keo, gọi 0976.884.341", nguon) == []
    assert so_lieu_la("Bền tới 10 năm, chịu nhiệt 120 độ", nguon) == ["10", "120"]


def test_chon_file():
    hom_nay = date(2026, 10, 12)
    ds = [
        FileMedia("a", "IMG_001.jpg", "image/jpeg"),
        FileMedia("b", "phun-mut-sofa.jpg", "image/jpeg"),
        FileMedia("c", "phun mut sofa.mp4", "video/mp4"),
        FileMedia("d", "sofa-moi-dung.jpg", "image/jpeg", lan_dung_cuoi=hom_nay - timedelta(days=3)),
    ]
    tk = ["sofa", "phun"]
    assert chon_file(ds, tk, False, set(), hom_nay, 28).id == "b"
    assert chon_file(ds, tk, True, set(), hom_nay, 28).id == "c"
    assert chon_file(ds, tk, False, {"b", "c"}, hom_nay, 28).id == "a"  # "d" vừa dùng 3 ngày trước
    assert chon_file(ds, [], False, {"a", "b", "c", "d"}, hom_nay, 28) is None


def test_doc_o_trong_sheet():
    assert drive_id_tu_link("https://drive.google.com/file/d/1AbC_dEf-123456789/view?usp=sharing") == "1AbC_dEf-123456789"
    assert drive_id_tu_link("https://drive.google.com/open?id=1AbC_dEf-123456789") == "1AbC_dEf-123456789"
    assert drive_id_tu_link("") is None
    assert doc_ngay("2026-10-12") == doc_ngay("12/10/2026") == date(2026, 10, 12)
    assert doc_gio("8:00:00").hour == 8 and doc_gio("19h30").minute == 30


def test_khong_hen_gio_trong_qua_khu():
    page = Fanpage("1", "token", "v24.0")
    with pytest.raises(LoiFacebook):
        page.len_lich("x", datetime.now(timezone.utc) + timedelta(minutes=5))
    with pytest.raises(LoiFacebook):
        page.len_lich("x", datetime.now(timezone.utc) + timedelta(days=40))


# ---- Tự xếp ảnh vào kho ----
from hoanbao_mkt import phan_loai


class KhoGia:
    def __init__(self, files):
        self.files, self.da_chuyen, self.thu_muc, self.nguon = files, [], {}, {}

    def id_thu_muc(self, ten, tao=False):
        return self.thu_muc.setdefault(ten, f"id:{ten}")

    def liet_ke_de_quy(self, _):
        return self.files

    def tai_bytes(self, _):
        from io import BytesIO
        from PIL import Image
        buf = BytesIO()
        Image.new("RGB", (40, 30), "white").save(buf, "PNG")
        return buf.getvalue()

    def chuyen(self, file_id, tu, den, ten_moi=None):
        self.nguon[file_id] = tu
        self.da_chuyen.append((file_id, den, ten_moi))


def test_phan_loai_kho(du_lieu):
    kho = KhoGia([
        {"id": "a", "name": "IMG_1.jpg", "mimeType": "image/jpeg", "parents": ["thu-muc-con"]},
        {"id": "b", "name": "IMG_2.png", "mimeType": "image/png"},
        {"id": "c", "name": "phun mut sofa 339.mp4", "mimeType": "video/mp4"},
        {"id": "d", "name": "ghi-chu.pdf", "mimeType": "application/pdf"},
    ])
    tra = iter([
        phan_loai.KetQuaAnh(thu_muc="keo-phun-228", tu_khoa=["Phun Mút", "sofa"], chac_chan=True),
        phan_loai.KetQuaAnh(thu_muc="thu-muc-la", tu_khoa=["gì đó"], chac_chan=True),
    ])
    bao_cao = phan_loai.chay(kho, du_lieu, CFG["thu_muc"], lambda anh, mo_ta: next(tra))
    dich = {f: den for f, den, _ in kho.da_chuyen}
    assert dich["a"] == "id:keo-phun-228"
    assert dich["b"] == "id:_can-xem-lai"  # thư mục AI trả không có trong danh sách
    assert dich["c"] == "id:keo-phun-339"  # video khớp mã sản phẩm trong tên file
    assert "d" not in dich and any("bỏ qua" in d for d in bao_cao)
    assert kho.nguon["a"] == "thu-muc-con"  # lấy từ thư mục con thật sự chứa file
    ten = next(t for f, _, t in kho.da_chuyen if f == "a")
    assert ten.startswith("phun-mut-sofa-") and ten.endswith(".jpg")


def test_mo_ta_thu_muc_khong_co_video(du_lieu):
    mo_ta = phan_loai.mo_ta_thu_muc(du_lieu, CFG["thu_muc"])
    assert "video-demo" not in mo_ta and "keo-phun-228" in mo_ta and "khach-hang" in mo_ta


# ---- Bảng điều khiển HTML ----
from hoanbao_mkt.bang_dieu_khien import dung_html


def test_bang_dieu_khien_html():
    d = {"cap_nhat": "21:00 06/10/2026", "page": "Keo dán giày", "che_do_duyet": True, "khong_loc_thang": True,
         "sheet_url": "https://docs.google.com/spreadsheets/d/abc",
         "bai": [
             {"ma_bai": "1", "ngay": "2026-10-12", "gio": "08:00", "loai": "Giới thiệu", "noi_dung": "Xin chào <script>x</script>",
              "media": "", "trang_thai": "Chờ duyệt", "ghi_chu": "Kiểm tra số liệu: 70", "facebook_id": ""},
             {"ma_bai": "2", "ngay": "2026-10-13", "gio": "19:30", "loai": "Mẹo", "noi_dung": "b",
              "media": "https://drive.google.com/file/d/x/view", "trang_thai": "Đã lên lịch", "ghi_chu": "", "facebook_id": "1:2"}],
         "kho": [{"ten": "keo-x66", "so_file": 0}, {"ten": "_chua-phan-loai", "so_file": 3}]}
    out = dung_html(d)
    assert "<script>x" not in out and "&lt;script&gt;" in out  # nội dung bị thoát, không chạy được
    assert "Thứ 2 12/10" in out and "Đã lên lịch" in out
    assert "1</b> bài đang chờ duyệt" in out and "3</b> file chưa xếp loại" in out and "keo-x66" in out


def test_khung_them_moi_ngay_va_ma_bai_khong_trung(du_lieu):
    from hoanbao_mkt.du_lieu import khung_phu
    them = [{"gio": "12:00", "loai_bai": ["Mẹo dùng keo"]}, {"gio": "20:30", "loai_bai": ["Theo ngành", "Giới thiệu sản phẩm"]}]
    du_lieu.lich = khung_phu(du_lieu.lich, them)
    assert len(du_lieu.lich) == 18
    ds = ke_hoach(du_lieu)
    assert len(ds) == 18 and len({b.ma_bai for b in ds}) == 18
    assert ds[0].ma_bai.endswith("_thu2")  # bài gốc giữ mã cũ
    assert any(b.ma_bai.endswith("_thu2_1200") for b in ds)


def test_chon_file_uu_tien_cung_file_chua_dung_du_khop_tu_khoa_hon():
    from hoanbao_mkt.kho_anh import FileMedia, chon_file

    hom_nay = date(2026, 10, 22)
    ds = [FileMedia("cu", "228 sofa phun.jpg", "image/jpeg", date(2026, 10, 20)),
          FileMedia("trung", "228 sofa phun 2.jpg", "image/jpeg"),
          FileMedia("moi", "anh khac.jpg", "image/jpeg")]
    assert chon_file(ds, ["228", "sofa", "phun"], False, set(), hom_nay, 28, {"trung"}).id == "moi"
    assert chon_file(ds, ["228"], False, {"moi"}, hom_nay, 28, {"trung"}).id == "trung"  # hết file mới thì mới dùng lại


def test_video_dang_reel_va_roi_ve_video_thuong_khi_meta_tu_choi(tmp_path, monkeypatch):
    from hoanbao_mkt import facebook as fb

    f = tmp_path / "v.mp4"
    f.write_bytes(b"x" * 10)
    goi = []

    class R:
        def __init__(self, body, code=200):
            self.body, self.status_code, self.content = body, code, b"x"
        def json(self): return self.body
        text = ""

    def post(url, data=None, files=None, headers=None, timeout=0):
        goi.append(url.rsplit("/", 1)[-1] if "rupload" not in url else "rupload")
        if url.endswith("/video_reels") and data.get("upload_phase") == "start":
            return R({"video_id": "V1", "upload_url": "https://rupload.facebook.com/video-upload/v24.0/V1"})
        return R({"success": True, "id": "VIDEO_THUONG"})

    monkeypatch.setattr(fb.requests, "post", post)
    page = fb.Fanpage("P", "T", "v24.0")
    gio = datetime.now(timezone.utc) + timedelta(days=2)
    assert page.len_lich("nd", gio, str(f), la_video=True, ten_file="v.mp4") == "V1"
    assert page.loai_cuoi == "Reel" and goi == ["video_reels", "rupload", "video_reels"]

    def post_loi(url, data=None, files=None, headers=None, timeout=0):
        if url.endswith("/video_reels"):
            return R({"error": {"message": "video ngang", "code": 100}}, 400)
        return R({"id": "VIDEO_THUONG"})

    monkeypatch.setattr(fb.requests, "post", post_loi)
    assert page.len_lich("nd", gio, str(f), la_video=True, ten_file="v.mp4") == "VIDEO_THUONG"
    assert page.loai_cuoi == "video" and "video ngang" in page.ly_do_khong_reel


def test_nguon_chung_loc_video_va_chi_chon_khi_khop_tu_khoa():
    from hoanbao_mkt.kho_anh import FileMedia, chon_file, file_nguon_chung_hop_le

    assert file_nguon_chung_hop_le("228_vuong_1080x1080.jpg", "image/jpeg", False)
    assert not file_nguon_chung_hop_le("anh.jpg", "image/jpeg", True)  # ảnh nằm trong thư mục video
    assert file_nguon_chung_hop_le("a.mp4", "video/mp4", True, video_cho_phep=True)
    assert not file_nguon_chung_hop_le("a.mp4", "video/mp4", True, video_cho_phep=False)  # video ngoài thư mục được phép
    ds = [FileMedia("a", "SPRO_vuong_1080x1080.jpg", "image/jpeg", can_khop=True),
          FileMedia("b", "228_vuong_1080x1080.jpg", "image/jpeg", can_khop=True)]
    assert chon_file(ds, ["228"], False, set(), date(2026, 11, 11), 28).id == "b"
    assert chon_file(ds, ["339"], False, {"a"}, date(2026, 11, 11), 28).id == "b"  # xoay vòng: hết file khớp vẫn lấy file chung chưa dùng


def test_nguon_chung_duyet_thu_muc_loai_tru_va_chi_lay_video_trong_thu_muc_duoc_phep():
    from hoanbao_mkt.kho_anh import FOLDER, KhoDrive

    cay = {
        "goc": [("f1", "SPRO", FOLDER), ("f2", "VIDEO-SACH-AI", FOLDER), ("f3", "VIDEO CLIP THẬT", FOLDER),
                ("f4", "SEO", FOLDER), ("f5", "VIDEO-REEL", FOLDER), ("i0", "228_doc.jpg", "image/jpeg")],
        "f1": [("i1", "spro.jpg", "image/jpeg")],
        "f2": [("v1", "CHINH_01.mp4", "video/mp4"), ("t1", "huong-dan.txt", "text/plain")],
        "f3": [("v2", "clip.mp4", "video/mp4")],
        "f4": [("i2", "seo.jpg", "image/jpeg")],
        "f5": [("v3", "reel.mp4", "video/mp4")],
    }
    kho = KhoDrive(None, "k", ["goc"], ["seo", "video clip that"], ["video sach ai", "reel"])
    kho.anh_tu = []  # không giới hạn thư mục ảnh
    kho._liet_ke = lambda q, fields: [{"id": i, "name": n, "mimeType": m} for i, n, m in cay[q.split("'")[1]]]
    ten = sorted(f.id for f in kho.file_nguon_chung())
    assert ten == ["i0", "i1", "v1", "v3"]  # ảnh gốc + ảnh SPRO + video sạch AI + reel; bỏ SEO và VIDEO CLIP THẬT


def test_nguon_chung_anh_chi_lay_trong_thu_muc_anh_duoc_phep():
    from hoanbao_mkt.kho_anh import FOLDER, KhoDrive

    cay = {
        "goc": [("a1", "ANH-SACH-AI", FOLDER), ("a2", "ẢNH QUẢNG CÁO", FOLDER), ("a3", "SPRO", FOLDER),
                ("a4", "ẢNH ĐĂNG SHOPEE", FOLDER), ("i0", "loose.jpg", "image/jpeg")],
        "a1": [("i1", "ai.jpg", "image/jpeg")],
        "a2": [("i2", "qc.jpg", "image/jpeg"), ("b", "BANNER DISPLAY", FOLDER)],
        "b": [("i3", "728x90.jpg", "image/jpeg")],
        "a3": [("i4", "spro.jpg", "image/jpeg")],
        "a4": [("i5", "shopee.png", "image/png")],
    }
    kho = KhoDrive(None, "k", ["goc"], ["banner display"], [], ["anh sach ai", "anh quang cao"])
    kho._liet_ke = lambda q, fields: [{"id": i, "name": n, "mimeType": m} for i, n, m in cay[q.split("'")[1]]]
    assert sorted(f.id for f in kho.file_nguon_chung()) == ["i1", "i2"]  # chỉ ảnh sạch AI + ảnh quảng cáo, bỏ banner display


def test_chi_dung_nguon_chung_bo_qua_kho_marketing():
    from hoanbao_mkt.kho_anh import FOLDER, KhoDrive

    cay = {"goc": [("a1", "ANH-SACH-AI", FOLDER)], "a1": [("i1", "ai.jpg", "image/jpeg")]}
    kho = KhoDrive(None, "k", ["goc"], [], [], ["anh sach ai"], chi_nguon_chung=True)
    kho._liet_ke = lambda q, fields: [{"id": i, "name": n, "mimeType": m} for i, n, m in cay[q.split("'")[1]]]
    assert [f.id for f in kho.file_trong("keo-phun-228")] == ["i1"]  # không hỏi Kho-Marketing


def test_chu_nhat_co_khung_rieng_va_ma_bai_khong_trung(du_lieu):
    from hoanbao_mkt.du_lieu import khung_phu

    cn = [{"gio": "08:00", "loai_bai": "Giới thiệu sản phẩm"}, {"gio": "12:00", "loai_bai": "Video demo thật"}]
    du_lieu.lich = khung_phu(du_lieu.lich, [{"gio": "10:00", "loai_bai": ["Mẹo dùng keo"]}], cn)
    ds = ke_hoach(du_lieu)
    chu_nhat = [b for b in ds if b.ngay.weekday() == 6]
    assert [b.thoi_diem.hour for b in chu_nhat] == [8, 12]
    assert chu_nhat[1].uu_tien_video and len({b.ma_bai for b in ds}) == len(ds)


def test_vong_hoc_xep_hang_va_dua_bai_mau_cho_ai():
    from types import SimpleNamespace as NS

    from hoanbao_mkt import hoc
    from hoanbao_mkt.viet_bai import tao_yeu_cau

    tho = [{"id": "1", "message": "Bài hay về sofa", "reactions": {"summary": {"total_count": 10}},
            "comments": {"summary": {"total_count": 5}}, "shares": {"count": 2}},
           {"id": "2", "message": "Bài thường", "reactions": {"summary": {"total_count": 1}}}]
    dong = [NS(noi_dung="Bài hay về sofa", loai_bai="Mẹo dùng keo", gio="12:00"),
            NS(noi_dung="Bài thường", loai_bai="Theo ngành", gio="20:30")]
    ph = hoc.phan_tich(tho, dong)
    assert ph["loai"][0][0] == "Mẹo dùng keo" and ph["gio"][0][0] == "12:00" and ph["top"][0]["id"] == "1"
    assert hoc.bai_mau(ph)[0] == "Bài hay về sofa" and "TOP" in "\n".join(hoc.tom_tat(ph))
    assert "ĐẠT TƯƠNG TÁC CAO" in tao_yeu_cau([], object(), ["Bài hay về sofa"])
