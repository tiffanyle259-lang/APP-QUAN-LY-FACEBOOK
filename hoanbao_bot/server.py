"""Máy chủ webhook (Flask). Meta gọi vào /webhook; xử lý chạy nền để trả 200 thật nhanh."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request

log = logging.getLogger("hoanbao_bot")


def chu_ky_hop_le(raw: bytes, header: str, app_secret: str) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    mong_doi = hmac.new(app_secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mong_doi, header[len("sha256="):])


def tao_ung_dung(bot, app_secret: str, verify_token: str, chay=None, moi_truong=None) -> Flask:
    app = Flask(__name__)
    pool = ThreadPoolExecutor(max_workers=4)
    chay = chay or pool.submit

    @app.get("/")
    @app.get("/healthz")
    def suc_khoe():
        return "ok", 200

    @app.get("/trang-thai")
    def trang_thai():
        """Báo tình trạng bot cho công cụ chẩn đoán. Cần mật khẩu xác minh; không trả về khóa hay nội dung khách."""
        if not hmac.compare_digest(request.args.get("k", ""), verify_token):
            return "forbidden", 403
        return {"bot": getattr(bot, "thong_ke", {}), "moi_truong": moi_truong() if moi_truong else {}}

    @app.get("/webhook")
    def xac_minh():
        if request.args.get("hub.mode") == "subscribe" and hmac.compare_digest(
                request.args.get("hub.verify_token", ""), verify_token):
            return request.args.get("hub.challenge", ""), 200
        return "forbidden", 403

    @app.post("/webhook")
    def nhan():
        raw = request.get_data()
        if not chu_ky_hop_le(raw, request.headers.get("X-Hub-Signature-256", ""), app_secret):
            return "forbidden", 403
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            return "bad request", 400
        chay(bot.xu_ly_su_kien, body)
        return "ok", 200

    return app
