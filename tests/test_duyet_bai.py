

def test_chuan_trang_thai_hieu_nhieu_cach_go():
    from hoanbao_mkt.duyet_bai import BO, CHO_DUYET, DUYET, chuan_trang_thai

    for go in ("Duyệt", "duyệt", "Đã duyệt", "DA DUYET", " duyet ", "Duyệt bài"):
        assert chuan_trang_thai(go) == DUYET
    assert chuan_trang_thai("chờ duyệt") == CHO_DUYET
    assert chuan_trang_thai("Hủy") == BO
    assert chuan_trang_thai("linh tinh") == "linh tinh"


def test_don_bai_chon_dung_bai():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from hoanbao_mkt.don_bai import chon_bai
    from hoanbao_mkt.duyet_bai import DongBai

    tz = ZoneInfo("Asia/Ho_Chi_Minh")
    bay_gio = datetime(2026, 10, 17, 12, 0, tzinfo=tz)
    mk = lambda ma, ngay, gio, tt="Chờ duyệt", nd="nd", ghi="": DongBai(2, ma, ngay, gio, "L", nd, "", tt, ghi, "")
    ds = [mk("cu", "2026-10-12", "08:00"), mk("gan", "2026-10-17", "12:10"), mk("ok", "2026-10-20", "08:00"),
          mk("canh_bao", "2026-10-21", "08:00", ghi="Kiểm tra số liệu không có trong file: 60%"),
          mk("rong", "2026-10-22", "08:00", nd=" "), mk("da_duyet", "2026-10-23", "08:00", tt="Duyệt")]
    doi, bo = chon_bai(ds, "duyet", bay_gio, tz)
    assert [b.ma_bai for b in doi] == ["ok"]
    assert {b.ma_bai for b, _ in bo} == {"cu", "gan", "canh_bao", "rong"}
    doi, _ = chon_bai(ds, "bo-qua-gio", bay_gio, tz)
    assert [b.ma_bai for b in doi] == ["cu"]
