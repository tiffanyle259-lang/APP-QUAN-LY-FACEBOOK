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
    assert thu7.thu_muc == ["nha-may"] and thu7.nhom_khach.mua_qua == "Đại lý"
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
    d = {"cap_nhat": "21:00 06/10/2026", "page": "Keo dán giày", "che_do_duyet": True,
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
