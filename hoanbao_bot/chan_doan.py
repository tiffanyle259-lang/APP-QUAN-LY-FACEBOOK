"""Chẩn đoán từ xa: bot có nhận được tin không, Facebook có gửi về không, lỗi ở đâu."""

from __future__ import annotations

import requests


def chan_doan(url: str, app_id: str, app_secret: str, verify_token: str, page_id: str, page_token: str,
              graph_version: str = "v24.0", http=requests) -> list[str]:
    graph = f"https://graph.facebook.com/{graph_version}"
    ra: list[str] = []
    base = url.strip().rstrip("/").removesuffix("/webhook")

    def g(path, **tham):
        r = http.get(f"{graph}/{path}", params=tham, timeout=60)
        body = r.json() if r.content else {}
        if "error" in body:
            raise RuntimeError(body["error"].get("message", "lỗi Graph"))
        return body

    # 1. Máy chủ bot tự báo
    try:
        r = http.get(f"{base}/trang-thai", params={"k": verify_token}, timeout=90)
        if r.status_code == 404:
            ra.append("✗ Máy chủ chưa có bản mới (chưa có /trang-thai). Đợi Render deploy xong rồi chạy lại.")
        elif r.status_code != 200:
            ra.append(f"✗ /trang-thai trả mã {r.status_code} (kiểm tra FB_VERIFY_TOKEN)")
        else:
            d = r.json()
            b, m = d.get("bot", {}), d.get("moi_truong", {})
            ra.append(f"• Facebook đã gọi webhook {b.get('goi_webhook', 0)} lần, lần cuối: {b.get('lan_cuoi') or 'chưa lần nào'}")
            ra.append(f"• Tin khách nhận: {b.get('tin_nhan_khach', 0)} | bình luận: {b.get('binh_luan', 0)} | "
                      f"đã gửi trả lời: {b.get('da_gui_tra_loi', 0)} | bỏ qua vì im lặng: {b.get('bo_qua_im_lang', 0)}")
            ra.append(f"• Lỗi: {b.get('loi', 0)}" + (f" – lỗi cuối: {b['loi_cuoi']}" if b.get("loi_cuoi") else ""))
            ra.append("• Cấu hình trên Render: " + ", ".join(f"{k}={v}" for k, v in m.items()))
    except requests.RequestException as e:
        ra.append(f"✗ Không gọi được máy chủ: {e}")

    # 2. Facebook đã đăng ký đúng chưa
    try:
        ds = g(f"{app_id}/subscriptions", access_token=f"{app_id}|{app_secret}").get("data", [])
        pg = [x for x in ds if x.get("object") == "page"]
        ra.append("• Webhook của ứng dụng: " + (", ".join(f"{x.get('callback_url')} [{x.get('fields') and ','.join(f['name'] for f in x['fields'])}]" for x in pg) if pg else "CHƯA đăng ký"))
    except Exception as e:
        ra.append(f"✗ Không đọc được đăng ký webhook: {e}")
    try:
        ds = g(f"{page_id}/subscribed_apps", access_token=page_token).get("data", [])
        ra.append("• Fanpage đang gửi sự kiện về: " + (", ".join(f"{a.get('name')} [{','.join(a.get('subscribed_fields', []))}]" for a in ds) or "CHƯA có ứng dụng nào"))
    except Exception as e:
        ra.append(f"✗ Không đọc được đăng ký Fanpage: {e}")

    # 3. Quyền của token
    try:
        d = g("debug_token", input_token=page_token, access_token=f"{app_id}|{app_secret}").get("data", {})
        thieu = {"pages_messaging", "pages_manage_metadata", "pages_read_engagement"} - set(d.get("scopes", []))
        ra.append("• Token Fanpage: " + ("không hết hạn" if d.get("expires_at") == 0 else "CÓ HẠN") +
                  (f"; THIẾU quyền {', '.join(sorted(thieu))}" if thieu else "; đủ quyền nhắn tin"))
    except Exception as e:
        ra.append(f"✗ Không kiểm tra được token: {e}")

    # 4. Hộp thư thực tế: tin khách có tới Fanpage không, Fanpage có trả lời không
    try:
        cs = g(f"{page_id}/conversations", platform="messenger", limit="3",
               fields="updated_time,messages.limit(2){from,created_time}", access_token=page_token).get("data", [])
        if not cs:
            ra.append("• Hộp thư Fanpage chưa có cuộc trò chuyện nào (tin nhắn thử chưa tới Fanpage này?)")
        for c in cs:
            ms = c.get("messages", {}).get("data", [])
            ai_nhan = ["Fanpage" if m.get("from", {}).get("id") == page_id else "khách" for m in ms]
            ra.append(f"• Cuộc trò chuyện cập nhật {c.get('updated_time')}: tin mới nhất từ {ai_nhan[0] if ai_nhan else '?'}")
    except Exception as e:
        ra.append(f"• Không đọc được hộp thư: {e}")
    return ra
