"""Nhập khách để lại thông tin qua quảng cáo Facebook (file CSV 'Biểu mẫu' tải từ Meta) vào tab 'Khách hàng'."""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from zoneinfo import ZoneInfo

KENH = "Quảng cáo Facebook"
VN = ZoneInfo("Asia/Ho_Chi_Minh")


def chuan_sdt(text: str) -> str:
    """'+84976884341' -> '0976884341'. Không đoán được thì giữ nguyên chữ số."""
    so = re.sub(r"[^\d+]", "", text or "")
    if so.startswith("+84"):
        return "0" + so[3:]
    if so.startswith("84") and len(so) >= 11:
        return "0" + so[2:]
    return re.sub(r"\D", "", so)


def doi_gio(text: str) -> str:
    try:
        return datetime.fromisoformat(text).astimezone(VN).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return (text or "").strip()


def doc_csv_quang_cao(noi_dung: str) -> list[list[str]]:
    """Dòng 9 cột cho tab Khách hàng. Mã khách quảng cáo ghi ở cột 'ID Messenger' dạng 'lead:<id>' để không nhập trùng."""
    doc = csv.DictReader(io.StringIO(noi_dung.lstrip("﻿")))
    ket_qua = []
    for r in doc:
        ma, ten, sdt = (r.get("id") or "").strip(), (r.get("full_name") or "").strip(), chuan_sdt(r.get("phone_number", ""))
        if not ma or not (ten or sdt):
            continue
        nhu_cau = (r.get("form_name") or r.get("campaign_name") or "").strip()
        ket_qua.append([doi_gio(r.get("created_time", "")), KENH, f"lead:{ma}", ten, sdt,
                        f"Quảng cáo: {nhu_cau}"[:200], "Để lại thông tin qua biểu mẫu quảng cáo", "Mới", ""])
    return ket_qua
