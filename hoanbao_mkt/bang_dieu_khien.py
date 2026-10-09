"""Bảng điều khiển: một file HTML tự chứa, mở bằng trình duyệt để xem app đang làm gì."""

from __future__ import annotations

import html
from collections import Counter
from datetime import date, datetime

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--text:#1c2430;--muted:#667085;--line:#e4e7ec;--accent:#b7791f;
--cho:#b54708;--cho-bg:#fef0c7;--duyet:#175cd3;--duyet-bg:#d1e9ff;--ok:#067647;--ok-bg:#d1fadf;
--loi:#b42318;--loi-bg:#fee4e2;--bo:#475467;--bo-bg:#eaecf0}
@media(prefers-color-scheme:dark){:root{--bg:#0f1319;--card:#171d26;--text:#e8ecf2;--muted:#9aa6b6;--line:#2a3340;
--accent:#e5b25d;--cho:#fdb022;--cho-bg:#4a3507;--duyet:#84caff;--duyet-bg:#10325c;--ok:#6ce9a6;--ok-bg:#0b3a24;
--loi:#fda29b;--loi-bg:#512018;--bo:#cbd5e1;--bo-bg:#2a3340}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:980px;margin:0 auto;padding:20px 16px 48px}
header{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;align-items:baseline;margin-bottom:16px}
h1{font-size:22px;margin:0}h2{font-size:17px;margin:28px 0 10px}.muted{color:var(--muted);font-size:13px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.num{font-size:28px;font-weight:700;line-height:1.1}.lbl{font-size:13px;color:var(--muted)}
.todo{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:12px;
padding:12px 16px;margin-top:14px}.todo ul{margin:6px 0 0;padding-left:20px}
.post{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-bottom:10px}
.top{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between}
.when{font-weight:650}.badge{font-size:12px;font-weight:650;padding:2px 9px;border-radius:99px}
.s-cho{color:var(--cho);background:var(--cho-bg)}.s-duyet{color:var(--duyet);background:var(--duyet-bg)}
.s-ok{color:var(--ok);background:var(--ok-bg)}.s-loi{color:var(--loi);background:var(--loi-bg)}
.s-bo,.s-moi{color:var(--bo);background:var(--bo-bg)}
.meta{font-size:13px;color:var(--muted);margin-top:2px}.note{font-size:13px;color:var(--cho);margin-top:6px}
details{margin-top:8px}summary{cursor:pointer;color:var(--accent);font-size:14px}
.body{white-space:pre-wrap;margin-top:8px;padding:10px 12px;background:var(--bg);border-radius:8px}
a{color:var(--duyet)}table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);
border-radius:12px;overflow:hidden}th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line);font-size:14px}
th{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.03em}tr:last-child td{border-bottom:0}
.zero{color:var(--loi);font-weight:650}
"""

_LOP = {"Chờ duyệt": "s-cho", "Duyệt": "s-duyet", "Đã lên lịch": "s-ok", "Lỗi": "s-loi", "Bỏ": "s-bo"}
_THU = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]


def _e(x) -> str:
    return html.escape(str(x or ""))


def _ngay(text: str) -> str:
    try:
        d = date.fromisoformat(text)
        return f"{_THU[d.weekday()]} {d:%d/%m}"
    except ValueError:
        return text


def dung_html(d: dict) -> str:
    """d: cap_nhat(str), page(str), che_do_duyet(bool|None), sheet_url(str), bai(list), kho(list)."""
    bai = sorted(d["bai"], key=lambda b: (b["ngay"], b["gio"]))
    dem = Counter(b["trang_thai"] for b in bai)
    kho_trong = [k["ten"] for k in d["kho"] if k["so_file"] == 0 and not k["ten"].startswith("_")]
    cho_phan_loai = next((k["so_file"] for k in d["kho"] if k["ten"] == "_chua-phan-loai"), 0)
    xem_lai = next((k["so_file"] for k in d["kho"] if k["ten"] == "_can-xem-lai"), 0)

    viec = []
    sheet = f'<a href="{_e(d["sheet_url"])}" target="_blank" rel="noopener">mở Google Sheet</a>' if d.get("sheet_url") else "Google Sheet"
    if dem["Chờ duyệt"]:
        viec.append(f"Có <b>{dem['Chờ duyệt']}</b> bài đang chờ duyệt: {sheet}, sửa nội dung nếu cần rồi đổi trạng thái thành <b>Duyệt</b>.")
    if dem["Lỗi"]:
        viec.append(f"Có <b>{dem['Lỗi']}</b> bài bị lỗi: xem cột Ghi chú trong {sheet}.")
    if cho_phan_loai:
        viec.append(f"Có <b>{cho_phan_loai}</b> file chưa xếp loại: chạy workflow <b>Xếp ảnh vào kho</b>.")
    if xem_lai:
        viec.append(f"Có <b>{xem_lai}</b> file trong <code>_can-xem-lai</code> cần kéo về đúng thư mục.")
    if kho_trong:
        viec.append(f"{len(kho_trong)} thư mục kho chưa có ảnh/video: " + ", ".join(f"<code>{_e(t)}</code>" for t in kho_trong[:8])
                    + ("…" if len(kho_trong) > 8 else "") + ". Bài vẫn đăng được, nhưng chỉ có chữ.")
    todo = ("<div class='todo'><b>Việc cần chị/anh làm</b><ul>" + "".join(f"<li>{v}</li>" for v in viec) + "</ul></div>"
            if viec else "<div class='todo'><b>Không có việc gì cần làm.</b> Mọi thứ đang chạy bình thường.</div>")

    def the(num, nhan):
        return f"<div class='card'><div class='num'>{num}</div><div class='lbl'>{nhan}</div></div>"

    cards = "".join([the(len(bai), "Tổng số bài"), the(dem["Chờ duyệt"], "Chờ duyệt"), the(dem["Duyệt"], "Đã duyệt, chờ lên lịch"),
                     the(dem["Đã lên lịch"], "Đã lên lịch đăng"), the(dem["Lỗi"], "Lỗi")])

    ds = []
    for b in bai:
        ghi_chu = f"<div class='note'>{_e(b['ghi_chu'])}</div>" if b.get("ghi_chu") else ""
        media = (f" · <a href='{_e(b['media'])}' target='_blank' rel='noopener'>ảnh/video</a>" if b.get("media")
                 else " · chưa có ảnh/video")
        lop = _LOP.get(b["trang_thai"], "s-moi")
        ds.append(
            f"<div class='post'><div class='top'><div><span class='when'>{_e(_ngay(b['ngay']))} · {_e(b['gio'])}</span>"
            f"<div class='meta'>{_e(b['loai'])}{media}</div></div>"
            f"<span class='badge {lop}'>{_e(b['trang_thai'] or 'Chưa có')}</span></div>{ghi_chu}"
            f"<details><summary>Xem nội dung bài</summary><div class='body'>{_e(b['noi_dung'])}</div></details></div>")
    ds_html = "".join(ds) or "<p class='muted'>Chưa có bài nào. Chạy workflow <b>Tạo bài cả tuần</b>.</p>"

    kho = "".join(
        f"<tr><td><code>{_e(k['ten'])}</code></td><td class='{'zero' if k['so_file'] == 0 and not k['ten'].startswith('_') else ''}'>"
        f"{k['so_file']}</td></tr>" for k in d["kho"])

    che_do = {True: "BẬT (bài phải được duyệt)", False: "TẮT (tự lên lịch)", None: "—"}[d.get("che_do_duyet")]
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Bảng điều khiển Fanpage</title>
<style>{CSS}</style></head><body><main>
<header><h1>Bảng điều khiển Fanpage {_e(d.get('page'))}</h1>
<span class="muted">Cập nhật: {_e(d['cap_nhat'])} · Chế độ duyệt: <b>{che_do}</b></span></header>
<div class="cards">{cards}</div>{todo}
<h2>Lịch bài đăng</h2>{ds_html}
<h2>Kho ảnh/video (số file mỗi thư mục)</h2>
<table><thead><tr><th>Thư mục</th><th>Số file</th></tr></thead><tbody>{kho}</tbody></table>
<p class="muted">Trang này chỉ để xem. Muốn sửa bài hoặc duyệt bài, làm trong Google Sheet.</p>
</main></body></html>"""


def thu_thap(cfg, drive, sheets, sheet_id: str, kho_id: str, ten_page: str = "") -> dict:
    """Gom dữ liệu thật từ Google Sheet và Drive."""
    from .duyet_bai import SheetDuyet
    from .kho_anh import KhoDrive

    sheet = SheetDuyet(sheets, sheet_id)
    kho = KhoDrive(drive, kho_id) if kho_id else None
    bai = [{"ma_bai": r.ma_bai, "ngay": r.ngay, "gio": r.gio, "loai": r.loai_bai, "noi_dung": r.noi_dung,
            "media": r.media, "trang_thai": r.trang_thai.strip(), "ghi_chu": r.ghi_chu, "facebook_id": r.facebook_id}
           for r in sheet.doc_tat_ca()]
    ten_thu_muc = sorted({n for n in _ten_thu_muc_kho(cfg)}) + ["_chua-phan-loai", "_can-xem-lai"]
    dem = []
    for ten in ten_thu_muc if kho else []:  # chưa có DRIVE_KHO_ID thì bỏ phần kho ảnh
        tm = kho.id_thu_muc(ten)
        dem.append({"ten": ten, "so_file": len(kho.liet_ke_de_quy(tm)) if tm else 0})
    return {"cap_nhat": datetime.now(cfg.mui_gio).strftime("%H:%M %d/%m/%Y"), "page": ten_page,
            "che_do_duyet": sheet.che_do_duyet(cfg["che_do_duyet"]),
            "sheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}", "bai": bai, "kho": dem}


def _ten_thu_muc_kho(cfg):
    from .du_lieu import doc_du_lieu

    du_lieu = doc_du_lieu(cfg.file_du_lieu, cfg.get("cot_bo_qua"))
    tm = cfg["thu_muc"]
    return ([sp.thu_muc for sp in du_lieu.san_pham if sp.thu_muc] + [tm["anh_chung"], *tm["theo_nganh"].values(),
            "video-demo", "khach-hang", "nha-may"])
