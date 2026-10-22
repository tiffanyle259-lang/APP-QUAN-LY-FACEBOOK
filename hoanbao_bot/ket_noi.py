"""Trang "Connect your Facebook Page": đăng nhập Facebook, chọn Fanpage, bật trợ lý (đăng ký webhook cho Page).

Dùng cho video quay màn hình xin quyền Meta: cho thấy toàn bộ quy trình đăng nhập, người dùng cấp quyền
(pages_show_list, pages_manage_metadata, pages_messaging, pages_read_engagement) và trải nghiệm dùng quyền đó.
Không lưu token ở đâu cả: token chỉ đi qua trình duyệt của chính người đăng nhập, trong phiên này.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from html import escape
from urllib.parse import urlencode

import requests
from flask import make_response, request

QUYEN = "pages_show_list,pages_manage_metadata,pages_messaging,pages_read_engagement"
TRUONG_WEBHOOK = "messages,messaging_postbacks,feed"

_CSS = """body{font:16px/1.55 system-ui,Segoe UI,Arial,sans-serif;background:#f4f5f7;color:#16191f;margin:0}
main{max-width:640px;margin:32px auto;padding:0 16px}.card{background:#fff;border:1px solid #e1e4ea;border-radius:14px;padding:22px 24px;margin:14px 0}
h1{font-size:22px;margin:0 0 6px}h2{font-size:17px;margin:0 0 8px}p{margin:8px 0}.muted{color:#5b6472;font-size:14px}
.btn{display:inline-block;background:#1877f2;color:#fff;border:0;border-radius:8px;padding:11px 18px;font:600 16px inherit;text-decoration:none;cursor:pointer}
.btn.green{background:#1a7f4b}.ok{color:#1a7f4b;font-weight:650}.err{color:#b42318;font-weight:650}
li{margin:6px 0}code{background:#eef0f4;padding:1px 5px;border-radius:5px}"""


def _trang(noi_dung: str, tieu_de: str = "Connect your Facebook Page"):
    html = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{escape(tieu_de)}</title><style>{_CSS}</style></head><body><main>{noi_dung}</main></body></html>")
    r = make_response(html)
    r.headers["Cache-Control"] = "no-store"
    return r


def _ky(state: str, bi_mat: str) -> str:
    return hmac.new(bi_mat.encode(), f"ket-noi:{state}".encode(), hashlib.sha256).hexdigest()[:32]


def dang_ky_route(app, app_id: str, app_secret: str, verify_token: str, graph_version: str = "v24.0", http=requests):
    graph = f"https://graph.facebook.com/{graph_version}"

    def redirect_uri() -> str:
        return request.url_root.replace("http://", "https://").rstrip("/") + "/ket-noi/callback"

    def goi(method, path, **tham):
        r = http.request(method, f"{graph}/{path}", params=tham, timeout=30)
        body = r.json() if r.content else {}
        if r.status_code >= 400 or "error" in body:
            raise RuntimeError(body.get("error", {}).get("message", r.text))
        return body

    @app.get("/ket-noi")
    def ket_noi():
        state = secrets.token_urlsafe(16)
        url = "https://www.facebook.com/" + graph_version + "/dialog/oauth?" + urlencode({
            "client_id": app_id, "redirect_uri": redirect_uri(), "state": f"{state}.{_ky(state, verify_token)}",
            "scope": QUYEN, "response_type": "code"})
        return _trang(
            "<div class='card'><h1>Hoan Bao Marketing assistant</h1>"
            "<p class='muted'>Customer-support assistant for Facebook Pages of Hoan Bao Trading Production Import Export Co., Ltd (brand: Golden Lion).</p>"
            "<h2>Step 1 &middot; Connect your Facebook Page</h2>"
            "<p>Log in with Facebook and choose the Page you manage. The assistant will answer customer messages and comments on that Page.</p>"
            "<p>The app asks for these permissions:</p><ul>"
            "<li><code>pages_show_list</code>: show the list of Pages you manage, so you can choose one</li>"
            "<li><code>pages_manage_metadata</code>: subscribe the chosen Page to our webhook (messages and comments)</li>"
            "<li><code>pages_messaging</code>: reply to customers who message the Page</li>"
            "<li><code>pages_read_engagement</code>: read the conversation and the post a customer comments on</li></ul>"
            f"<p><a class='btn' href='{escape(url)}'>Continue with Facebook</a></p>"
            "<p class='muted'>We never post, send unsolicited messages or store your Facebook token. "
            "<a href='/chinh-sach-rieng-tu'>Privacy policy</a> &middot; <a href='/xoa-du-lieu'>Data deletion</a></p></div>")

    def hop_le(state: str) -> bool:
        s, _, k = state.partition(".")
        return bool(s) and hmac.compare_digest(k, _ky(s, verify_token))

    @app.get("/ket-noi/callback")
    def ket_noi_callback():
        if request.args.get("error"):
            return _trang("<div class='card'><h1>Not connected</h1><p>You did not grant the permissions, so nothing was connected. "
                          "<a href='/ket-noi'>Try again</a></p></div>"), 200
        if not hop_le(request.args.get("state", "")) or not request.args.get("code"):
            return _trang("<div class='card'><h1 class='err'>Invalid request</h1><p><a href='/ket-noi'>Start again</a></p></div>"), 400
        try:
            tk = goi("GET", "oauth/access_token", client_id=app_id, client_secret=app_secret,
                     redirect_uri=redirect_uri(), code=request.args["code"])["access_token"]
            ten = goi("GET", "me", fields="name", access_token=tk).get("name", "")
            pages = goi("GET", "me/accounts", fields="id,name,access_token", access_token=tk).get("data", [])
        except Exception as e:  # noqa: BLE001
            return _trang(f"<div class='card'><h1 class='err'>Facebook returned an error</h1><p>{escape(str(e))}</p>"
                          "<p><a href='/ket-noi'>Start again</a></p></div>"), 502
        state = request.args["state"]
        if not pages:
            return _trang(f"<div class='card'><h1>Logged in as {escape(ten)}</h1><p>No Pages found for this account.</p></div>")
        hang = "".join(
            f"<li><form method='post' action='/ket-noi/bat'><b>{escape(p['name'])}</b> "
            f"<input type='hidden' name='state' value='{escape(state)}'><input type='hidden' name='page_id' value='{escape(p['id'])}'>"
            f"<input type='hidden' name='page_name' value='{escape(p['name'])}'><input type='hidden' name='t' value='{escape(p['access_token'])}'> "
            "<button class='btn green' type='submit'>Enable assistant for this Page</button></form></li>" for p in pages)
        return _trang(f"<div class='card'><h1>Step 2 &middot; Choose a Page</h1><p class='muted'>Logged in as <b>{escape(ten)}</b>. "
                      f"Permissions granted. These are the Pages you manage (<code>pages_show_list</code>):</p><ul>{hang}</ul></div>")

    @app.post("/ket-noi/bat")
    def ket_noi_bat():
        f = request.form
        if not hop_le(f.get("state", "")) or not f.get("page_id") or not f.get("t"):
            return _trang("<div class='card'><h1 class='err'>Invalid request</h1><p><a href='/ket-noi'>Start again</a></p></div>"), 400
        try:
            goi("POST", f"{f['page_id']}/subscribed_apps", subscribed_fields=TRUONG_WEBHOOK, access_token=f["t"])
            ds = goi("GET", f"{f['page_id']}/subscribed_apps", access_token=f["t"]).get("data", [])
        except Exception as e:  # noqa: BLE001
            return _trang(f"<div class='card'><h1 class='err'>Could not enable the assistant</h1><p>{escape(str(e))}</p>"
                          "<p><a href='/ket-noi'>Start again</a></p></div>"), 502
        ung_dung = ", ".join(escape(str(a.get("name", a.get("id")))) for a in ds)
        return _trang(
            f"<div class='card'><h1 class='ok'>Assistant enabled for {escape(f.get('page_name', 'your Page'))}</h1>"
            f"<p>The Page is now subscribed to <code>{escape(TRUONG_WEBHOOK)}</code> (<code>pages_manage_metadata</code>). Subscribed app: {ung_dung}.</p>"
            "<h2>Step 3 &middot; Try it</h2><ol><li>Open Messenger and send a message to the Page, for example: "
            "<code>Which adhesive bonds sofa foam without a strong smell?</code></li>"
            "<li>The assistant answers from our product catalog (<code>pages_messaging</code>).</li>"
            "<li>If the customer asks for a price, the assistant asks for a phone number and our staff follows up.</li></ol>"
            "<p class='muted'>The assistant only replies to people who contacted the Page first, inside the 24-hour messaging window.</p></div>")
