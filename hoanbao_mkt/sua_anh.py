"""Kiểm tra và sửa các bài chưa đăng bị gán sai ảnh/video (không đúng sản phẩm, hoặc bài video mà gắn ảnh)."""

from __future__ import annotations

from datetime import datetime, timedelta

from .duyet_bai import CHO_DUYET, DA_LEN_LICH, DUYET, doc_gio, doc_ngay
from .ke_hoach import bo_dau
from .kho_anh import FileMedia, chon_file, khop_ma, ma_mo_rong


def _file_day_du(drive, fid: str, cache: dict) -> FileMedia | None:
    try:
        f = drive.files().get(fileId=fid, fields="id,name,mimeType,parents", supportsAllDrives=True).execute()
    except Exception:  # noqa: BLE001
        return None
    cha = (f.get("parents") or [""])[0]
    if cha not in cache:
        try:
            cache[cha] = drive.files().get(fileId=cha, fields="name", supportsAllDrives=True).execute().get("name", "")
        except Exception:  # noqa: BLE001
            cache[cha] = ""
    return FileMedia(f["id"], f["name"], f["mimeType"], nhom=cache[cha], can_khop=True)


def chay(cfg, drive, sheet, kho, du_lieu, page, sua: bool, lap_ke_hoach, drive_id_tu_link) -> None:
    bay_gio = datetime.now(cfg.mui_gio)
    ke_hoach: dict = {}
    cache_cha: dict = {}
    sai = []
    for d in sheet.doc_tat_ca():
        if d.trang_thai.strip() not in (DA_LEN_LICH, DUYET, CHO_DUYET) or not d.media.strip():
            continue
        try:
            gio_dang = datetime.combine(doc_ngay(d.ngay), doc_gio(d.gio), tzinfo=cfg.mui_gio)
        except Exception:  # noqa: BLE001
            continue
        if gio_dang < bay_gio + timedelta(minutes=30):
            continue  # đã đăng hoặc sắp tới giờ: không đụng
        ngay = doc_ngay(d.ngay)
        thu_hai = ngay - timedelta(days=ngay.weekday())
        if thu_hai not in ke_hoach:
            ke_hoach[thu_hai] = {b.ma_bai: b for b in lap_ke_hoach(du_lieu, thu_hai, cfg["thu_muc"], cfg.mui_gio)}
        b = ke_hoach[thu_hai].get(d.ma_bai)
        fid = drive_id_tu_link(d.media)
        if not b or not fid:
            continue
        fm = _file_day_du(drive, fid, cache_cha)
        if not fm:
            sai.append((d, b, "file không còn/không đọc được"))
            continue
        ma_goc = [sp.ma for sp in b.san_pham]
        ma = ma_mo_rong(ma_goc, cfg.get("ma_phu"))
        khac = [c for sp in du_lieu.san_pham if sp.ma not in ma_goc for c in ma_mo_rong([sp.ma], cfg.get("ma_phu"))
                if c not in ma]
        video_tu = [bo_dau(x) for x in (cfg.get("nguon_chung_video_tu") or [])]
        if b.uu_tien_video and not fm.la_video:
            sai.append((d, b, f"bài video nhưng gắn ảnh ({fm.ten})"))
        elif fm.la_video and not any(x in bo_dau(fm.nhom) for x in video_tu):
            sai.append((d, b, f"video ngoài thư mục được phép ({fm.ten}, thư mục {fm.nhom})"))
        elif ma and khop_ma(fm, khac) and not khop_ma(fm, ma):
            sai.append((d, b, f"sai sản phẩm: bài {'/'.join(ma_goc)} nhưng file '{fm.ten}' (thư mục {fm.nhom}) của sản phẩm khác"))
    print(f"{len(sai)} bài chưa đăng gán sai ảnh/video{' (đang sửa)' if sua else ' (chỉ xem)'}.")
    da_chon: set[str] = set()
    dang_dung = {drive_id_tu_link(x.media) for x in sheet.doc_tat_ca() if x.media.strip() and x.trang_thai.strip() != "Bỏ"} - {None}
    for d, b, ly_do in sai:
        print(f"  - {d.ma_bai} ({d.ngay} {d.gio}) [{d.trang_thai}] {ly_do}")
        if not sua:
            continue
        try:
            if d.facebook_id.strip():
                page.xoa(d.facebook_id.strip())  # hủy bài đang hẹn giờ để gán lại cho đúng
            media = chon_file(kho.file_nguon_chung(), b.tu_khoa_media, b.uu_tien_video, da_chon, bay_gio.date(),
                              cfg.get("khong_lap_lai_trong_ngay", 28), dang_dung,
                              ma_mo_rong([sp.ma for sp in b.san_pham], cfg.get("ma_phu")), b.uu_tien_video)
            if media:
                da_chon.add(media.id)
                sheet.gan_media(d.dong, media.link, f"File: {media.ten} (đã đổi cho đúng sản phẩm)")
                sheet.cap_nhat(d.dong, DUYET, f"File: {media.ten} (đã đổi cho đúng sản phẩm)", "")
                print(f"      → {media.ten}")
            else:
                sheet.gan_media(d.dong, "", "Thiếu ảnh/video đúng sản phẩm trong thư mục nguồn chung")
                sheet.cap_nhat(d.dong, CHO_DUYET, "Thiếu ảnh/video đúng sản phẩm trong thư mục nguồn chung", "")
                print("      → chưa có file đúng, chuyển Chờ duyệt")
        except Exception as e:  # noqa: BLE001
            print(f"      ✗ lỗi: {e}")
