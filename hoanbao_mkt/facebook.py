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

    def so_nguoi_theo_doi(self) -> int:
        r = requests.get(f"{self.graph}/{self.page_id}", params={"fields": "followers_count,fan_count",
                                                                  "access_token": self.token}, timeout=30)
        body = r.json()
        if "error" in body:
            raise LoiFacebook(body["error"].get("message"))
        return int(body.get("followers_count") or body.get("fan_count") or 0)

    def bai_da_dang(self, tu_luc: datetime) -> list[dict]:
        """Các bài đã đăng từ thời điểm tu_luc, kèm số cảm xúc, bình luận, chia sẻ."""
        r = requests.get(
            f"{self.graph}/{self.page_id}/published_posts",
            params={"since": int(tu_luc.timestamp()), "limit": 50, "access_token": self.token,
                    "fields": "id,created_time,message,permalink_url,shares,"
                              "reactions.summary(total_count).limit(0),comments.summary(total_count).limit(0)"},
            timeout=60)
        body = r.json()
        if "error" in body:
            raise LoiFacebook(body["error"].get("message"))
        return body.get("data", [])

    def bai_hen_gio(self) -> list[dict]:
        """Các bài đang hẹn giờ, chưa đăng."""
        r = requests.get(f"{self.graph}/{self.page_id}/scheduled_posts",
                         params={"limit": 100, "fields": "id,scheduled_publish_time,message",
                                 "access_token": self.token}, timeout=60)
        body = r.json()
        if "error" in body:
            raise LoiFacebook(body["error"].get("message"))
        return body.get("data", [])

    def xoa(self, doi_tuong_id: str) -> None:
        """Xóa bài/ảnh/video (dùng để hủy bài đã hẹn giờ). Đã không còn thì coi như xong."""
        r = requests.delete(f"{self.graph}/{doi_tuong_id}", params={"access_token": self.token}, timeout=60)
        body = r.json() if r.content else {}
        if r.status_code >= 400 or "error" in body:
            loi = body.get("error", {})
            if loi.get("code") in (100, 803) and "exist" in str(loi.get("message", "")).lower():
                return
            raise LoiFacebook(f"{loi.get('message', r.text)} (mã {loi.get('code')})")

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
        self.loai_cuoi = "ảnh" if not la_video else "video"
        if la_video:  # video luôn thử đăng dạng Reel trước; Meta từ chối (vd video ngang, quá dài) thì đăng video thường
            try:
                vid = self._len_lich_reel(noi_dung, thoi_diem, file_media)
                self.loai_cuoi = "Reel"
                return vid
            except LoiFacebook as e:
                self.ly_do_khong_reel = str(e)[:150]
        with Path(file_media).open("rb") as fh:
            if la_video:
                r = self._post(f"{self.graph_video}/{self.page_id}/videos",
                               {**hen, "description": noi_dung}, files={"source": (ten_file, fh, mime)})
            else:
                r = self._post(f"{self.graph}/{self.page_id}/photos",
                               {**hen, "message": noi_dung}, files={"source": (ten_file, fh, mime)})
        return r.get("post_id") or r["id"]

    def _len_lich_reel(self, noi_dung: str, thoi_diem: datetime, file_media: str) -> str:
        """Hẹn giờ đăng video dạng Reel (3 bước của Meta: mở phiên, tải lên, chốt lịch). Trả về ID video."""
        bd = self._post(f"{self.graph}/{self.page_id}/video_reels", {"upload_phase": "start"})
        video_id, url = bd["video_id"], bd["upload_url"]
        kich_thuoc = Path(file_media).stat().st_size
        with Path(file_media).open("rb") as fh:
            r = requests.post(url, data=fh, timeout=900, headers={
                "Authorization": f"OAuth {self.token}", "offset": "0", "file_size": str(kich_thuoc)})
        body = r.json() if r.content else {}
        if r.status_code >= 400 or body.get("success") is False or "error" in body:
            raise LoiFacebook(f"Tải Reel lên không được: {str(body)[:150]}")
        self._post(f"{self.graph}/{self.page_id}/video_reels", {
            "upload_phase": "finish", "video_id": video_id, "video_state": "SCHEDULED",
            "scheduled_publish_time": str(int(thoi_diem.timestamp())), "description": noi_dung})
        return str(video_id)
