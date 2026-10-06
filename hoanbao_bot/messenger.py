"""Gửi/nhận qua Graph API chính thức của Meta: Messenger và bình luận Fanpage."""

from __future__ import annotations

import requests

GIOI_HAN_TIN = 1900  # Messenger giới hạn 2000 ký tự mỗi tin


class LoiGraph(RuntimeError):
    pass


def cat_tin(text: str, gioi_han: int = GIOI_HAN_TIN) -> list[str]:
    text = text.strip()
    phan = []
    while len(text) > gioi_han:
        cat = max(text.rfind("\n", 0, gioi_han), text.rfind(". ", 0, gioi_han), text.rfind(" ", 0, gioi_han))
        cat = cat if cat > gioi_han // 2 else gioi_han
        phan.append(text[:cat].strip())
        text = text[cat:].strip()
    return phan + ([text] if text else [])


class Messenger:
    def __init__(self, page_id: str, token: str, graph_version: str = "v24.0", session=None):
        self.page_id, self.token = page_id, token
        self.graph = f"https://graph.facebook.com/{graph_version}"
        self.http = session or requests

    def _goi(self, method: str, path: str, **kw) -> dict:
        r = self.http.request(method, f"{self.graph}/{path}", params={"access_token": self.token, **kw.pop("params", {})},
                              timeout=30, **kw)
        body = r.json() if r.content else {}
        if r.status_code >= 400 or "error" in body:
            e = body.get("error", {})
            raise LoiGraph(f"{e.get('message', r.text)} (mã {e.get('code')})")
        return body

    def gui_chu(self, psid: str, text: str) -> None:
        for phan in cat_tin(text):
            self._goi("POST", "me/messages", json={
                "recipient": {"id": psid}, "messaging_type": "RESPONSE",
                "message": {"text": phan, "metadata": "bot"}})

    def hanh_dong(self, psid: str, hanh_dong: str) -> None:
        """mark_seen | typing_on | typing_off. Lỗi ở đây không quan trọng."""
        try:
            self._goi("POST", "me/messages", json={"recipient": {"id": psid}, "sender_action": hanh_dong})
        except LoiGraph:
            pass

    def lich_su(self, psid: str, gioi_han: int = 12) -> list[dict]:
        body = self._goi("GET", f"{self.page_id}/conversations", params={
            "platform": "messenger", "user_id": psid,
            "fields": f"messages.limit({gioi_han}){{message,from,created_time}}"})
        tin = []
        for cuoc in body.get("data", [])[:1]:
            for m in reversed(cuoc.get("messages", {}).get("data", [])):
                if m.get("message"):
                    tin.append({"tu": "page" if m.get("from", {}).get("id") == self.page_id else "khach",
                                "noi_dung": m["message"]})
        return tin

    def nhan_rieng_binh_luan(self, comment_id: str, text: str) -> None:
        """Private reply: nhắn riêng cho người bình luận (một lần, trong 7 ngày)."""
        self._goi("POST", "me/messages", json={
            "recipient": {"comment_id": comment_id}, "message": {"text": text[:GIOI_HAN_TIN], "metadata": "bot"}})

    def tra_loi_binh_luan(self, comment_id: str, text: str) -> None:
        self._goi("POST", f"{comment_id}/comments", json={"message": text})
