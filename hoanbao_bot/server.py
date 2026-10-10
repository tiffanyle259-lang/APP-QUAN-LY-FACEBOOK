"""Máy chủ webhook (Flask). Meta gọi vào /webhook; xử lý chạy nền để trả 200 thật nhanh."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor

from pathlib import Path

from flask import Flask, jsonify, make_response, redirect, request, send_file

log = logging.getLogger("hoanbao_bot")


TRANG_DANG_NHAP = """<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Đăng nhập bảng điều khiển</title>
<style>:root{color-scheme:light dark}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f3f4f6;color:#141a24;
font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}@media(prefers-color-scheme:dark){body{background:#0d1117;color:#e8edf4}
form{background:#161b22!important;border-color:#2a323d!important}input{background:#0d1117!important;color:#e8edf4!important;border-color:#2a323d!important}}
form{background:#fff;border:1px solid #e1e4ea;border-radius:16px;padding:24px;width:min(360px,calc(100vw - 32px));display:grid;gap:12px}
h1{font-size:18px;margin:0}input,button{font:inherit;padding:10px 12px;border-radius:10px;border:1px solid #cfd4dc}
button{background:#d99a00;border-color:#d99a00;color:#1a1200;font-weight:700;cursor:pointer}.l{color:#b42318;font-size:14px;min-height:1.2em}</style></head>
<body><form method="get" action="/bang-dieu-khien"><h1>Bảng điều khiển Golden Lion</h1>
<label for="k">Mật khẩu</label><input id="k" name="k" type="password" autocomplete="current-password" autofocus required>
<div class="l">{{LOI}}</div><button type="submit">Vào bảng điều khiển</button></form></body></html>"""


class LoiThaoTac(ValueError):
    """Thao tác từ bảng điều khiển không hợp lệ; thông báo được hiện cho người dùng."""


def chu_ky_hop_le(raw: bytes, header: str, app_secret: str) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    mong_doi = hmac.new(app_secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mong_doi, header[len("sha256="):])


def tao_ung_dung(bot, app_secret: str, verify_token: str, chay=None, moi_truong=None, bang_dieu_khien=None, thao_tac=None, kho_xem=None) -> Flask:
    app = Flask(__name__)
    pool = ThreadPoolExecutor(max_workers=4)
    chay = chay or pool.submit

    @app.get("/")
    @app.get("/healthz")
    def suc_khoe():
        return "ok", 200

    trang_web = Path(__file__).resolve().parent.parent / "trang_web"

    @app.get("/chinh-sach-rieng-tu")
    def chinh_sach():
        return send_file(trang_web / "chinh-sach-rieng-tu.html", mimetype="text/html")

    @app.get("/xoa-du-lieu")
    def xoa_du_lieu():
        return send_file(trang_web / "xoa-du-lieu.html", mimetype="text/html")

    @app.get("/trang-thai")
    def trang_thai():
        """Báo tình trạng bot cho công cụ chẩn đoán. Cần mật khẩu xác minh; không trả về khóa hay nội dung khách."""
        if not hmac.compare_digest(request.args.get("k", ""), verify_token):
            return "forbidden", 403
        return {"bot": getattr(bot, "thong_ke", {}), "moi_truong": moi_truong() if moi_truong else {}}

    cookie = "gl_dang_nhap"

    def the_dang_nhap() -> str:
        return hmac.new(verify_token.encode(), b"bang-dieu-khien", hashlib.sha256).hexdigest()

    def da_dang_nhap() -> bool:
        return hmac.compare_digest(request.cookies.get(cookie, ""), the_dang_nhap())

    @app.get("/bang-dieu-khien")
    def bang_dieu_khien_trang():
        """Bảng điều khiển. Vào lần đầu bằng ?k=mật khẩu; sau đó trình duyệt nhớ 30 ngày, địa chỉ không còn mật khẩu."""
        if hmac.compare_digest(request.args.get("k", ""), verify_token):
            r = make_response(redirect("/bang-dieu-khien"))
            r.set_cookie(cookie, the_dang_nhap(), max_age=30 * 86400, httponly=True, samesite="Strict",
                         secure=request.is_secure)
            return r
        if not da_dang_nhap():
            sai = "k" in request.args  # có nhập mà sai
            return TRANG_DANG_NHAP.replace("{{LOI}}", "Mật khẩu chưa đúng, thử lại." if sai else ""), 403, {
                "Content-Type": "text/html; charset=utf-8"}
        if not bang_dieu_khien:
            return "chưa bật", 404
        try:
            return bang_dieu_khien(), 200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}
        except Exception as e:
            log.exception("Lỗi dựng bảng điều khiển")
            return f"Không dựng được bảng điều khiển: {type(e).__name__}", 500

    @app.get("/api/anh/<file_id>")
    def api_anh(file_id):
        if not da_dang_nhap() or not kho_xem:
            return "forbidden", 403
        try:
            noi_dung = kho_xem.anh_nho(file_id)
        except ValueError as e:
            return str(e), 404
        except Exception:
            log.exception("Lỗi lấy ảnh xem trước")
            return "lỗi", 502
        return noi_dung, 200, {"Content-Type": "image/jpeg" if noi_dung[:3] == b"\xff\xd8\xff" else "image/png",
                                "Cache-Control": "private, max-age=3600"}

    @app.get("/api/kho/<path:ten>")
    def api_kho(ten):
        if not da_dang_nhap() or not kho_xem:
            return jsonify(loi="forbidden"), 403
        try:
            return jsonify(kho_xem.danh_sach(ten))
        except Exception:
            log.exception("Lỗi liệt kê thư mục kho")
            return jsonify(loi="Không đọc được thư mục kho"), 502

    @app.post("/api/thao-tac")
    def api_thao_tac():
        """Duyệt/bỏ/sửa bài và đổi trạng thái khách ngay trên bảng điều khiển."""
        if not da_dang_nhap() or request.headers.get("X-GL") != "1":
            return jsonify(loi="Hết phiên đăng nhập, hãy mở lại bảng điều khiển bằng link có mật khẩu."), 403
        if not thao_tac:
            return jsonify(loi="Chưa bật"), 404
        lenh = request.get_json(silent=True)
        if not isinstance(lenh, dict):
            return jsonify(loi="Dữ liệu không hợp lệ"), 400
        try:
            return jsonify(thao_tac(lenh))
        except LoiThaoTac as e:
            return jsonify(loi=str(e)), 400
        except Exception as e:
            log.exception("Lỗi thao tác bảng điều khiển")
            return jsonify(loi=f"Lỗi máy chủ ({type(e).__name__})"), 500

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
