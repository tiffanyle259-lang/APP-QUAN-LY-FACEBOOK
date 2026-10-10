"""Đăng video lên kênh YouTube qua YouTube Data API chính thức (hẹn giờ công khai)."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
SOM_NHAT_PHUT = 15


class LoiYouTube(RuntimeError):
    pass


def da_cau_hinh() -> bool:
    return all(os.environ.get(k, "").strip() for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))


def tieu_de_tu_noi_dung(noi_dung: str) -> str:
    """Lấy dòng đầu có chữ làm tiêu đề (YouTube tối đa 100 ký tự, không nhận < >)."""
    for dong in noi_dung.splitlines():
        dong = dong.strip().replace("<", "").replace(">", "")
        if dong and not dong.startswith("#"):
            return dong[:97] + "..." if len(dong) > 100 else dong
    return "Keo dán Golden Lion"


class KenhYouTube:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self._cap = (client_id, client_secret, refresh_token)

    @classmethod
    def tu_moi_truong(cls) -> "KenhYouTube":
        return cls(*(os.environ[k].strip() for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")))

    def _access_token(self) -> str:
        cid, secret, refresh = self._cap
        r = requests.post(TOKEN_URL, data={"client_id": cid, "client_secret": secret,
                                           "refresh_token": refresh, "grant_type": "refresh_token"}, timeout=30)
        if r.status_code != 200:
            raise LoiYouTube(f"Không lấy được quyền YouTube ({r.status_code}): {r.text[:200]}")
        return r.json()["access_token"]

    def dang_video(self, duong_dan: str, tieu_de: str, mo_ta: str, thoi_diem: datetime | None = None,
                   mime: str = "video/mp4") -> str:
        """Tải video lên. Có thoi_diem thì để riêng tư và tự công khai đúng giờ đó. Trả về ID video."""
        status = {"privacyStatus": "private", "selfDeclaredMadeForKids": False}
        if thoi_diem:
            if (thoi_diem - datetime.now(timezone.utc)).total_seconds() < SOM_NHAT_PHUT * 60:
                thoi_diem = None  # quá sát giờ: đăng công khai ngay
                status["privacyStatus"] = "public"
            else:
                status["publishAt"] = thoi_diem.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        else:
            status["privacyStatus"] = "public"
        body = {"snippet": {"title": tieu_de[:100], "description": mo_ta[:4900], "categoryId": "22"},
                "status": status}
        dau = {"Authorization": f"Bearer {self._access_token()}", "X-Upload-Content-Type": mime,
               "X-Upload-Content-Length": str(os.path.getsize(duong_dan))}
        r = requests.post(UPLOAD_URL, params={"uploadType": "resumable", "part": "snippet,status"},
                          json=body, headers=dau, timeout=60)
        if r.status_code != 200 or "Location" not in r.headers:
            raise LoiYouTube(f"YouTube từ chối ({r.status_code}): {r.text[:300]}")
        with open(duong_dan, "rb") as fh:
            up = requests.put(r.headers["Location"], data=fh, headers={"Content-Type": mime}, timeout=1800)
        if up.status_code not in (200, 201):
            raise LoiYouTube(f"Tải video lên YouTube lỗi ({up.status_code}): {up.text[:300]}")
        return up.json()["id"]
