"""Vòng học tự động: xem bài nào tương tác cao trong 4 tuần qua để AI học giọng văn, và báo loại bài/khung giờ hiệu quả."""

from __future__ import annotations

from .bao_cao import chuan_bai, diem_bai


def _khoa(noi_dung: str) -> str:
    return " ".join(noi_dung.split())[:80]


def phan_tich(bai_tho: list[dict], dong_sheet: list) -> dict:
    """bai_tho: bài đã đăng từ Facebook; dong_sheet: các DongBai trong Sheet (để biết loại bài và giờ của từng bài)."""
    bai = [chuan_bai(b) for b in bai_tho]
    tra = {_khoa(d.noi_dung): d for d in dong_sheet if d.noi_dung.strip()}
    theo_loai: dict[str, list[int]] = {}
    theo_gio: dict[str, list[int]] = {}
    for b in bai:
        d = tra.get(_khoa(b["noi_dung"]))
        if not d:
            continue
        diem = diem_bai(b)
        theo_loai.setdefault(d.loai_bai.strip() or "?", []).append(diem)
        theo_gio.setdefault(str(d.gio).strip()[:5] or "?", []).append(diem)

    def tb(nhom: dict[str, list[int]]) -> list[tuple[str, float, int]]:
        return sorted(((k, sum(v) / len(v), len(v)) for k, v in nhom.items() if v), key=lambda x: -x[1])

    top = [b for b in sorted(bai, key=diem_bai, reverse=True) if diem_bai(b) > 0][:5]
    return {"top": top, "loai": tb(theo_loai), "gio": tb(theo_gio), "so_bai": len(bai)}


def bai_mau(ph: dict, toi_da: int = 4) -> list[str]:
    """Nội dung các bài thắng để AI học cách mở bài và giọng văn (không sao chép)."""
    return [b["noi_dung"][:700] for b in ph["top"][:toi_da]]


def tom_tat(ph: dict) -> list[str]:
    dong = [f"Phân tích {ph['so_bai']} bài đã đăng 4 tuần qua (điểm = cảm xúc + 2×bình luận + 3×chia sẻ):"]
    dong += [f"  Loại bài {k}: trung bình {v:.1f} điểm/bài ({n} bài)" for k, v, n in ph["loai"]]
    dong += [f"  Giờ {k}: trung bình {v:.1f} điểm/bài ({n} bài)" for k, v, n in ph["gio"]]
    dong += [f"  TOP: điểm {diem_bai(b)} | {(b['noi_dung'].splitlines() or [''])[0][:70]}" for b in ph["top"]]
    return dong
