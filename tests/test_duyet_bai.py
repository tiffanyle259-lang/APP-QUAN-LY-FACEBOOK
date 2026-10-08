

def test_chuan_trang_thai_hieu_nhieu_cach_go():
    from hoanbao_mkt.duyet_bai import BO, CHO_DUYET, DUYET, chuan_trang_thai

    for go in ("Duyệt", "duyệt", "Đã duyệt", "DA DUYET", " duyet ", "Duyệt bài"):
        assert chuan_trang_thai(go) == DUYET
    assert chuan_trang_thai("chờ duyệt") == CHO_DUYET
    assert chuan_trang_thai("Hủy") == BO
    assert chuan_trang_thai("linh tinh") == "linh tinh"
