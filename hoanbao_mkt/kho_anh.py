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
    nhom: str = ""  # tên thư mục chứa (vd 405A, SPRO): thư mục theo mã hàng cũng được tính khi khớp từ khóa
    can_khop: bool = False  # file từ nguồn chung: chỉ dùng cho bài có từ khóa (mã sản phẩm) khớp tên file

    @property
    def la_video(self) -> bool:
        return self.mime.startswith("video/")

    @property
    def link(self) -> str:
        return f"https://drive.google.com/file/d/{self.id}/view"


def khop_ma(f: "FileMedia", ma_san_pham: list[str]) -> bool:
    """File ghi đúng mã một trong các sản phẩm (trong tên file hoặc tên thư mục chứa), vd HP-333 khớp HP333, S-PRO khớp spro."""
    ma = [bo_dau(m).replace(" ", "") for m in ma_san_pham if m and m.strip()]
    van_ban = bo_dau(f"{f.ten} {f.nhom}")
    tu = set(van_ban.split())
    gon = van_ban.replace(" ", "")
    return any(m in tu or (not m.isdigit() and m in gon) for m in ma)


def ma_mo_rong(ma_san_pham: list[str], ma_phu: dict | None) -> list[str]:
    """Thêm tên gọi khác của sản phẩm (vd SUPERPRO còn gọi là SPRO, S-PRO) để khớp được tên file."""
    ra = list(ma_san_pham)
    phu = {bo_dau(k).replace(" ", ""): v for k, v in (ma_phu or {}).items()}
    for m in ma_san_pham:
        ra += list(phu.get(bo_dau(m).replace(" ", ""), []))
    return ra


def chon_file(
    ds: list[FileMedia],
    tu_khoa: list[str],
    uu_tien_video: bool,
    da_chon: set[str],
    hom_nay: date,
    khong_lap_lai_trong_ngay: int,
    dang_dung: frozenset[str] | set[str] = frozenset(),
    ma_bat_buoc: list[str] | None = None,
    chi_video: bool = False,
) -> FileMedia | None:
    """Chấm điểm theo tên file khớp từ khóa, đúng loại (ảnh/video), lâu chưa dùng."""
    tu_khoa = [bo_dau(t) for t in tu_khoa if t.strip()]

    def diem(f: FileMedia):
        ten = bo_dau(f"{f.ten} {f.nhom}")
        tu_ten = set(ten.split())
        khop = sum(1 for t in tu_khoa if t in tu_ten or (" " in t and t in ten))
        d = khop * 3
        d += 5 if f.la_video == uu_tien_video else 0
        if f.lan_dung_cuoi and (hom_nay - f.lan_dung_cuoi).days < khong_lap_lai_trong_ngay:
            d -= 30
        if f.id in dang_dung:  # đang nằm trong một bài khác của Sheet (chưa/đã lên lịch)
            d -= 30
        # Ưu tiên file chưa dùng bao giờ, rồi file lâu chưa dùng nhất.
        return (-d, f.lan_dung_cuoi or date.min, f.ten)

    def khop_ten(f: FileMedia) -> bool:
        tu_ten = set(bo_dau(f"{f.ten} {f.nhom}").split())
        return any(t in tu_ten for t in tu_khoa)

    ma = list(ma_bat_buoc or [])

    def dung_san_pham(f: FileMedia) -> bool:
        return not ma or not f.can_khop or khop_ma(f, ma)

    con_lai = [f for f in ds if f.id not in da_chon and dung_san_pham(f) and (f.la_video or not chi_video)]
    if chi_video:
        con_lai = [f for f in con_lai if f.la_video]

    def tuoi(f):
        return f.id not in dang_dung and not (f.lan_dung_cuoi and (hom_nay - f.lan_dung_cuoi).days < khong_lap_lai_trong_ngay)

    # Đúng sản phẩm là điều kiện bắt buộc; trong đó ưu tiên file chưa dùng gần đây, chỉ khi hết mới dùng lại.
    pool = [f for f in con_lai if tuoi(f)] or con_lai
    return min(pool, key=diem) if pool else None


def file_nguon_chung_hop_le(ten: str, mime: str, trong_thu_muc_video: bool, video_cho_phep: bool = True,
                            anh_cho_phep: bool = True) -> bool:
    """Ảnh: chỉ khi nằm trong thư mục ảnh được phép (ảnh sạch AI, ảnh quảng cáo). Video: chỉ khi nằm trong thư mục video được phép."""
    if mime.startswith("video/"):
        return video_cho_phep
    return mime.startswith("image/") and not trong_thu_muc_video and anh_cho_phep


class KhoDrive:
    def __init__(self, drive_service, thu_muc_goc_id: str, nguon_chung: list[str] | None = None,
                 loai_tru: list[str] | None = None, video_tu: list[str] | None = None, anh_tu: list[str] | None = None,
                 chi_nguon_chung: bool = False):
        self.svc = drive_service
        self.goc = thu_muc_goc_id
        self.nguon_chung = [n for n in (nguon_chung or []) if n]
        self.loai_tru = [bo_dau(x) for x in (loai_tru or [])]
        self.video_tu = [bo_dau(x) for x in (video_tu or [])]
        self.anh_tu = [bo_dau(x) for x in (anh_tu or [])]  # rỗng = lấy ảnh ở mọi thư mục
        self.chi_nguon_chung = chi_nguon_chung and bool(self.nguon_chung)  # true: bỏ hẳn ảnh trong Kho-Marketing
        self._cache: dict[str, list[FileMedia]] = {}
        self._chung: list[FileMedia] | None = None

    def file_nguon_chung(self) -> list[FileMedia]:
        """Ảnh/video trong các thư mục nguồn chung (chỉ đọc, không di chuyển). Bỏ thư mục không phải ảnh đăng (SEO, banner...);
        video chỉ lấy trong thư mục video sạch AI / reel."""
        if self._chung is not None:
            return self._chung
        ds: list[FileMedia] = []
        # (id thư mục, đang trong thư mục video, được lấy video, được lấy ảnh)
        hang_doi = [(n, False, False, not self.anh_tu, "") for n in self.nguon_chung]
        while hang_doi:
            tm_id, trong_video, video_ok, anh_ok, ten_nhom = hang_doi.pop()
            for f in self._liet_ke(f"'{tm_id}' in parents and trashed = false", "id, name, mimeType, appProperties"):
                if f["mimeType"] == FOLDER:
                    ten = bo_dau(f["name"])
                    if any(x and x in ten for x in self.loai_tru):
                        continue
                    hang_doi.append((f["id"], trong_video or ten.startswith("video"),
                                     video_ok or any(x and x in ten for x in self.video_tu),
                                     anh_ok or any(x and x in ten for x in self.anh_tu), f"{ten_nhom} {f['name']}".strip()))
                elif file_nguon_chung_hop_le(f["name"], f["mimeType"], trong_video, video_ok, anh_ok):
                    dung = (f.get("appProperties") or {}).get("lan_dung_cuoi")
                    ds.append(FileMedia(f["id"], f["name"], f["mimeType"],
                                        date.fromisoformat(dung) if dung else None, nhom=ten_nhom, can_khop=True))
        self._chung = ds
        return ds

    def _liet_ke(self, q: str, fields: str) -> list[dict]:
        ket_qua, token = [], None
        while True:
            r = self.svc.files().list(
                q=q, fields=f"nextPageToken, files({fields})", pageSize=200, pageToken=token,
                includeItemsFromAllDrives=True, **_CHUNG,
            ).execute(num_retries=3)  # Drive thỉnh thoảng báo lỗi 500 tạm thời
            ket_qua += r.get("files", [])
            token = r.get("nextPageToken")
            if not token:
                return ket_qua

    def file_trong(self, ten_thu_muc: str) -> list[FileMedia]:
        if self.chi_nguon_chung:
            return self.file_nguon_chung()
        if ten_thu_muc in self._cache:
            return self._cache[ten_thu_muc]
        ten = ten_thu_muc.replace("'", "\\'")
        thu_muc = self._liet_ke(
            f"'{self.goc}' in parents and name = '{ten}' and mimeType = '{FOLDER}' and trashed = false", "id")
        ds: list[FileMedia] = []
        hang_doi = [tm["id"] for tm in thu_muc]  # gồm cả thư mục con (vd. KOL) lồng bên trong
        while hang_doi:
            tm_id = hang_doi.pop()
            hang_doi += [d["id"] for d in self._liet_ke(
                f"'{tm_id}' in parents and trashed = false and mimeType = '{FOLDER}'", "id")]
            for f in self._liet_ke(
                f"'{tm_id}' in parents and trashed = false and "
                "(mimeType contains 'image/' or mimeType contains 'video/')",
                "id, name, mimeType, appProperties",
            ):
                dung = (f.get("appProperties") or {}).get("lan_dung_cuoi")
                ds.append(FileMedia(f["id"], f["name"], f["mimeType"], date.fromisoformat(dung) if dung else None))
        ds += self.file_nguon_chung()
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

    def id_thu_muc(self, ten: str, tao: bool = False) -> str | None:
        """ID thư mục con của Kho-Marketing; tao=True thì tạo nếu chưa có."""
        ten_q = ten.replace("'", "\\'")
        tim = self._liet_ke(
            f"'{self.goc}' in parents and name = '{ten_q}' and mimeType = '{FOLDER}' and trashed = false", "id")
        if tim:
            return tim[0]["id"]
        if not tao:
            return None
        return self.svc.files().create(
            body={"name": ten, "mimeType": FOLDER, "parents": [self.goc]}, fields="id", **_CHUNG
        ).execute()["id"]

    def liet_ke_de_quy(self, thu_muc_id: str) -> list[dict]:
        """Mọi file (không tính thư mục) trong thư mục và các thư mục con lồng nhau, kèm 'parents'."""
        ket_qua, hang_doi = [], [thu_muc_id]
        while hang_doi:
            tm = hang_doi.pop()
            ket_qua += self._liet_ke(
                f"'{tm}' in parents and trashed = false and mimeType != '{FOLDER}'",
                "id, name, mimeType, parents")
            hang_doi += [d["id"] for d in self._liet_ke(
                f"'{tm}' in parents and trashed = false and mimeType = '{FOLDER}'", "id")]
        return ket_qua

    def tai_bytes(self, file_id: str) -> bytes:
        return self.svc.files().get_media(fileId=file_id, **_CHUNG).execute()

    def chuyen(self, file_id: str, tu_id: str, den_id: str, ten_moi: str | None = None) -> None:
        body = {"name": ten_moi} if ten_moi else {}
        self.svc.files().update(
            fileId=file_id, body=body, addParents=den_id, removeParents=tu_id, fields="id", **_CHUNG
        ).execute()
        self._cache.clear()

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
