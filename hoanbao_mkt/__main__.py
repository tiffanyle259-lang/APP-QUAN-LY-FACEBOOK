"""Chạy: python -m hoanbao_mkt <lệnh>

  xem-ke-hoach [--tuan 2026-10-12] [--ai]   Xem kế hoạch tuần (không đụng Drive/Sheet/Facebook)
  tao-tuan     [--tuan 2026-10-12]          AI viết bài + chọn ảnh, ghi vào Sheet duyệt
  len-lich                                  Lên lịch Facebook cho các bài trạng thái "Duyệt"
  phan-loai                                 Xếp ảnh/video thả vào _chua-phan-loai về thư mục con (AI xem ảnh)
  tao-thu-muc                               Tạo sẵn các thư mục con trong Kho-Marketing
  kiem-tra                                  Kiểm tra kết nối Facebook, Drive, Sheet, Claude
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from datetime import date, datetime

import anthropic

from .cau_hinh import CauHinh, ThieuCauHinh
from .du_lieu import DuLieuNen, doc_du_lieu
from .duyet_bai import (CHO_DUYET, DA_LEN_LICH, DUYET, LOI, SheetDuyet, doc_gio, doc_ngay,
                        drive_id_tu_link)
from .ke_hoach import BaiKeHoach, lap_ke_hoach, thu_hai_tuan_sau


def _google(cfg: CauHinh):
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_service_account_info(
        cfg.google_service_account(),
        scopes=["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"],
    )
    return (build("drive", "v3", credentials=creds, cache_discovery=False),
            build("sheets", "v4", credentials=creds, cache_discovery=False))


def _doc_du_lieu(cfg: CauHinh, drive=None) -> DuLieuNen:
    """Mặc định đọc file trong repo; nếu có DATA_DRIVE_FILE_ID thì đọc bản mới nhất trên Drive."""
    duong_dan = cfg.file_du_lieu
    file_id = CauHinh.bien("DATA_DRIVE_FILE_ID", bat_buoc=False)
    if file_id and drive is not None:
        from googleapiclient.http import MediaIoBaseDownload
        meta = drive.files().get(fileId=file_id, fields="mimeType", supportsAllDrives=True).execute()
        if meta["mimeType"] == "application/vnd.google-apps.spreadsheet":
            req = drive.files().export_media(
                fileId=file_id, mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            req = drive.files().get_media(fileId=file_id, supportsAllDrives=True)
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as fh:
            dl, xong = MediaIoBaseDownload(fh, req), False
            while not xong:
                _, xong = dl.next_chunk()
        duong_dan = fh.name
    return doc_du_lieu(duong_dan, cfg.get("cot_bo_qua"))


def _tuan(cfg: CauHinh, tuan: str | None) -> date:
    if tuan:
        return date.fromisoformat(tuan)
    return thu_hai_tuan_sau(datetime.now(cfg.mui_gio).date())


def _in_ke_hoach(ds: list[BaiKeHoach]) -> None:
    for b in ds:
        sp = ", ".join(s.ma for s in b.san_pham) or "—"
        print(f"{b.ma_bai}  {b.thoi_diem:%H:%M}  {b.khung.loai_bai}")
        print(f"    Sản phẩm: {sp} | Nhóm khách: {b.nhom_khach.ten if b.nhom_khach else '—'}")
        print(f"    Thư mục media: {' → '.join(b.thu_muc) or '—'}{' (ưu tiên video)' if b.uu_tien_video else ''}")


def xem_ke_hoach(cfg: CauHinh, args) -> None:
    du_lieu = _doc_du_lieu(cfg)
    ds = lap_ke_hoach(du_lieu, _tuan(cfg, args.tuan), cfg["thu_muc"], cfg.mui_gio)
    _in_ke_hoach(ds)
    if args.ai:
        from .viet_bai import du_lieu_cua_bai, so_lieu_la, viet_ca_tuan
        bai_viet = viet_ca_tuan(ds, du_lieu, cfg["ai"]["model"], cfg["ai"]["effort"])
        for b in ds:
            bv = bai_viet.get(b.ma_bai)
            print(f"\n===== {b.ma_bai} – {b.khung.loai_bai} =====")
            if not bv:
                print("(AI không trả bài này)")
                continue
            print(bv.noi_dung)
            print(f"[từ khóa media: {', '.join(bv.tu_khoa_media)}]")
            if la := so_lieu_la(bv.noi_dung, du_lieu_cua_bai(b, du_lieu)):
                print(f"⚠ Số liệu không có trong file: {', '.join(la)}")


def tao_tuan(cfg: CauHinh, args) -> None:
    from .kho_anh import KhoDrive, chon_file
    from .viet_bai import du_lieu_cua_bai, so_lieu_la, viet_ca_tuan

    drive, sheets = _google(cfg)
    sheet = SheetDuyet(sheets, CauHinh.bien("SHEET_DUYET_ID"))
    sheet.dam_bao_cau_truc(cfg["che_do_duyet"])
    can_duyet = sheet.che_do_duyet(cfg["che_do_duyet"])
    kho = KhoDrive(drive, CauHinh.bien("DRIVE_KHO_ID"))

    du_lieu = _doc_du_lieu(cfg, drive)
    thu_hai = _tuan(cfg, args.tuan)
    ds = lap_ke_hoach(du_lieu, thu_hai, cfg["thu_muc"], cfg.mui_gio)
    print(f"Tạo {len(ds)} bài cho tuần {thu_hai:%d/%m/%Y}. Chế độ duyệt: {'BẬT' if can_duyet else 'TẮT'}")
    bai_viet = viet_ca_tuan(ds, du_lieu, cfg["ai"]["model"], cfg["ai"]["effort"])

    hom_nay = datetime.now(cfg.mui_gio).date()
    da_chon: set[str] = set()
    dong_moi = []
    for b in ds:
        bv = bai_viet.get(b.ma_bai)
        if not bv:
            print(f"  ! AI không trả bài {b.ma_bai}, bỏ qua.")
            continue
        canh_bao = []
        if la := so_lieu_la(bv.noi_dung, du_lieu_cua_bai(b, du_lieu)):
            canh_bao.append(f"Kiểm tra số liệu không có trong file: {', '.join(la)}")

        media = None
        for tm in b.thu_muc:
            media = chon_file(kho.file_trong(tm), b.tu_khoa_media + bv.tu_khoa_media, b.uu_tien_video,
                              da_chon, hom_nay, cfg.get("khong_lap_lai_trong_ngay", 28))
            if media:
                break
        if media:
            da_chon.add(media.id)
        else:
            canh_bao.append(f"Không có ảnh/video trong thư mục: {', '.join(b.thu_muc) or '(chưa cấu hình)'}")

        trang_thai = CHO_DUYET if (can_duyet or canh_bao) else DUYET
        ghi_chu = "; ".join(canh_bao) or (f"File: {media.ten}" if media else "")
        dong_moi.append([b.ma_bai, b.ngay.isoformat(), b.khung.gio_dang, b.khung.loai_bai,
                         bv.noi_dung, media.link if media else "", trang_thai, ghi_chu, ""])
        print(f"  {b.ma_bai}: {trang_thai}{' – ' + ghi_chu if canh_bao else ''}")

    print(f"Đã ghi {sheet.them(dong_moi)} bài mới vào Sheet.")
    if not can_duyet:
        len_lich(cfg, args, drive=drive, sheets=sheets)


def len_lich(cfg: CauHinh, args, drive=None, sheets=None) -> None:
    from .facebook import Fanpage
    from .kho_anh import KhoDrive

    if drive is None:
        drive, sheets = _google(cfg)
    sheet = SheetDuyet(sheets, CauHinh.bien("SHEET_DUYET_ID"))
    kho = KhoDrive(drive, CauHinh.bien("DRIVE_KHO_ID"))
    page = Fanpage(CauHinh.bien("FB_PAGE_ID"), CauHinh.bien("FB_PAGE_TOKEN"), cfg["facebook"]["graph_version"])

    cho = [d for d in sheet.doc_tat_ca() if d.trang_thai.strip() == DUYET and not d.facebook_id.strip()]
    print(f"{len(cho)} bài đã duyệt chờ lên lịch.")
    for d in cho:
        duong_dan = None
        try:
            if not d.noi_dung.strip():
                raise ValueError("Nội dung trống")
            thoi_diem = datetime.combine(doc_ngay(d.ngay), doc_gio(d.gio), tzinfo=cfg.mui_gio)
            media_id = drive_id_tu_link(d.media)
            media = kho.thong_tin(media_id) if media_id else None
            duong_dan = kho.tai_ve(media.id) if media else None
            fb_id = page.len_lich(d.noi_dung.strip(), thoi_diem, duong_dan,
                                  la_video=bool(media and media.la_video), ten_file=media.ten if media else "media")
            sheet.cap_nhat(d.dong, DA_LEN_LICH, f"Hẹn đăng {thoi_diem:%H:%M %d/%m/%Y}", fb_id)
            print(f"  ✓ {d.ma_bai} → {fb_id}")
            if media:
                try:
                    kho.danh_dau_da_dung(media.id, thoi_diem)
                except Exception as e:  # không quan trọng: chỉ để tránh lặp ảnh
                    print(f"    (không ghi được ngày dùng ảnh: {e})")
        except Exception as e:
            sheet.cap_nhat(d.dong, LOI, str(e)[:500])
            print(f"  ✗ {d.ma_bai}: {e}")
        finally:
            if duong_dan:
                os.unlink(duong_dan)


def tao_thu_muc(cfg: CauHinh, args) -> None:
    """Tạo sẵn các thư mục con trong Kho-Marketing (chạy lại an toàn, không tạo trùng)."""
    from .kho_anh import KhoDrive

    drive, _ = _google(cfg)
    du_lieu = _doc_du_lieu(cfg, drive)
    ten = [sp.thu_muc for sp in du_lieu.san_pham if sp.thu_muc]
    thu_muc = cfg["thu_muc"]
    ten += [thu_muc["anh_chung"], *thu_muc["theo_nganh"].values()]
    ten += [m for k in du_lieu.lich for m in re.findall(r"thư mục ([a-z0-9]+(?:-[a-z0-9]+)+)", k.nguon_media.lower())]
    ten += ["video-demo", "khach-hang", "nha-may", "_chua-phan-loai", "_can-xem-lai"]
    moi = KhoDrive(drive, CauHinh.bien("DRIVE_KHO_ID")).tao_thu_muc_con(ten)
    print(f"Đã tạo {len(moi)} thư mục mới: {', '.join(moi) or '(không, đã đủ)'}")


def phan_loai_kho(cfg: CauHinh, args) -> None:
    """Xếp ảnh/video trong Kho-Marketing/_chua-phan-loai vào thư mục con bằng AI."""
    from . import phan_loai
    from .kho_anh import KhoDrive

    drive, _ = _google(cfg)
    du_lieu = _doc_du_lieu(cfg, drive)
    client = anthropic.Anthropic()
    ai = cfg["ai"]
    bao_cao = phan_loai.chay(
        KhoDrive(drive, CauHinh.bien("DRIVE_KHO_ID")), du_lieu, cfg["thu_muc"],
        lambda anh, mo_ta: phan_loai.hoi_ai(client, ai["model"], anh, mo_ta))
    print("\n".join(bao_cao) or f"Không có file mới trong '{phan_loai.THU_MUC_CHO}'.")


def kiem_tra(cfg: CauHinh, args) -> None:
    ok = True

    def buoc(ten, ham):
        nonlocal ok
        try:
            print(f"✓ {ten}: {ham()}")
        except Exception as e:
            ok = False
            print(f"✗ {ten}: {e}")

    du_lieu = _doc_du_lieu(cfg)
    print(f"✓ File dữ liệu: {len(du_lieu.san_pham)} sản phẩm, {len(du_lieu.nhom_khach)} nhóm khách, "
          f"{len(du_lieu.lich)} ngày đăng/tuần")
    from .facebook import Fanpage
    from .kho_anh import KhoDrive

    buoc("Facebook", lambda: Fanpage(CauHinh.bien("FB_PAGE_ID"), CauHinh.bien("FB_PAGE_TOKEN"),
                                     cfg["facebook"]["graph_version"]).kiem_tra())
    try:
        drive, sheets = _google(cfg)
    except Exception as e:
        print(f"✗ Google: {e}")
        sys.exit(1)

    def kiem_kho():
        kho = KhoDrive(drive, CauHinh.bien("DRIVE_KHO_ID"))
        ten = {sp.thu_muc for sp in du_lieu.san_pham if sp.thu_muc}
        ds = lap_ke_hoach(du_lieu, _tuan(cfg, None), cfg["thu_muc"], cfg.mui_gio)
        ten |= {tm for b in ds for tm in b.thu_muc}
        thieu = sorted(t for t in ten if not kho.file_trong(t))
        return "đủ ảnh/video" if not thieu else f"thư mục trống hoặc chưa có: {', '.join(thieu)}"

    buoc("Kho Drive", kiem_kho)
    buoc("Sheet duyệt", lambda: SheetDuyet(sheets, CauHinh.bien("SHEET_DUYET_ID")).dam_bao_cau_truc(
        cfg["che_do_duyet"]) or "đọc/ghi được")
    buoc("Claude API", lambda: "có khóa" if CauHinh.bien("ANTHROPIC_API_KEY") else "")
    sys.exit(0 if ok else 1)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="hoanbao_mkt", description="Tự động nội dung fanpage Golden Lion")
    sub = p.add_subparsers(dest="lenh", required=True)
    x = sub.add_parser("xem-ke-hoach")
    x.add_argument("--tuan", help="Ngày Thứ 2 của tuần, dạng 2026-10-12 (mặc định: tuần sau)")
    x.add_argument("--ai", action="store_true", help="Gọi AI viết thử (cần ANTHROPIC_API_KEY)")
    t = sub.add_parser("tao-tuan")
    t.add_argument("--tuan")
    sub.add_parser("len-lich")
    sub.add_parser("tao-thu-muc")
    sub.add_parser("phan-loai")
    sub.add_parser("kiem-tra")
    args = p.parse_args(argv)

    cfg = CauHinh.doc()
    lenh = {"xem-ke-hoach": xem_ke_hoach, "tao-tuan": tao_tuan, "len-lich": len_lich,
            "tao-thu-muc": tao_thu_muc, "phan-loai": phan_loai_kho, "kiem-tra": kiem_tra}
    try:
        lenh[args.lenh](cfg, args)
    except ThieuCauHinh as e:
        print(f"Lỗi cấu hình: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
