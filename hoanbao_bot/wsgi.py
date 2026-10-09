"""Điểm khởi động cho máy chủ: gunicorn hoanbao_bot.wsgi:app"""

from __future__ import annotations

import logging
import os

import anthropic

from hoanbao_mkt.cau_hinh import CauHinh
from hoanbao_mkt.du_lieu import doc_du_lieu

from .ai_bot import AiBot
from .khach import SoKhach, bao_nhan_vien
from .kien_thuc import dung_he_thong
from .messenger import Messenger
from .server import LoiThaoTac, tao_ung_dung
from .xu_ly import Bot


def tao_bot() -> tuple[Bot, str, str]:
    cfg = CauHinh.doc()
    bot_cfg = cfg.get("bot", {})
    du_lieu = doc_du_lieu(cfg.file_du_lieu, cfg.get("cot_bo_qua"))
    page_id = CauHinh.bien("FB_PAGE_ID")
    mess = Messenger(page_id, CauHinh.bien("FB_PAGE_TOKEN"), cfg["facebook"]["graph_version"])
    ai = AiBot(dung_he_thong(du_lieu), bot_cfg.get("model", "claude-sonnet-5-5"), bot_cfg.get("effort", "low"),
               anthropic.Anthropic())
    so_khach = None
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        creds = Credentials.from_service_account_info(
            cfg.google_service_account(), scopes=["https://www.googleapis.com/auth/spreadsheets"])
        so_khach = SoKhach(build("sheets", "v4", credentials=creds, cache_discovery=False),
                           CauHinh.bien("SHEET_DUYET_ID"))
    except Exception:
        logging.getLogger("hoanbao_bot").exception("Không nối được Google Sheet; bot vẫn chạy nhưng không ghi khách")
    return (Bot(page_id, mess, ai, so_khach, bao_nhan_vien, cfg.get("mui_gio", "Asia/Ho_Chi_Minh")),
            CauHinh.bien("FB_APP_SECRET"), CauHinh.bien("FB_VERIFY_TOKEN"))


def kiem_moi_truong() -> dict:
    """Tình trạng cấu hình (đúng/sai), tuyệt đối không lộ giá trị."""
    from hoanbao_mkt.cau_hinh import ThieuCauHinh
    ket_qua = {}
    try:
        CauHinh.khoa_claude()
        ket_qua["khoa_claude"] = "đúng dạng"
    except ThieuCauHinh as e:
        ket_qua["khoa_claude"] = "SAI: " + str(e)[:80]
    for ten in ("FB_PAGE_ID", "FB_PAGE_TOKEN", "FB_APP_SECRET", "SHEET_DUYET_ID", "GOOGLE_SERVICE_ACCOUNT_JSON"):
        ket_qua[ten] = "có" if os.environ.get(ten, "").strip() else "THIẾU"
    ket_qua["ghi_so_khach"] = "có" if _bot.so_khach else "KHÔNG (không nối được Google Sheet)"
    return ket_qua


_cache_bdk: dict = {"luc": 0.0, "html": ""}


def dung_bang_dieu_khien() -> str:
    """Dựng bảng điều khiển từ dữ liệu thật (Sheet, Drive, Fanpage). Lưu tạm 60 giây để đỡ gọi API."""
    import time

    if time.time() - _cache_bdk["luc"] < 60 and _cache_bdk["html"]:
        return _cache_bdk["html"]
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    from hoanbao_mkt import bang_dieu_khien as bdk
    from hoanbao_mkt.facebook import Fanpage

    cfg = CauHinh.doc()
    creds = Credentials.from_service_account_info(
        cfg.google_service_account(),
        scopes=["https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/spreadsheets.readonly"])
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
    ten_page = ""
    try:
        ten_page = Fanpage(CauHinh.bien("FB_PAGE_ID"), CauHinh.bien("FB_PAGE_TOKEN"),
                           cfg["facebook"]["graph_version"]).kiem_tra()
    except Exception:
        logging.getLogger("hoanbao_bot").warning("Không lấy được tên Fanpage cho bảng điều khiển")
    d = bdk.thu_thap(cfg, drive, sheets, CauHinh.bien("SHEET_DUYET_ID"),
                     os.environ.get("DRIVE_KHO_ID", "").strip(), ten_page)
    d["bot"] = dict(_bot.thong_ke)
    d["sua_duoc"] = True
    try:
        dong = sheets.spreadsheets().values().get(
            spreadsheetId=CauHinh.bien("SHEET_DUYET_ID"), range="'Khách hàng'!A2:I500").execute().get("values", [])
        # Thêm số dòng trong Sheet (phần tử cuối) để bảng điều khiển đổi được trạng thái đúng khách.
        d["khach"] = [(list(r) + [""] * 9)[:9] + [i] for i, r in enumerate(dong, start=2)][::-1][:30]
    except Exception as e:
        d["khach"] = None
        d["khach_loi"] = type(e).__name__
    try:
        d["hoi_thoai"] = _bot.mess.hoi_thoai_gan_day()
    except Exception as e:
        d["hoi_thoai"] = None
        d["hoi_thoai_loi"] = str(e)[:200]
    _cache_bdk.update(luc=time.time(), html=bdk.dung_html(d))
    return _cache_bdk["html"]


_kho_xem = None


def lay_kho_xem():
    """Bộ xem trước ảnh/video trong Kho-Marketing (cần DRIVE_KHO_ID trên máy chủ)."""
    global _kho_xem
    if _kho_xem is not None:
        return _kho_xem
    kho_id = os.environ.get("DRIVE_KHO_ID", "").strip()
    if not kho_id:
        return None
    from google.auth.transport.requests import Request
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    from .kho_xem import KhoXem

    creds = Credentials.from_service_account_info(
        CauHinh.google_service_account(), scopes=["https://www.googleapis.com/auth/drive.readonly"])

    def token() -> str:
        if not creds.valid:
            creds.refresh(Request())
        return creds.token

    _kho_xem = KhoXem(build("drive", "v3", credentials=creds, cache_discovery=False), kho_id, token)
    return _kho_xem


class _KhoXemLazy:
    """Tạo bộ xem kho khi cần, để máy chủ vẫn chạy nếu chưa có DRIVE_KHO_ID."""

    def anh_nho(self, file_id):
        k = lay_kho_xem()
        if not k:
            raise ValueError("Chưa cấu hình DRIVE_KHO_ID trên máy chủ.")
        return k.anh_nho(file_id)

    def danh_sach(self, ten):
        k = lay_kho_xem()
        if not k:
            raise ValueError("Chưa cấu hình DRIVE_KHO_ID trên máy chủ.")
        return k.danh_sach(ten)


def thao_tac(lenh: dict) -> dict:
    """Ghi thay đổi từ bảng điều khiển vào Google Sheet. Chỉ nhận vài thao tác cố định, kiểm tra kỹ trước khi ghi."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    from hoanbao_mkt.duyet_bai import BO, CHO_DUYET, DA_LEN_LICH, DUYET, SheetDuyet
    from .khach import TAB, TRANG_THAI_KHACH

    cfg = CauHinh.doc()
    creds = Credentials.from_service_account_info(
        cfg.google_service_account(), scopes=["https://www.googleapis.com/auth/spreadsheets"])
    sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
    sheet_id = CauHinh.bien("SHEET_DUYET_ID")
    sheet = SheetDuyet(sheets, sheet_id)
    hanh = lenh.get("hanh")
    if hanh in ("bai_trang_thai", "bai_noi_dung", "bai_media"):
        bai = next((b for b in sheet.doc_tat_ca() if b.ma_bai == str(lenh.get("ma_bai", ""))), None)
        if not bai:
            raise LoiThaoTac("Không tìm thấy bài này trong Sheet.")
        if bai.trang_thai == DA_LEN_LICH or bai.facebook_id.strip():
            raise LoiThaoTac("Bài đã lên lịch trên Facebook. Muốn sửa hoặc hủy, làm trong Meta Business Suite.")
        if hanh == "bai_media":
            file_id = str(lenh.get("file_id") or "").strip()
            if not file_id:  # bỏ ảnh/video: bài chỉ đăng chữ
                sheet.gan_media(bai.dong, "", "Đăng chỉ chữ (đã bỏ ảnh/video)")
            else:
                k = lay_kho_xem()
                if not k:
                    raise LoiThaoTac("Chưa cấu hình DRIVE_KHO_ID trên máy chủ.")
                try:
                    f = k.thong_tin(file_id)
                except ValueError as e:
                    raise LoiThaoTac(str(e))
                sheet.gan_media(bai.dong, f"https://drive.google.com/file/d/{file_id}/view", f"File: {f['name']}")
        elif hanh == "bai_trang_thai":
            tt = lenh.get("trang_thai")
            if tt not in (CHO_DUYET, DUYET, BO):
                raise LoiThaoTac("Trạng thái không hợp lệ.")
            sheet.dat_trang_thai(bai.dong, tt)
        else:
            nd = str(lenh.get("noi_dung", "")).strip()
            if not nd or len(nd) > 5000:
                raise LoiThaoTac("Nội dung bài phải có chữ và không quá 5000 ký tự.")
            sheet.dat_noi_dung(bai.dong, nd)
    elif hanh == "khach_trang_thai":
        try:
            dong = int(lenh.get("dong"))
        except (TypeError, ValueError):
            raise LoiThaoTac("Dòng khách không hợp lệ.")
        if dong < 2 or dong > 5000 or lenh.get("trang_thai") not in TRANG_THAI_KHACH:
            raise LoiThaoTac("Trạng thái khách không hợp lệ.")
        co = sheets.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"'{TAB}'!A{dong}").execute().get("values")
        if not co:
            raise LoiThaoTac("Dòng khách này không còn trong Sheet.")
        sheets.spreadsheets().values().update(
            spreadsheetId=sheet_id, range=f"'{TAB}'!H{dong}", valueInputOption="RAW",
            body={"values": [[lenh["trang_thai"]]]}).execute()
    else:
        raise LoiThaoTac("Thao tác không hỗ trợ.")
    _cache_bdk["luc"] = 0.0  # lần mở sau đọc dữ liệu mới
    return {"ok": True}


logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
_bot, _secret, _verify = tao_bot()
app = tao_ung_dung(_bot, _secret, _verify, moi_truong=kiem_moi_truong, bang_dieu_khien=dung_bang_dieu_khien, thao_tac=thao_tac,
                   kho_xem=_KhoXemLazy())
