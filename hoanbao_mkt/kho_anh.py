"""Chọn ảnh/video từ Google Drive, thư mục "Kho-Marketing" và các thư mục con."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import date, datetime

from googleapiclient.http import MediaIoBaseDownload

from .ke_hoach import bo_dau

FOLDER = "application/vnd.google-apps.folder"
_CHUNG = {"supportsAllDrives": True}


@dataclass
class FileMedia:
    id: str
    ten: str
    mime: str
    lan_dung_cuoi: date | None = None

    @property
    def la_video(self) -> bool:
        return self.mime.startswith("video/")

    @property
    def link(self) -> str:
        return f"https://drive.google.com/file/d/{self.id}/view"


def chon_file(
    ds: list[FileMedia],
    tu_khoa: list[str],
    uu_tien_video: bool,
    da_chon: set[str],
    hom_nay: date,
    khong_lap_lai_trong_ngay: int,
) -> FileMedia | None:
    """Chấm điểm theo tên file khớp từ khóa, đúng loại (ảnh/video), lâu chưa dùng."""
    tu_khoa = [bo_dau(t) for t in tu_khoa if t.strip()]

    def diem(f: FileMedia):
        ten = bo_dau(f.ten)
        tu_ten = set(ten.split())
        khop = sum(1 for t in tu_khoa if t in tu_ten or (" " in t and t in ten))
        d = khop * 3
        d += 5 if f.la_video == uu_tien_video else 0
        if f.lan_dung_cuoi and (hom_nay - f.lan_dung_cuoi).days < khong_lap_lai_trong_ngay:
            d -= 10
        # Ưu tiên file chưa dùng bao giờ, rồi file lâu chưa dùng nhất.
        return (-d, f.lan_dung_cuoi or date.min, f.ten)

    con_lai = [f for f in ds if f.id not in da_chon]
    return min(con_lai, key=diem) if con_lai else None


class KhoDrive:
    def __init__(self, drive_service, thu_muc_goc_id: str):
        self.svc = drive_service
        self.goc = thu_muc_goc_id
        self._cache: dict[str, list[FileMedia]] = {}

    def _liet_ke(self, q: str, fields: str) -> list[dict]:
        ket_qua, token = [], None
        while True:
            r = self.svc.files().list(
                q=q, fields=f"nextPageToken, files({fields})", pageSize=200, pageToken=token,
                includeItemsFromAllDrives=True, **_CHUNG,
            ).execute()
            ket_qua += r.get("files", [])
            token = r.get("nextPageToken")
            if not token:
                return ket_qua

    def file_trong(self, ten_thu_muc: str) -> list[FileMedia]:
        if ten_thu_muc in self._cache:
            return self._cache[ten_thu_muc]
        ten = ten_thu_muc.replace("'", "\\'")
        thu_muc = self._liet_ke(
            f"'{self.goc}' in parents and name = '{ten}' and mimeType = '{FOLDER}' and trashed = false", "id")
        ds: list[FileMedia] = []
        for tm in thu_muc:
            for f in self._liet_ke(
                f"'{tm['id']}' in parents and trashed = false and "
                "(mimeType contains 'image/' or mimeType contains 'video/')",
                "id, name, mimeType, appProperties",
            ):
                dung = (f.get("appProperties") or {}).get("lan_dung_cuoi")
                ds.append(FileMedia(f["id"], f["name"], f["mimeType"], date.fromisoformat(dung) if dung else None))
        self._cache[ten_thu_muc] = ds
        return ds

    def tao_thu_muc_con(self, ten_thu_muc: list[str]) -> list[str]:
        """Tạo các thư mục con còn thiếu trong Kho-Marketing. Trả về tên các thư mục vừa tạo."""
        da_co = {f["name"] for f in self._liet_ke(
            f"'{self.goc}' in parents and mimeType = '{FOLDER}' and trashed = false", "name")}
        moi = [t for t in dict.fromkeys(ten_thu_muc) if t not in da_co]
        for ten in moi:
            self.svc.files().create(
                body={"name": ten, "mimeType": FOLDER, "parents": [self.goc]}, fields="id", **_CHUNG
            ).execute()
        self._cache.clear()
        return moi

    def thong_tin(self, file_id: str) -> FileMedia:
        f = self.svc.files().get(fileId=file_id, fields="id, name, mimeType", **_CHUNG).execute()
        return FileMedia(f["id"], f["name"], f["mimeType"])

    def tai_ve(self, file_id: str) -> str:
        """Tải file về thư mục tạm, trả về đường dẫn."""
        with tempfile.NamedTemporaryFile(delete=False) as fh:
            req = self.svc.files().get_media(fileId=file_id, **_CHUNG)
            dl = MediaIoBaseDownload(fh, req, chunksize=20 * 1024 * 1024)
            xong = False
            while not xong:
                _, xong = dl.next_chunk()
        return fh.name

    def danh_dau_da_dung(self, file_id: str, ngay: datetime) -> None:
        self.svc.files().update(
            fileId=file_id, body={"appProperties": {"lan_dung_cuoi": ngay.date().isoformat()}}, **_CHUNG
        ).execute()
