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
from .server import tao_ung_dung
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


logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
_bot, _secret, _verify = tao_bot()
app = tao_ung_dung(_bot, _secret, _verify, moi_truong=kiem_moi_truong)
