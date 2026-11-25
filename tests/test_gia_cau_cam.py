from hoanbao_mkt import gia


def test_bo_cau_toluene_chung_va_gia_si():
    s = "Keo phun.\nCả nhà đều không chứa Toluene/Benzene, an tâm.\nGiá sỉ 1,8tr/thùng\nHotline 0976"
    assert gia.co_cau_cam(s)
    k = gia.lam_sach(s)
    assert "Toluene" not in k and "sỉ" not in k and "Hotline 0976" in k


def test_giu_cau_rieng_228():
    s = "Keo phun 228 không mùi, không chứa Toluene."
    assert not gia.co_cau_cam(s) and gia.lam_sach(s) == s
