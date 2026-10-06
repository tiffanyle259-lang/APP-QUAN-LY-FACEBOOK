"""Đọc config.yaml và biến môi trường (GitHub Secrets)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

GOC = Path(__file__).resolve().parent.parent


class ThieuCauHinh(RuntimeError):
    pass


@dataclass
class CauHinh:
    raw: dict

    @classmethod
    def doc(cls, duong_dan: str | Path | None = None) -> "CauHinh":
        p = Path(duong_dan) if duong_dan else GOC / "config.yaml"
        return cls(yaml.safe_load(p.read_text(encoding="utf-8")))

    def __getitem__(self, key):
        return self.raw[key]

    def get(self, key, default=None):
        return self.raw.get(key, default)

    @property
    def mui_gio(self) -> ZoneInfo:
        return ZoneInfo(self.raw.get("mui_gio", "Asia/Ho_Chi_Minh"))

    @property
    def file_du_lieu(self) -> Path:
        return GOC / self.raw["file_du_lieu"]

    @staticmethod
    def bien(ten: str, bat_buoc: bool = True) -> str | None:
        gia_tri = os.environ.get(ten, "").strip()
        if bat_buoc and not gia_tri:
            raise ThieuCauHinh(f"Thiếu biến môi trường/GitHub Secret: {ten}")
        return gia_tri or None

    @classmethod
    def google_service_account(cls) -> dict:
        return json.loads(cls.bien("GOOGLE_SERVICE_ACCOUNT_JSON"))
