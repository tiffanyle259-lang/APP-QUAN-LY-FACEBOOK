"""Xem trước và chọn ảnh/video trong Kho-Marketing cho bảng điều khiển.

Mọi file đều phải nằm trong Kho-Marketing (kiểm tra theo chuỗi thư mục cha), nên bảng điều khiển không đọc được
file nào khác mà tài khoản dịch vụ có quyền xem.
"""

from __future__ import annotations

import io
import re
import threading
from collections import OrderedDict

import requests

FOLDER = "application/vnd.google-apps.folder"
_CHUNG = {"supportsAllDrives": True}
_ID = re.compile(r"^[A-Za-z0-9_-]{10,}$")


class NgoaiKho(ValueError):
    """File không nằm trong Kho-Marketing."""


class KhoXem:
    def __init__(self, drive, kho_id: str, lay_token=None, http=None):
        self.drive, self.kho_id = drive, kho_id
        self.lay_token = lay_token  # hàm trả về access token Google, dùng cho ảnh xem trước
        self.http = http or requests
        self._trong_kho: dict[str, bool] = {}
        # Client Google (httplib2) không an toàn khi nhiều luồng dùng chung, nên các lệnh gọi Drive đi lần lượt.
        self._khoa = threading.Lock()
        self._nho: OrderedDict[str, bytes] = OrderedDict()  # ảnh xem trước vừa lấy, tối đa 40 ảnh

    def hop_le(self, file_id: str) -> bool:
        """True nếu file nằm (ở bất kỳ cấp nào) trong Kho-Marketing."""
        if not _ID.match(file_id or ""):
            return False
        if file_id in self._trong_kho:
            return self._trong_kho[file_id]
        hien, ket_qua = file_id, False
        for _ in range(8):
            with self._khoa:
                f = self.drive.files().get(fileId=hien, fields="id,parents", **_CHUNG).execute()
            cha = (f.get("parents") or [None])[0]
            if cha is None:
                break
            if cha == self.kho_id:
                ket_qua = True
                break
            hien = cha
        self._trong_kho[file_id] = ket_qua
        return ket_qua

    def thong_tin(self, file_id: str) -> dict:
        if not self.hop_le(file_id):
            raise NgoaiKho("File không nằm trong Kho-Marketing.")
        with self._khoa:
            return self.drive.files().get(fileId=file_id, fields="id,name,mimeType,size,thumbnailLink", **_CHUNG).execute()

    def anh_nho(self, file_id: str, canh: int = 640) -> bytes:
        """Ảnh xem trước (JPEG/PNG) của ảnh hoặc video."""
        if file_id in self._nho:
            self._nho.move_to_end(file_id)
            return self._nho[file_id]
        noi_dung = self._lay_anh_nho(file_id, canh)
        self._nho[file_id] = noi_dung
        while len(self._nho) > 40:
            self._nho.popitem(last=False)
        return noi_dung

    def _lay_anh_nho(self, file_id: str, canh: int) -> bytes:
        f = self.thong_tin(file_id)
        link = f.get("thumbnailLink")
        if link and self.lay_token:
            link = re.sub(r"=s\d+(-c)?$", f"=s{canh}", link)
            r = self.http.get(link, headers={"Authorization": f"Bearer {self.lay_token()}"}, timeout=20)
            if r.status_code == 200 and r.content:
                return r.content
        if f["mimeType"].startswith("image/"):  # không có ảnh xem trước từ Drive: tải ảnh gốc rồi thu nhỏ
            if int(f.get("size") or 0) > 6_000_000:  # ảnh quá nặng có thể làm máy chủ hết bộ nhớ
                raise NgoaiKho("Ảnh quá lớn để xem trước.")
            from PIL import Image

            with self._khoa:
                goc = self.drive.files().get_media(fileId=file_id, **_CHUNG).execute()
            img = Image.open(io.BytesIO(goc))
            img.thumbnail((canh, canh))
            buf = io.BytesIO()
            img.convert("RGB").save(buf, "JPEG", quality=82)
            return buf.getvalue()
        raise NgoaiKho("Không có ảnh xem trước cho file này.")

    def danh_sach(self, ten_thu_muc: str, toi_da: int = 80) -> list[dict]:
        """Ảnh/video trong một thư mục con của Kho-Marketing."""
        ten = (ten_thu_muc or "").replace("\\", "\\\\").replace("'", "\\'")
        with self._khoa:
            tim = self.drive.files().list(
                q=f"'{self.kho_id}' in parents and name = '{ten}' and mimeType = '{FOLDER}' and trashed = false",
                fields="files(id)", includeItemsFromAllDrives=True, **_CHUNG).execute().get("files", [])
            if not tim:
                return []
            r = self.drive.files().list(
                q=f"'{tim[0]['id']}' in parents and trashed = false and (mimeType contains 'image/' or mimeType contains 'video/')",
                fields="files(id,name,mimeType)", pageSize=toi_da, orderBy="name", includeItemsFromAllDrives=True,
                **_CHUNG).execute()
        return [{"id": f["id"], "ten": f["name"], "video": f["mimeType"].startswith("video/")} for f in r.get("files", [])]
