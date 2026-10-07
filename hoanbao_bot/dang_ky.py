"""Tự nối Facebook với máy chủ bot bằng Graph API: đăng ký webhook cho ứng dụng và cho Fanpage."""

from __future__ import annotations

import requests

TRUONG_WEBHOOK = "messages,messaging_postbacks,feed"


class LoiDangKy(RuntimeError):
    pass


def chuan_hoa_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url.startswith("https://"):
        raise LoiDangKy("Địa chỉ máy chủ phải bắt đầu bằng https://")
    return url if url.endswith("/webhook") else url + "/webhook"


def _graph(http, method: str, graph: str, path: str, **tham) -> dict:
    r = http.request(method, f"{graph}/{path}", params=tham, timeout=60)
    body = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in body:
        e = body.get("error", {})
        raise LoiDangKy(f"{e.get('message', r.text)} (mã {e.get('code')})")
    return body


def dang_ky(url: str, app_id: str, app_secret: str, verify_token: str, page_id: str, page_token: str,
            graph_version: str = "v24.0", http=requests) -> list[str]:
    """Trả về danh sách dòng báo cáo. Ném LoiDangKy kèm hướng xử lý khi một bước hỏng."""
    graph = f"https://graph.facebook.com/{graph_version}"
    url = chuan_hoa_url(url)
    bao_cao = []

    # 1. Máy chủ phải sống và đúng mật khẩu xác minh (Facebook cũng sẽ kiểm tra như vậy).
    try:
        r = http.get(url, params={"hub.mode": "subscribe", "hub.verify_token": verify_token,
                                  "hub.challenge": "kiem-tra-123"}, timeout=90)
    except requests.RequestException as e:
        raise LoiDangKy(f"Không gọi được máy chủ {url}: {e}. Kiểm tra Render đã ở trạng thái Live chưa "
                        "(gói miễn phí có thể đang ngủ, thử lại sau 1 phút).")
    if r.status_code != 200 or r.text.strip() != "kiem-tra-123":
        raise LoiDangKy(f"Máy chủ trả mã {r.status_code}. Kiểm tra FB_VERIFY_TOKEN trên Render phải giống hệt "
                        "FB_VERIFY_TOKEN trong GitHub, và Render đã deploy bản mới nhất.")
    bao_cao.append("✓ Máy chủ bot hoạt động và mật khẩu xác minh khớp")

    # 2. Đăng ký webhook ở cấp ứng dụng (dùng 'app token' = app_id|app_secret).
    _graph(http, "POST", graph, f"{app_id}/subscriptions", object="page", callback_url=url,
           verify_token=verify_token, fields=TRUONG_WEBHOOK, access_token=f"{app_id}|{app_secret}")
    bao_cao.append(f"✓ Đã đăng ký webhook cho ứng dụng: {url}")

    # 3. Cho Fanpage gửi sự kiện về ứng dụng.
    _graph(http, "POST", graph, f"{page_id}/subscribed_apps", subscribed_fields=TRUONG_WEBHOOK,
           access_token=page_token)
    ket_qua = _graph(http, "GET", graph, f"{page_id}/subscribed_apps", access_token=page_token)
    ung_dung = [a.get("name", a.get("id")) for a in ket_qua.get("data", [])]
    if not ung_dung:
        raise LoiDangKy("Fanpage chưa đăng ký được ứng dụng nào.")
    bao_cao.append("✓ Fanpage đã gửi sự kiện về: " + ", ".join(map(str, ung_dung)))
    return bao_cao
