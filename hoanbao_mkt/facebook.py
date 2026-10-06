"""Lên lịch bài trên Fanpage bằng Graph API chính thức của Meta."""

from __future__ import annotations

import mimetypes
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

# Meta chỉ nhận giờ hẹn cách hiện tại từ 10 phút đến tối đa vài chục ngày.
SOM_NHAT = timedelta(minutes=15)
MUON_NHAT = timedelta(days=29)


class LoiFacebook(RuntimeError):
    pass


class Fanpage:
    def __init__(self, page_id: str, page_token: str, graph_version: str):
        self.page_id = page_id
        self.token = page_token
        self.graph = f"https://graph.facebook.com/{graph_version}"
        self.graph_video = f"https://graph-video.facebook.com/{graph_version}"

    def _post(self, url: str, data: dict, files: dict | None = None) -> dict:
        r = requests.post(url, data={**data, "access_token": self.token}, files=files, timeout=600)
        body = r.json() if r.content else {}
        if r.status_code >= 400 or "error" in body:
            loi = body.get("error", {})
            raise LoiFacebook(f"{loi.get('message', r.text)} (mã {loi.get('code')})")
        return body

    def kiem_tra(self) -> str:
        r = requests.get(f"{self.graph}/{self.page_id}", params={"fields": "name", "access_token": self.token},
                         timeout=30)
        body = r.json()
        if "error" in body:
            raise LoiFacebook(body["error"].get("message"))
        return body["name"]

    def len_lich(self, noi_dung: str, thoi_diem: datetime, file_media: str | None = None,
                 la_video: bool = False, ten_file: str = "media") -> str:
        """Hẹn giờ đăng. Trả về ID bài/ảnh/video trên Facebook."""
        bay_gio = datetime.now(timezone.utc)
        if thoi_diem - bay_gio < SOM_NHAT:
            raise LoiFacebook("Đã quá giờ hẹn (hoặc còn dưới 15 phút) – sửa cột Giờ/Ngày rồi chọn 'Duyệt' lại.")
        if thoi_diem - bay_gio > MUON_NHAT:
            raise LoiFacebook("Giờ hẹn quá xa (Meta chỉ nhận trong khoảng 29 ngày tới).")
        hen = {"published": "false", "scheduled_publish_time": str(int(thoi_diem.timestamp()))}

        if not file_media:
            return self._post(f"{self.graph}/{self.page_id}/feed", {**hen, "message": noi_dung})["id"]

        mime = mimetypes.guess_type(ten_file)[0] or ("video/mp4" if la_video else "image/jpeg")
        with Path(file_media).open("rb") as fh:
            if la_video:
                r = self._post(f"{self.graph_video}/{self.page_id}/videos",
                               {**hen, "description": noi_dung}, files={"source": (ten_file, fh, mime)})
            else:
                r = self._post(f"{self.graph}/{self.page_id}/photos",
                               {**hen, "message": noi_dung}, files={"source": (ten_file, fh, mime)})
        return r.get("post_id") or r["id"]
