"""Điểm khởi động cho máy chủ: gunicorn hoanbao_bot.wsgi:app"""

from __future__ import annotations

import logging
import os
import threading

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
    ket_qua["bang_dieu_khien"] = {"da_co_ban": bool(_bdk["html"]), "dang_dung": _bdk["dang_dung"],
                                  "loi": _bdk["loi"] or "không", "dang_dem_kho": _cache_cham["dang_dem"]}
    ket_qua["ghi_so_khach"] = "có" if _bot.so_khach else "KHÔNG (không nối được Google Sheet)"
    return ket_qua




_ht_cache: dict = {"claude_luc": 0.0, "claude": None}
_claude_client = None
_google_doc: dict = {}


def http_co_timeout(creds, giay: int = 30):
    """Kết nối Google có giới hạn thời gian, để một lệnh gọi treo không làm kẹt cả bảng điều khiển."""
    import google_auth_httplib2
    import httplib2

    return google_auth_httplib2.AuthorizedHttp(creds, http=httplib2.Http(timeout=giay))


def google_chi_doc(cfg, viec: str = "chinh"):
    """Client Google chỉ-đọc, tạo một lần cho mỗi "việc" rồi dùng lại (httplib2 không an toàn nếu hai luồng dùng chung)."""
    if viec not in _google_doc:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_service_account_info(
            cfg.google_service_account(),
            scopes=["https://www.googleapis.com/auth/drive.readonly",
                    "https://www.googleapis.com/auth/spreadsheets.readonly"])
        _google_doc[viec] = (build("drive", "v3", http=http_co_timeout(creds), cache_discovery=False),
                             build("sheets", "v4", http=http_co_timeout(creds), cache_discovery=False))
    return _google_doc[viec]


def kiem_claude(cfg) -> tuple[bool, str]:
    """Kiểm tra khóa Claude, nhớ kết quả 10 phút để khỏi gọi lại mỗi lần mở trang."""
    import time

    global _claude_client
    if _ht_cache["claude"] is not None and time.time() - _ht_cache["claude_luc"] < 600:
        return _ht_cache["claude"]
    try:
        CauHinh.khoa_claude()
        if _claude_client is None:
            _claude_client = anthropic.Anthropic(timeout=20.0, max_retries=1)
        _claude_client.models.retrieve(cfg["bot"]["model"])
        kq = (True, "Khóa dùng được, mô hình " + cfg["bot"]["model"])
    except Exception as e:
        kq = (False, f"Không dùng được ({type(e).__name__})")
    _ht_cache.update(claude=kq, claude_luc=time.time())
    return kq


def kiem_he_thong(cfg, drive, sheets, ten_page: str) -> list[dict]:
    """Tình trạng từng bộ phận để chủ shop nhìn là biết cái nào hỏng. Không bao giờ hiện khóa hay token."""
    kq = []

    def them(ten, ok, chi_tiet, huong_dan="", nut=""):
        kq.append({"ten": ten, "ok": ok, "chi_tiet": chi_tiet, "huong_dan": huong_dan, "nut": nut})

    them("Máy chủ bot (Render)", True, "Đang chạy, khởi động lúc " + _bot.thong_ke.get("khoi_dong", "?"))
    them("Fanpage (Meta)", bool(ten_page), f"Token dùng được, Page: {ten_page}" if ten_page else "Không đọc được Page bằng token hiện tại",
         "" if ten_page else "Lấy lại token Fanpage và cập nhật FB_PAGE_TOKEN trên Render và GitHub.")
    lan_cuoi = _bot.thong_ke.get("lan_cuoi") or "chưa có"
    them("Nhận tin khách từ Meta", True, f"Lần nhận gần nhất: {lan_cuoi}" if lan_cuoi != "chưa có"
         else "Chưa nhận tin nào từ lần khởi động này (bình thường nếu chưa có khách nhắn)")
    try:
        sheets.spreadsheets().get(spreadsheetId=CauHinh.bien("SHEET_DUYET_ID"), fields="spreadsheetId").execute()
        them("Google Sheet", True, "Đọc được")
    except Exception as e:
        them("Google Sheet", False, f"Không đọc được ({type(e).__name__})", "Kiểm tra Sheet còn chia sẻ cho tài khoản dịch vụ.")
    kho_id = os.environ.get("DRIVE_KHO_ID", "").strip()
    if not kho_id:
        them("Kho ảnh (Google Drive)", False, "Chưa cấu hình DRIVE_KHO_ID trên Render",
             "Render > hoanbao-bot > Environment > thêm DRIVE_KHO_ID.")
    else:
        try:
            drive.files().get(fileId=kho_id, fields="id", supportsAllDrives=True).execute()
            them("Kho ảnh (Google Drive)", True, "Đọc được Kho-Marketing")
        except Exception as e:
            them("Kho ảnh (Google Drive)", False, f"Không đọc được ({type(e).__name__})", "Kiểm tra thư mục còn chia sẻ cho tài khoản dịch vụ.")
    ok_claude, chi_tiet_claude = kiem_claude(cfg)
    them("Claude (AI)", ok_claude, chi_tiet_claude, "" if ok_claude else
         "Kiểm tra số dư và khóa tại console.anthropic.com, rồi cập nhật ANTHROPIC_API_KEY.")
    from .khach import email_da_cau_hinh

    if email_da_cau_hinh():
        them("Báo khách mới qua email", True, "Đã cấu hình, có khách để lại số điện thoại thì gửi email ngay", nut="email_thu")
    else:
        them("Báo khách mới qua email", False, "Chưa cấu hình, nhân viên chưa được báo khi có khách mới",
             "Render > Environment > thêm EMAIL_WEBHOOK_URL và EMAIL_WEBHOOK_SECRET (xem hướng dẫn Google Apps Script).")
    if _bot.thong_ke.get("loi"):
        them("Lỗi gần đây của bot", False, f"{_bot.thong_ke['loi']} lỗi: {_bot.thong_ke.get('loi_cuoi', '')[:160]}")
    return kq


_khoa_dung = threading.Lock()
_bdk = {"html": "", "luc": 0.0, "dang_dung": False, "loi": ""}
_cache_cham = {"dem_kho": (0.0, None), "ten_page": "", "hoi_thoai": (0.0, None, ""), "dang_dem": False}
TUOI_BANG_DIEU_KHIEN = 90      # giây: quá hạn này thì làm mới ngầm, người dùng vẫn thấy ngay bản gần nhất
TUOI_DEM_KHO = 30 * 60         # đếm file kho rất tốn lần gọi Drive nên nhớ 30 phút
TUOI_HOI_THOAI = 90

TRANG_DANG_TAI = """<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta http-equiv="refresh" content="3">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Đang chuẩn bị</title>
<style>body{font:16px system-ui,sans-serif;display:grid;place-items:center;min-height:100vh;margin:0;background:#f3f4f6;color:#141a24}
@media(prefers-color-scheme:dark){body{background:#0d1117;color:#e8edf4}}</style></head>
<body><p>Đang chuẩn bị dữ liệu bảng điều khiển, vài giây nữa là xong…</p></body></html>"""


def _dung_bang_dieu_khien() -> str:
    """Dựng lại toàn bộ bảng điều khiển từ dữ liệu thật. Các phần nặng (đếm kho, tin nhắn) được nhớ lại."""
    import time

    from hoanbao_mkt import bang_dieu_khien as bdk
    from hoanbao_mkt.facebook import Fanpage

    cfg = CauHinh.doc()
    drive, sheets = google_chi_doc(cfg)
    if not _cache_cham["ten_page"]:  # tên Fanpage không đổi, hỏi một lần
        try:
            _cache_cham["ten_page"] = Fanpage(CauHinh.bien("FB_PAGE_ID"), CauHinh.bien("FB_PAGE_TOKEN"),
                                              cfg["facebook"]["graph_version"]).kiem_tra()
        except Exception:
            logging.getLogger("hoanbao_bot").warning("Không lấy được tên Fanpage cho bảng điều khiển")
    ten_page = _cache_cham["ten_page"]
    kho_id = os.environ.get("DRIVE_KHO_ID", "").strip()
    luc_kho, dem = _cache_cham["dem_kho"]
    if kho_id and (dem is None or time.time() - luc_kho > TUOI_DEM_KHO):
        _dem_kho_ngam(cfg, kho_id)  # đếm chạy riêng, không bắt người dùng chờ
    d = bdk.thu_thap(cfg, drive, sheets, CauHinh.bien("SHEET_DUYET_ID"), kho_id, ten_page, dem_kho_san=dem or [])
    d["kho_dang_dem"] = bool(kho_id and dem is None)
    d["he_thong"] = kiem_he_thong(cfg, drive, sheets, ten_page)
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
    luc_hoi, hoi, loi_hoi = _cache_cham["hoi_thoai"]
    if hoi is None or time.time() - luc_hoi > TUOI_HOI_THOAI:
        try:
            hoi, loi_hoi = _bot.mess.hoi_thoai_gan_day(), ""
        except Exception as e:
            hoi, loi_hoi = None, str(e)[:200]
        _cache_cham["hoi_thoai"] = (time.time(), hoi, loi_hoi)
    d["hoi_thoai"] = hoi
    if hoi is None:
        d["hoi_thoai_loi"] = loi_hoi
    return bdk.dung_html(d)


def _dem_kho_ngam(cfg, kho_id: str) -> None:
    """Đếm file kho ở luồng riêng (dùng client Drive riêng), xong thì dựng lại bảng để hiện số liệu."""
    import time

    if _cache_cham["dang_dem"]:
        return
    _cache_cham["dang_dem"] = True

    def lam():
        from hoanbao_mkt import bang_dieu_khien as bdk

        try:
            drive, _ = google_chi_doc(cfg, "dem-kho")
            _cache_cham["dem_kho"] = (time.time(), bdk.dem_kho(cfg, drive, kho_id))
        except Exception:
            logging.getLogger("hoanbao_bot").exception("Không đếm được kho ảnh")
            if _cache_cham["dem_kho"][1] is None:
                _cache_cham["dem_kho"] = (time.time(), [])  # đừng thử lại liên tục khi lỗi
        finally:
            _cache_cham["dang_dem"] = False
        _lam_moi_ngam()

    threading.Thread(target=lam, daemon=True).start()


def lam_moi_bang_dieu_khien() -> None:
    """Dựng lại và lưu bản mới. Chỉ một luồng làm cùng lúc (client Google dùng chung, tiết kiệm bộ nhớ)."""
    import time

    with _khoa_dung:
        _bdk["dang_dung"] = True
        try:
            bat_dau = time.time()
            _bdk.update(html=_dung_bang_dieu_khien(), luc=time.time(), loi="")
            logging.getLogger("hoanbao_bot").info("Dựng bảng điều khiển mất %.1f giây", time.time() - bat_dau)
        except Exception as e:
            _bdk["loi"] = f"{type(e).__name__}: {str(e)[:160]}"
            logging.getLogger("hoanbao_bot").exception("Lỗi dựng bảng điều khiển")
        finally:
            _bdk["dang_dung"] = False


def _lam_moi_ngam() -> None:
    if not _bdk["dang_dung"]:
        threading.Thread(target=lam_moi_bang_dieu_khien, daemon=True).start()


def dung_bang_dieu_khien() -> str:
    """Trả về ngay bản gần nhất. Nếu đã cũ thì làm mới ngầm cho lần mở sau, nên mở trang luôn nhanh."""
    import time

    if _bdk["html"]:
        if time.time() - _bdk["luc"] > TUOI_BANG_DIEU_KHIEN:
            _lam_moi_ngam()
        return _bdk["html"]
    _lam_moi_ngam()
    for _ in range(50):  # lần đầu sau khi máy chủ khởi động: chờ tối đa khoảng 25 giây
        time.sleep(0.5)
        if _bdk["html"]:
            return _bdk["html"]
    if _bdk["loi"]:
        return TRANG_DANG_TAI.replace("vài giây nữa là xong…", "gặp lỗi, đang thử lại (" + _bdk["loi"].replace("<", "") + ")")
    return TRANG_DANG_TAI


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

    _kho_xem = KhoXem(build("drive", "v3", http=http_co_timeout(creds), cache_discovery=False), kho_id, token)
    return _kho_xem


class _KhoXemLazy:
    """Tạo bộ xem kho khi cần, để máy chủ vẫn chạy nếu chưa có DRIVE_KHO_ID."""

    def anh_nho(self, file_id, canh=640):
        k = lay_kho_xem()
        if not k:
            raise ValueError("Chưa cấu hình DRIVE_KHO_ID trên máy chủ.")
        return k.anh_nho(file_id, canh)

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

    if lenh.get("hanh") == "email_thu":
        from .khach import email_da_cau_hinh, gui_email_chi_tiet

        if not email_da_cau_hinh():
            raise LoiThaoTac("Chưa cấu hình email trên Render (EMAIL_WEBHOOK_URL, EMAIL_WEBHOOK_SECRET).")
        ok, ly_do = gui_email_chi_tiet("Thư thử từ bảng điều khiển Golden Lion\nNếu chị/anh đọc được thư này, báo khách mới qua email đã hoạt động.")
        if not ok:
            raise LoiThaoTac(ly_do)
        return {"ok": True, "thong_bao": "Đã gửi thư thử, chị/anh kiểm tra hộp thư (cả mục Thư rác)."}

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
    if hanh == "khach_trang_thai":
        _cache_cham["hoi_thoai"] = (0.0, None, "")
    lam_moi_bang_dieu_khien()  # dựng lại ngay để lần tải lại sau thao tác thấy đúng dữ liệu mới
    return {"ok": True}


logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
_bot, _secret, _verify = tao_bot()
app = tao_ung_dung(_bot, _secret, _verify, moi_truong=kiem_moi_truong, bang_dieu_khien=dung_bang_dieu_khien, thao_tac=thao_tac,
                   kho_xem=_KhoXemLazy())
_lam_moi_ngam()  # dựng sẵn bảng điều khiển ngay khi máy chủ khởi động
