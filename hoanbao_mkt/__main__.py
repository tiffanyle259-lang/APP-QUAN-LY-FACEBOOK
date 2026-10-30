"""Chạy: python -m hoanbao_mkt <lệnh>

  xem-ke-hoach [--tuan 2026-10-12] [--ai]   Xem kế hoạch tuần (không đụng Drive/Sheet/Facebook)
  tao-tuan     [--tuan 2026-10-12]          AI viết bài + chọn ảnh, ghi vào Sheet duyệt
  len-lich                                  Lên lịch Facebook cho các bài trạng thái "Duyệt"
  phan-loai                                 Xếp ảnh/video thả vào _chua-phan-loai về thư mục con (AI xem ảnh)
  bang-dieu-khien [--ra file.html]          Xuất trang HTML xem lịch bài, trạng thái duyệt, kho ảnh
  dang-ky-webhook --url https://...         Nối Facebook với máy chủ chatbot (webhook)
  chan-doan --url https://...               Chẩn đoán chatbot: tin có tới không, lỗi ở đâu
  tao-thu-muc                               Tạo sẵn các thư mục con trong Kho-Marketing
  nhap-khach --file khach.csv               Nhập khách từ quảng cáo (CSV của Meta) vào tab Khách hàng
  bao-cao-tuan                              Báo cáo tương tác 7 ngày qua, lưu vào Sheet, gửi email
  kiem-tra                                  Kiểm tra kết nối Facebook, Drive, Sheet, Claude
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path
from datetime import date, datetime, timedelta

import anthropic

from .cau_hinh import CauHinh, ThieuCauHinh
from .du_lieu import DuLieuNen, doc_du_lieu, khung_phu
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
    du_lieu = doc_du_lieu(duong_dan, cfg.get("cot_bo_qua"))
    du_lieu.lich = khung_phu(du_lieu.lich, cfg.get("khung_them") or [])
    return du_lieu


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

    CauHinh.khoa_claude()  # báo lỗi sớm nếu khóa Claude dán sai
    drive, sheets = _google(cfg)
    sheet = SheetDuyet(sheets, CauHinh.bien("SHEET_DUYET_ID"))
    sheet.dam_bao_cau_truc(cfg["che_do_duyet"])
    can_duyet = sheet.che_do_duyet(cfg["che_do_duyet"])
    kho = KhoDrive(drive, CauHinh.bien("DRIVE_KHO_ID"))

    du_lieu = _doc_du_lieu(cfg, drive)
    da_co = {d.ma_bai for d in sheet.doc_tat_ca()}
    if getattr(args, "thang", None):  # cả tháng: mọi tuần chạm tháng đó, chỉ lấy bài có ngày trong tháng
        nam, thg = map(int, args.thang.split("-"))
        dau = date(nam, thg, 1)
        thu_hai_ds = []
        t = dau - timedelta(days=dau.weekday())
        while t.month != (thg % 12) + 1 or t.year != nam + (thg == 12):
            thu_hai_ds.append(t)
            t += timedelta(days=7)
        ds = [b for th in thu_hai_ds for b in lap_ke_hoach(du_lieu, th, cfg["thu_muc"], cfg.mui_gio)
              if (b.ngay.year, b.ngay.month) == (nam, thg)]
        mo_ta = f"tháng {thg}/{nam} ({len(thu_hai_ds)} tuần)"
    else:
        thu_hai = _tuan(cfg, args.tuan)
        ds = lap_ke_hoach(du_lieu, thu_hai, cfg["thu_muc"], cfg.mui_gio)
        mo_ta = f"tuần {thu_hai:%d/%m/%Y}"
    co_san = [b for b in ds if b.ma_bai in da_co]
    if co_san:  # bài đã có trong Sheet thì không nhờ AI viết lại (đỡ tốn tiền, không trùng)
        print(f"Bỏ {len(co_san)} bài đã có sẵn trong Sheet.")
        ds = [b for b in ds if b.ma_bai not in da_co]
    qua = [b for b in ds if b.thoi_diem < datetime.now(cfg.mui_gio) + timedelta(minutes=30)]
    if qua:  # tạo giữa tuần: bỏ các khung giờ đã qua, tránh bài báo lỗi "giờ đăng đã qua"
        print(f"Bỏ {len(qua)} khung giờ đã qua.")
        ds = [b for b in ds if b not in qua]
    print(f"Tạo {len(ds)} bài cho {mo_ta}. Chế độ duyệt: {'BẬT' if can_duyet else 'TẮT'}")
    if not ds:
        return
    bai_viet = viet_ca_tuan(ds, du_lieu, cfg["ai"]["model"], cfg["ai"]["effort"])

    hom_nay = datetime.now(cfg.mui_gio).date()
    da_chon: set[str] = set()
    dang_dung = {drive_id_tu_link(d.media) for d in sheet.doc_tat_ca() if d.media.strip() and d.trang_thai.strip() != "Bỏ"} - {None}
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
                              da_chon, hom_nay, cfg.get("khong_lap_lai_trong_ngay", 28), dang_dung)
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


def gan_anh(cfg: CauHinh, args) -> None:
    """Chọn ảnh/video từ kho cho các bài còn trống cột Ảnh/Video (bài tạo lúc kho chưa có ảnh)."""
    from .kho_anh import KhoDrive, chon_file

    drive, sheets = _google(cfg)
    sheet = SheetDuyet(sheets, CauHinh.bien("SHEET_DUYET_ID"))
    sheet.dam_bao_cau_truc(cfg["che_do_duyet"])
    kho = KhoDrive(drive, CauHinh.bien("DRIVE_KHO_ID"))
    du_lieu = _doc_du_lieu(cfg, drive)
    hom_nay = datetime.now(cfg.mui_gio).date()
    thieu = [d for d in sheet.doc_tat_ca()
             if not d.media.strip() and not d.facebook_id.strip() and d.trang_thai.strip() in (CHO_DUYET, DUYET)]
    print(f"{len(thieu)} bài chưa có ảnh/video.")
    ke_hoach: dict = {}
    da_chon: set[str] = set()
    dang_dung = {drive_id_tu_link(x.media) for x in sheet.doc_tat_ca() if x.media.strip() and x.trang_thai.strip() != "Bỏ"} - {None}
    for d in thieu:
        try:
            ngay = doc_ngay(d.ngay)
            thu_hai = ngay - timedelta(days=ngay.weekday())
            if thu_hai not in ke_hoach:
                ke_hoach[thu_hai] = {b.ma_bai: b for b in lap_ke_hoach(du_lieu, thu_hai, cfg["thu_muc"], cfg.mui_gio)}
            b = ke_hoach[thu_hai].get(d.ma_bai)
            if not b:
                print(f"  - {d.ma_bai}: không có trong kế hoạch tuần, bỏ qua.")
                continue
            media = None
            for tm in b.thu_muc:
                media = chon_file(kho.file_trong(tm), b.tu_khoa_media, b.uu_tien_video, da_chon, hom_nay,
                                  cfg.get("khong_lap_lai_trong_ngay", 28), dang_dung)
                if media:
                    break
            if not media:
                print(f"  - {d.ma_bai}: vẫn chưa có ảnh/video trong {', '.join(b.thu_muc)}.")
                continue
            da_chon.add(media.id)
            sheet.gan_media(d.dong, media.link, f"File: {media.ten}")
            print(f"  ✓ {d.ma_bai} → {media.ten}")
        except Exception as e:
            print(f"  ✗ {d.ma_bai}: {e}")


def len_lich(cfg: CauHinh, args, drive=None, sheets=None) -> None:
    from . import youtube
    from .facebook import Fanpage
    from .kho_anh import KhoDrive

    if drive is None:
        drive, sheets = _google(cfg)
    sheet = SheetDuyet(sheets, CauHinh.bien("SHEET_DUYET_ID"))
    sheet.dam_bao_cau_truc(cfg["che_do_duyet"])  # đặt lại danh sách chọn Trạng thái
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
            if thoi_diem - datetime.now(cfg.mui_gio) > timedelta(days=28):
                print(f"  . {d.ma_bai}: còn quá xa (Meta chỉ nhận trong 29 ngày), giữ 'Duyệt', sẽ tự lên lịch khi tới hạn.")
                continue
            media_id = drive_id_tu_link(d.media)
            media = kho.thong_tin(media_id) if media_id else None
            duong_dan = kho.tai_ve(media.id) if media else None
            fb_id = page.len_lich(d.noi_dung.strip(), thoi_diem, duong_dan,
                                  la_video=bool(media and media.la_video), ten_file=media.ten if media else "media")
            ghi_chu = f"Hẹn đăng {thoi_diem:%H:%M %d/%m/%Y}"
            if media and media.la_video and youtube.da_cau_hinh():
                try:  # YouTube chỉ là phần thêm: lỗi ở đây không làm hỏng bài đã lên lịch Facebook
                    yt_id = youtube.KenhYouTube.tu_moi_truong().dang_video(
                        duong_dan, youtube.tieu_de_tu_noi_dung(d.noi_dung), d.noi_dung.strip(), thoi_diem, media.mime)
                    ghi_chu += f" | YouTube: https://youtu.be/{yt_id}"
                except Exception as e:
                    ghi_chu += f" | YouTube lỗi: {str(e)[:200]}"
                    print(f"    (YouTube lỗi: {e})")
            sheet.cap_nhat(d.dong, DA_LEN_LICH, ghi_chu, fb_id)
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


def nhap_nhom(cfg: CauHinh, args) -> None:
    """Nhập danh sách nhóm Facebook từ file văn bản (mỗi dòng: Tên | link | ngành | luật | trạng thái) vào tab 'Nhóm'."""
    from hoanbao_bot.nhom import SoNhom, doc_van_ban

    rows, bo = doc_van_ban(Path(args.file).read_text(encoding="utf-8"))
    _, sheets = _google(cfg)
    them, cap_nhat = SoNhom(sheets, CauHinh.bien("SHEET_DUYET_ID")).nhap(rows)
    tam_dung = sum(1 for r in rows if r[7] == "Tạm dừng")
    print(f"Đã thêm {them} nhóm mới, cập nhật {cap_nhat} nhóm đã có, {tam_dung} nhóm để Tạm dừng, {len(bo)} dòng bị bỏ.")
    for b in bo:
        print("  -", b)


def bao_cao_tuan(cfg: CauHinh, args) -> None:
    """Lấy số liệu tương tác 7 ngày qua từ Facebook, lưu vào tab 'Báo cáo tuần', gửi email nếu đã cấu hình."""
    from datetime import timedelta

    from . import bao_cao
    from .facebook import Fanpage

    bay_gio = datetime.now(cfg.mui_gio)
    page = Fanpage(CauHinh.bien("FB_PAGE_ID"), CauHinh.bien("FB_PAGE_TOKEN"), cfg["facebook"]["graph_version"])
    ten = page.kiem_tra()
    _, sheets = _google(cfg)
    sheet_id = CauHinh.bien("SHEET_DUYET_ID")
    so = bao_cao.SoBaoCao(sheets, sheet_id)
    bai = page.bai_da_dang(bay_gio - timedelta(days=7))
    try:
        dong_khach = sheets.spreadsheets().values().get(
            spreadsheetId=sheet_id, range="'Khách hàng'!A2:A2000").execute().get("values", [])
    except Exception:
        dong_khach = []
    khach = bao_cao.dem_khach_moi(dong_khach, bay_gio - timedelta(days=7))
    dong = bao_cao.tinh(bai, page.so_nguoi_theo_doi(), so.nguoi_theo_doi_cuoi(), khach, bay_gio)
    so.ghi(dong)
    print(bao_cao.noi_dung_email(dong, ten))
    try:
        from hoanbao_bot.khach import email_da_cau_hinh, gui_email_chi_tiet

        if email_da_cau_hinh():
            ok, ly_do = gui_email_chi_tiet(bao_cao.noi_dung_email(dong, ten))
            print("Đã gửi email báo cáo." if ok else f"Không gửi được email: {ly_do}")
    except Exception as e:
        print(f"Bỏ qua email: {e}")


def nhap_khach(cfg: CauHinh, args) -> None:
    """Nhập file CSV khách từ quảng cáo Facebook vào tab 'Khách hàng' (không nhập trùng, không gửi email)."""
    from hoanbao_bot.khach import SoKhach

    from .nhap_khach import doc_csv_quang_cao

    rows = doc_csv_quang_cao(Path(args.file).read_text(encoding="utf-8-sig"))
    _, sheets = _google(cfg)
    them, da_co = SoKhach(sheets, CauHinh.bien("SHEET_DUYET_ID")).nhap_nhieu(rows)
    print(f"Đã thêm {them} khách mới từ quảng cáo, {da_co} khách đã có từ trước.")


def che_do_duyet(cfg: CauHinh, args) -> None:
    """Đặt chế độ duyệt bài: --dat BAT (duyệt tay) hoặc --dat TAT (bài sạch tự lên lịch)."""
    _, sheets = _google(cfg)
    sheet = SheetDuyet(sheets, CauHinh.bien("SHEET_DUYET_ID"))
    sheet.dat_che_do_duyet(args.dat == "BAT")
    print(f"Chế độ duyệt: {'BẬT (duyệt tay)' if sheet.che_do_duyet(True) else 'TẮT (bài sạch tự lên lịch)'}")


def don_bai(cfg: CauHinh, args) -> None:
    """--viec duyet | bo-qua-gio | dinh-dang. Thêm --thu để chỉ xem trước, không ghi."""
    from . import don_bai as db

    drive_, sheets = _google(cfg)
    sheet = SheetDuyet(sheets, CauHinh.bien("SHEET_DUYET_ID"))
    if args.viec == "thu-muc-drive":  # chỉ đọc: các thư mục Drive đã chia sẻ cho tài khoản dịch vụ
        kho_id = CauHinh.bien("DRIVE_KHO_ID", bat_buoc=False)
        print("Email tài khoản dịch vụ của app (chia sẻ thư mục Drive cho email này, quyền Biên tập viên): "
              + cfg.google_service_account().get("client_email", "?"))
        r = drive_.files().list(q="mimeType = 'application/vnd.google-apps.folder' and trashed = false and 'me' in owners or "
                                  "mimeType = 'application/vnd.google-apps.folder' and trashed = false and sharedWithMe",
                                fields="files(id,name,parents,owners(displayName),modifiedTime)", pageSize=200,
                                includeItemsFromAllDrives=True, supportsAllDrives=True).execute()
        ten_cha: dict[str, str] = {}
        for f in sorted(r.get("files", []), key=lambda x: x.get("modifiedTime", ""), reverse=True):
            cha = (f.get("parents") or [""])[0]
            n = len(drive_.files().list(q=f"'{f['id']}' in parents and trashed = false", fields="files(id)", pageSize=200,
                                        includeItemsFromAllDrives=True, supportsAllDrives=True).execute().get("files", []))
            print(f"  {f['name']} | id={f['id']} | {n} mục | sửa {f.get('modifiedTime', '')[:10]}" + (" | <- KHO-MARKETING" if f["id"] == kho_id else "")
                  + (" | nằm trong Kho" if cha == kho_id else ""))
        return
    if args.viec == "xem":  # chỉ đọc: in nội dung các bài đang Chờ duyệt để người duyệt xem trong log
        for b in sheet.doc_tat_ca():
            if b.trang_thai.strip() == CHO_DUYET:
                print(f"===== {b.ma_bai} ({b.ngay} {b.gio}) | {b.ghi_chu}\n{b.noi_dung}\n")
        return
    if args.viec == "doi-chieu-fb":  # chỉ đọc: so bài thật trên Facebook với Sheet
        from .facebook import Fanpage
        page = Fanpage(CauHinh.bien("FB_PAGE_ID"), CauHinh.bien("FB_PAGE_TOKEN"), cfg["facebook"]["graph_version"])
        bay_gio = datetime.now(cfg.mui_gio)
        da_dang = page.bai_da_dang(bay_gio - timedelta(days=9))
        hen = page.bai_hen_gio()
        print(f"Facebook: {len(da_dang)} bài đã đăng (9 ngày qua), {len(hen)} bài đang hẹn giờ.")
        for p_ in sorted(da_dang, key=lambda x: x["created_time"]):
            dong = next((x.strip() for x in (p_.get("message") or "").splitlines() if x.strip()), "(không có chữ)")
            print(f"  ĐÃ ĐĂNG {p_['created_time'][:16]} | {dong[:70]}")
        sheet_ds = [b for b in sheet.doc_tat_ca() if b.facebook_id.strip()]
        ids_fb = {str(p_["id"]) for p_ in da_dang} | {str(p_["id"]) for p_ in hen}
        thieu = [b for b in sheet_ds if b.trang_thai.strip() == DA_LEN_LICH and not any(
            b.facebook_id.strip() in i or i in b.facebook_id.strip() for i in ids_fb)]
        print(f"Sheet ghi 'Đã lên lịch' nhưng không thấy trên Facebook: {len(thieu)}")
        for b in thieu:
            print(f"  ! {b.ma_bai} ({b.ngay} {b.gio}) id={b.facebook_id}")
        return
    if args.viec == "youtube":  # chỉ đọc: liệt kê video đã đẩy lên YouTube và xem đã công khai chưa
        import re

        import requests as _rq
        tim = [(b, m.group(1)) for b in sheet.doc_tat_ca() if (m := re.search(r"youtu\.be/([\w-]{11})", b.ghi_chu or ""))]
        loi = [b for b in sheet.doc_tat_ca() if "YouTube lỗi" in (b.ghi_chu or "")]
        print(f"{len(tim)} bài có video YouTube, {len(loi)} bài YouTube lỗi.")
        for vid in [x for x in re.split(r"[,\s]+", args.ma) if x]:  # kiểm tra thêm mã video đã biết (vd bài bị ghi đè ghi chú)
            r = _rq.get("https://www.youtube.com/oembed", params={"url": f"https://youtu.be/{vid}", "format": "json"}, timeout=30)
            print(f"  (mã nhập tay) https://youtu.be/{vid} | " + ("CÔNG KHAI: " + r.json().get("title", "") if r.status_code == 200 else f"chưa công khai/riêng tư (mã {r.status_code})"))
        for b, vid in tim:
            r = _rq.get("https://www.youtube.com/oembed", params={"url": f"https://youtu.be/{vid}", "format": "json"}, timeout=30)
            tt = "CÔNG KHAI" if r.status_code == 200 else f"chưa công khai/riêng tư (mã {r.status_code})"
            print(f"  {b.ngay} {b.gio} | {b.ma_bai} | https://youtu.be/{vid} | {tt}")
        for b in loi:
            print(f"  LỖI {b.ma_bai}: {(b.ghi_chu or '')[-200:]}")
        return
    if args.viec == "duyet-ma":  # duyệt đúng một bài đã xem kỹ
        b = next((x for x in sheet.doc_tat_ca() if x.ma_bai == args.ma), None)
        if not b or b.trang_thai.strip() != CHO_DUYET:
            raise SystemExit(f"Không có bài '{args.ma}' đang Chờ duyệt.")
        if not args.thu:
            sheet.dat_trang_thai(b.dong, DUYET)
            sheet.dat_ghi_chu(b.dong, "Đã kiểm tra số liệu và duyệt")
        print(f"{'XEM TRƯỚC: ' if args.thu else ''}{b.ma_bai} -> {DUYET}")
        return
    if args.viec == "dinh-dang":
        print(f"Đã tô màu theo trạng thái ({sheet.dinh_dang_mau()} màu) trong tab Bài viết.")
        return
    bay_gio = datetime.now(cfg.mui_gio)
    doi, bo_qua = db.chon_bai(sheet.doc_tat_ca(), args.viec, bay_gio, cfg.mui_gio)
    moi = db.trang_thai_moi(args.viec)
    print(f"{'XEM TRƯỚC: ' if args.thu else ''}{len(doi)} bài sẽ chuyển sang '{moi}', {len(bo_qua)} bài giữ nguyên.")
    for b in doi:
        print(f"  - {b.ma_bai} ({b.ngay} {b.gio}) -> {moi}")
        if not args.thu:
            sheet.dat_trang_thai(b.dong, moi)
            if args.viec == "bo-qua-gio":
                sheet.dat_ghi_chu(b.dong, "Quá giờ đăng, đã bỏ khi dọn bài")
    for b, ly_do in bo_qua:
        print(f"  . {b.ma_bai} ({b.ngay} {b.gio}) giữ nguyên: {ly_do}")


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
        lambda anh, mo_ta: phan_loai.hoi_ai(client, ai["model"], anh, mo_ta),
        nguon_them=cfg.get("nguon_anh_them") or [])
    print("\n".join(bao_cao) or f"Không có file mới trong '{phan_loai.THU_MUC_CHO}'.")


def bang_dieu_khien(cfg: CauHinh, args) -> None:
    """Xuất bang-dieu-khien.html: trang xem lịch bài, trạng thái duyệt và kho ảnh."""
    from . import bang_dieu_khien as bdk
    from .facebook import Fanpage

    drive, sheets = _google(cfg)
    ten_page = ""
    try:
        ten_page = Fanpage(CauHinh.bien("FB_PAGE_ID"), CauHinh.bien("FB_PAGE_TOKEN"),
                           cfg["facebook"]["graph_version"]).kiem_tra()
    except Exception as e:  # không có tên page vẫn xuất được trang
        print(f"(không lấy được tên Fanpage: {e})")
    du_lieu = bdk.thu_thap(cfg, drive, sheets, CauHinh.bien("SHEET_DUYET_ID"), CauHinh.bien("DRIVE_KHO_ID"), ten_page)
    duong_dan = args.ra or "bang-dieu-khien.html"
    with open(duong_dan, "w", encoding="utf-8") as fh:
        fh.write(bdk.dung_html(du_lieu))
    print(f"Đã xuất {duong_dan}: {len(du_lieu['bai'])} bài, {len(du_lieu['kho'])} thư mục kho.")


def dang_ky_webhook(cfg: CauHinh, args) -> None:
    """Nối Facebook với máy chủ chatbot (Giai đoạn 2)."""
    from hoanbao_bot.dang_ky import LoiDangKy, dang_ky

    try:
        for dong in dang_ky(args.url, cfg["facebook"]["app_id"], CauHinh.bien("FB_APP_SECRET"),
                            CauHinh.bien("FB_VERIFY_TOKEN"), CauHinh.bien("FB_PAGE_ID"),
                            CauHinh.bien("FB_PAGE_TOKEN"), cfg["facebook"]["graph_version"]):
            print(dong)
    except LoiDangKy as e:
        print(f"✗ {e}")
        sys.exit(1)


def chan_doan_bot(cfg: CauHinh, args) -> None:
    from hoanbao_bot.chan_doan import chan_doan

    for dong in chan_doan(args.url, cfg["facebook"]["app_id"], CauHinh.bien("FB_APP_SECRET"),
                          CauHinh.bien("FB_VERIFY_TOKEN"), CauHinh.bien("FB_PAGE_ID"),
                          CauHinh.bien("FB_PAGE_TOKEN"), cfg["facebook"]["graph_version"]):
        print(dong)


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
    def kiem_claude():
        CauHinh.khoa_claude()
        # Hỏi thông tin một mô hình: miễn phí, nhưng chứng minh khóa dùng được.
        return "khóa dùng được, mô hình " + anthropic.Anthropic().models.retrieve(cfg["ai"]["model"]).id

    buoc("Claude API", kiem_claude)
    sys.exit(0 if ok else 1)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="hoanbao_mkt", description="Tự động nội dung fanpage Golden Lion")
    sub = p.add_subparsers(dest="lenh", required=True)
    x = sub.add_parser("xem-ke-hoach")
    x.add_argument("--tuan", help="Ngày Thứ 2 của tuần, dạng 2026-10-12 (mặc định: tuần sau)")
    x.add_argument("--ai", action="store_true", help="Gọi AI viết thử (cần ANTHROPIC_API_KEY)")
    t = sub.add_parser("tao-tuan")
    t.add_argument("--tuan")
    t.add_argument("--thang", help="Tạo cả tháng, dạng 2026-11 (bỏ qua bài đã có)")
    sub.add_parser("len-lich")
    sub.add_parser("tao-thu-muc")
    db_ = sub.add_parser("don-bai")
    db_.add_argument("--viec", choices=["duyet", "bo-qua-gio", "dinh-dang", "xem", "duyet-ma", "doi-chieu-fb", "youtube", "thu-muc-drive"], required=True)
    db_.add_argument("--thu", action="store_true")
    db_.add_argument("--ma", default="")
    cd2 = sub.add_parser("che-do-duyet")
    cd2.add_argument("--dat", choices=["BAT", "TAT"], required=True)
    nk = sub.add_parser("nhap-khach")
    nk.add_argument("--file", required=True)
    sub.add_parser("bao-cao-tuan")
    nn = sub.add_parser("nhap-nhom")
    nn.add_argument("--file", required=True)
    sub.add_parser("phan-loai")
    sub.add_parser("gan-anh")
    cd = sub.add_parser("chan-doan")
    cd.add_argument("--url", required=True)
    dk = sub.add_parser("dang-ky-webhook")
    dk.add_argument("--url", required=True, help="Địa chỉ máy chủ bot trên Render, ví dụ https://hoanbao-bot.onrender.com")
    bd = sub.add_parser("bang-dieu-khien")
    bd.add_argument("--ra", help="Đường dẫn file HTML xuất ra (mặc định bang-dieu-khien.html)")
    sub.add_parser("kiem-tra")
    args = p.parse_args(argv)

    cfg = CauHinh.doc()
    lenh = {"xem-ke-hoach": xem_ke_hoach, "tao-tuan": tao_tuan, "len-lich": len_lich,
            "tao-thu-muc": tao_thu_muc, "chan-doan": chan_doan_bot, "dang-ky-webhook": dang_ky_webhook, "bang-dieu-khien": bang_dieu_khien, "phan-loai": phan_loai_kho, "gan-anh": gan_anh, "kiem-tra": kiem_tra,
            "nhap-nhom": nhap_nhom, "bao-cao-tuan": bao_cao_tuan, "nhap-khach": nhap_khach, "che-do-duyet": che_do_duyet, "don-bai": don_bai}
    try:
        lenh[args.lenh](cfg, args)
    except ThieuCauHinh as e:
        print(f"Lỗi cấu hình: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
