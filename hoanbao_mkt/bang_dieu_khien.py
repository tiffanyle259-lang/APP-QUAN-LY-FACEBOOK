"""Bảng điều khiển: một file HTML tự chứa, mở bằng trình duyệt để xem app đang làm gì."""

from __future__ import annotations

import html
import re
from collections import Counter
from datetime import date, datetime

CSS = """
/* Bố cục: thanh thương hiệu, hàng chỉ số, việc cần làm, lịch bài dạng thẻ có ảnh, kho ảnh dạng thanh. */
:root{--bg:#f3f4f6;--card:#ffffff;--ink:#141a24;--muted:#5d6877;--line:#e1e4ea;--gold:#d99a00;--gold-ink:#7a5200;
--gold-bg:#fff4d1;--cho:#9a5b00;--cho-bg:#ffedc2;--duyet:#1849a9;--duyet-bg:#dbe8ff;--ok:#05603a;--ok-bg:#d3f5e2;
--loi:#a3201a;--loi-bg:#ffe0dd;--bo:#475467;--bo-bg:#e9ecf1;--bar:#d99a00;--bar-bg:#eceef3;--shadow:0 1px 2px rgba(20,26,36,.06)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0d1117;--card:#161b22;--ink:#e8edf4;--muted:#9aa5b5;
--line:#2a323d;--gold:#f0b429;--gold-ink:#f6cf74;--gold-bg:#3a2d08;--cho:#f6c35b;--cho-bg:#46330a;--duyet:#8bb8ff;
--duyet-bg:#14305e;--ok:#5fe0a1;--ok-bg:#0b3a24;--loi:#ff9d94;--loi-bg:#511b17;--bo:#c3cddb;--bo-bg:#272f3a;
--bar:#f0b429;--bar-bg:#262d38;--shadow:none;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0d1117;--card:#161b22;--ink:#e8edf4;--muted:#9aa5b5;--line:#2a323d;--gold:#f0b429;
--gold-ink:#f6cf74;--gold-bg:#3a2d08;--cho:#f6c35b;--cho-bg:#46330a;--duyet:#8bb8ff;--duyet-bg:#14305e;--ok:#5fe0a1;
--ok-bg:#0b3a24;--loi:#ff9d94;--loi-bg:#511b17;--bo:#c3cddb;--bo-bg:#272f3a;--bar:#f0b429;--bar-bg:#262d38;--shadow:none;
color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 "Be Vietnam Pro",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:0 16px 56px}
.brand{background:var(--ink);color:var(--bg);border-bottom:4px solid var(--gold)}
.brand .in{max-width:1080px;margin:0 auto;padding:18px 16px;display:flex;flex-wrap:wrap;gap:6px 20px;align-items:center;
justify-content:space-between}
.logo{display:flex;align-items:center;gap:12px;min-width:0}
.mark{width:38px;height:38px;border-radius:10px;background:var(--gold);color:#1a1200;display:grid;place-items:center;
font-weight:800;font-size:17px;flex:none}
h1{font-size:19px;line-height:1.25;margin:0;font-weight:700;text-wrap:balance}
.sub{font-size:13px;opacity:.75}
.live{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px;align-items:center}
.dot{width:8px;height:8px;border-radius:50%;background:#2fd18b;display:inline-block;margin-right:6px}
.pill{border:1px solid color-mix(in srgb,var(--bg) 30%,transparent);border-radius:99px;padding:2px 10px}
h2{font-size:15px;margin:30px 0 12px;font-weight:700;letter-spacing:.01em;display:flex;align-items:baseline;gap:10px}
h2 small{font-weight:500;color:var(--muted);font-size:13px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:0;margin-top:20px;background:var(--card);
border:1px solid var(--line);border-radius:14px;overflow:hidden;box-shadow:var(--shadow)}
.stat{padding:14px 18px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);margin:0 -1px -1px 0}
.stat b{display:block;font-size:26px;line-height:1.15;font-variant-numeric:tabular-nums;font-weight:700}
.stat span{font-size:13px;color:var(--muted)}
.stat.canh b{color:var(--cho)}.stat.xanh b{color:var(--ok)}.stat.do b{color:var(--loi)}
.todo{margin-top:16px;background:var(--gold-bg);color:var(--ink);border:1px solid color-mix(in srgb,var(--gold) 45%,var(--line));
border-radius:14px;padding:14px 18px}
.todo.ok{background:var(--ok-bg);border-color:transparent}
.todo b.t{display:block;font-size:14px;margin-bottom:6px;color:var(--gold-ink)}.todo.ok b.t{color:var(--ok)}
.todo ul{margin:0;padding-left:18px}.todo li{margin:3px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,470px),1fr));gap:12px}
.post{background:var(--card);border:1px solid var(--line);border-radius:14px;display:grid;grid-template-columns:116px minmax(0,1fr);
overflow:hidden;box-shadow:var(--shadow)}
.thumb{background:var(--bar-bg);display:grid;place-items:center;color:var(--muted);font-size:12px;text-align:center;padding:6px;
min-height:132px;position:relative}
.thumb img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.pb{padding:12px 14px;min-width:0;display:flex;flex-direction:column;gap:6px}
.row{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;justify-content:space-between}
.when{font-weight:700;font-variant-numeric:tabular-nums}.loai{font-size:13px;color:var(--muted)}
.badge{font-size:12px;font-weight:650;padding:2px 10px;border-radius:99px;white-space:nowrap}
.s-cho{color:var(--cho);background:var(--cho-bg)}.s-duyet{color:var(--duyet);background:var(--duyet-bg)}
.s-ok{color:var(--ok);background:var(--ok-bg)}.s-loi{color:var(--loi);background:var(--loi-bg)}
.s-bo,.s-moi{color:var(--bo);background:var(--bo-bg)}
.pv{font-size:14px;color:var(--ink);display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;
overflow-wrap:anywhere}
.note{font-size:12.5px;color:var(--cho)}.note.loi{color:var(--loi)}
details summary{cursor:pointer;color:var(--duyet);font-size:13px;font-weight:600;width:max-content}
details summary:focus-visible,a:focus-visible{outline:2px solid var(--gold);outline-offset:2px;border-radius:4px}
.body{white-space:pre-wrap;margin-top:6px;padding:10px 12px;background:var(--bg);border-radius:10px;font-size:14px;
overflow-wrap:anywhere}
a{color:var(--duyet)}
.kho{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:6px 16px;box-shadow:var(--shadow)}
.k{display:grid;grid-template-columns:minmax(120px,190px) 1fr 44px;gap:12px;align-items:center;padding:8px 0;
border-bottom:1px solid var(--line);font-size:14px}.k:last-child{border-bottom:0}
.k code{font:13px ui-monospace,"JetBrains Mono",Menlo,Consolas,monospace;overflow-wrap:anywhere}
.track{height:8px;background:var(--bar-bg);border-radius:99px;overflow:hidden}
.fill{height:100%;background:var(--bar);border-radius:99px}
.k .n{text-align:right;font-variant-numeric:tabular-nums;font-weight:650}.k .n.zero{color:var(--loi)}
.kh{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;box-shadow:var(--shadow)}
.kh .scroll{overflow-x:auto}.kh table{width:100%;border-collapse:collapse;min-width:640px}
.kh th{font-size:12px;text-align:left;color:var(--muted);font-weight:600;padding:9px 14px;border-bottom:1px solid var(--line);white-space:nowrap}
.kh td{padding:9px 14px;border-bottom:1px solid var(--line);font-size:14px;vertical-align:top;overflow-wrap:anywhere}
.kh tr:last-child td{border-bottom:0}.sdt{font-variant-numeric:tabular-nums;font-weight:650;white-space:nowrap}
.chats{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,330px),1fr));gap:12px}
.chat{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px;box-shadow:var(--shadow);min-width:0}
.chat h3{margin:0 0 8px;font-size:14px;display:flex;justify-content:space-between;gap:8px;align-items:baseline}
.chat h3 small{font-weight:500;color:var(--muted);font-size:12px;white-space:nowrap}
.msg{max-width:88%;padding:6px 10px;border-radius:12px;font-size:13.5px;margin:4px 0;overflow-wrap:anywhere;white-space:pre-wrap}
.msg.khach{background:var(--bar-bg);border-bottom-left-radius:4px}
.msg.page{background:var(--gold-bg);color:var(--ink);margin-left:auto;border-bottom-right-radius:4px}
.msg.page::before{content:"Page/bot · ";font-size:11px;color:var(--gold-ink);font-weight:650}
.canhbao{background:var(--card);border:1px dashed var(--line);border-radius:14px;padding:14px 16px;color:var(--muted);font-size:14px}
.foot{margin-top:28px;font-size:13px;color:var(--muted)}
.empty{background:var(--card);border:1px dashed var(--line);border-radius:14px;padding:22px;color:var(--muted)}
@media (max-width:520px){.post{grid-template-columns:88px minmax(0,1fr)}.k{grid-template-columns:1fr 36px}.k .track{grid-column:1/-1;order:3}}
"""

_LOP = {"Chờ duyệt": "s-cho", "Duyệt": "s-duyet", "Đã lên lịch": "s-ok", "Lỗi": "s-loi", "Bỏ": "s-bo"}
_THU = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
_DRIVE_ID = re.compile(r"(?:/d/|[?&]id=)([A-Za-z0-9_-]{10,})")


def _e(x) -> str:
    return html.escape(str(x or ""))


def _ngay(text: str) -> str:
    try:
        d = date.fromisoformat(text)
        return f"{_THU[d.weekday()]} {d:%d/%m}"
    except ValueError:
        return text


def _gio_vn(iso: str) -> str:
    """Đổi giờ ISO của Facebook (UTC) sang giờ Việt Nam dạng 14:05 09/10."""
    try:
        from zoneinfo import ZoneInfo
        t = datetime.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=ZoneInfo("UTC"))
        return t.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%H:%M %d/%m")
    except ValueError:
        return iso


def _anh_nho(link: str) -> str:
    """Ảnh xem trước từ Drive (hiện khi người xem đang đăng nhập Google có quyền xem ảnh)."""
    m = _DRIVE_ID.search(link or "")
    if not m:
        return "<span>Chưa có<br>ảnh/video</span>"
    return (f"<span>Ảnh/video</span><img loading='lazy' alt='' referrerpolicy='no-referrer' "
            f"src='https://drive.google.com/thumbnail?id={m.group(1)}&sz=w400' onerror=\"this.remove()\">")


def dung_html(d: dict) -> str:
    """d: cap_nhat(str), page(str), che_do_duyet(bool|None), sheet_url(str), bai(list), kho(list)."""
    bai = sorted(d["bai"], key=lambda b: (b["ngay"], b["gio"]))
    dem = Counter(b["trang_thai"] for b in bai)
    kho_trong = [k["ten"] for k in d["kho"] if k["so_file"] == 0 and not k["ten"].startswith("_")]
    cho_phan_loai = next((k["so_file"] for k in d["kho"] if k["ten"] == "_chua-phan-loai"), 0)
    xem_lai = next((k["so_file"] for k in d["kho"] if k["ten"] == "_can-xem-lai"), 0)

    viec = []
    sheet = (f'<a href="{_e(d["sheet_url"])}" target="_blank" rel="noopener">mở Google Sheet</a>'
             if d.get("sheet_url") else "Google Sheet")
    if dem["Chờ duyệt"]:
        viec.append(f"<b>{dem['Chờ duyệt']}</b> bài đang chờ duyệt: {sheet}, sửa nội dung nếu cần rồi chọn trạng thái <b>Duyệt</b>.")
    if dem["Lỗi"]:
        viec.append(f"<b>{dem['Lỗi']}</b> bài bị lỗi: xem cột Ghi chú trong {sheet}.")
    if cho_phan_loai:
        viec.append(f"<b>{cho_phan_loai}</b> file chưa xếp loại: app tự xếp lúc 8h17 sáng, hoặc chạy <b>Xếp ảnh vào kho</b>.")
    if xem_lai:
        viec.append(f"<b>{xem_lai}</b> file trong <code>_can-xem-lai</code> cần kéo về đúng thư mục.")
    if kho_trong:
        viec.append(f"{len(kho_trong)} thư mục kho chưa có ảnh/video: " + ", ".join(f"<code>{_e(t)}</code>" for t in kho_trong[:8])
                    + ("…" if len(kho_trong) > 8 else "") + ". Bài vẫn đăng được, nhưng chỉ có chữ.")
    todo = ("<div class='todo'><b class='t'>Việc cần chị/anh làm</b><ul>" + "".join(f"<li>{v}</li>" for v in viec) + "</ul></div>"
            if viec else "<div class='todo ok'><b class='t'>Không có việc cần làm</b>Mọi thứ đang chạy bình thường.</div>")

    def chi_so(num, nhan, lop=""):
        return f"<div class='stat {lop}'><b>{num}</b><span>{nhan}</span></div>"

    stats = "".join([
        chi_so(len(bai), "Tổng số bài"),
        chi_so(dem["Chờ duyệt"], "Chờ duyệt", "canh" if dem["Chờ duyệt"] else ""),
        chi_so(dem["Duyệt"], "Đã duyệt, chờ lên lịch"),
        chi_so(dem["Đã lên lịch"], "Đã lên lịch đăng", "xanh" if dem["Đã lên lịch"] else ""),
        chi_so(dem["Lỗi"], "Lỗi", "do" if dem["Lỗi"] else ""),
    ])

    the = []
    for b in bai:
        ghi_chu = (f"<div class='note{' loi' if b['trang_thai'] == 'Lỗi' else ''}'>{_e(b['ghi_chu'])}</div>"
                   if b.get("ghi_chu") and b["trang_thai"] != "Đã lên lịch" else "")
        lop = _LOP.get(b["trang_thai"], "s-moi")
        xem_anh = f"<a href='{_e(b['media'])}' target='_blank' rel='noopener'>Mở ảnh/video</a>" if b.get("media") else ""
        the.append(
            f"<article class='post'><div class='thumb'>{_anh_nho(b.get('media'))}</div><div class='pb'>"
            f"<div class='row'><span class='when'>{_e(_ngay(b['ngay']))} · {_e(b['gio'])}</span>"
            f"<span class='badge {lop}'>{_e(b['trang_thai'] or 'Chưa có')}</span></div>"
            f"<div class='loai'>{_e(b['loai'])}</div><div class='pv'>{_e(b['noi_dung'])}</div>{ghi_chu}"
            f"<details><summary>Xem cả bài</summary><div class='body'>{_e(b['noi_dung'])}</div>"
            f"<div style='margin-top:6px;font-size:13px'>{xem_anh}</div></details></div></article>")
    ds_html = ("<div class='grid'>" + "".join(the) + "</div>" if the else
               "<div class='empty'>Chưa có bài nào. Chạy workflow <b>Tạo bài cả tuần</b> để AI viết bài mới.</div>")

    kho_html = ""
    if d["kho"]:
        toi_da = max([k["so_file"] for k in d["kho"]] + [1])
        dong = []
        for k in d["kho"]:
            zero = k["so_file"] == 0 and not k["ten"].startswith("_")
            rong = round(100 * k["so_file"] / toi_da)
            dong.append(f"<div class='k'><code>{_e(k['ten'])}</code><div class='track'><div class='fill' style='width:{rong}%'>"
                        f"</div></div><span class='n{' zero' if zero else ''}'>{k['so_file']}</span></div>")
        kho_html = ("<h2>Kho ảnh/video <small>số file mỗi thư mục</small></h2><div class='kho'>" + "".join(dong) + "</div>")

    tuong_tac = ""
    b = d.get("bot")
    if b:
        tuong_tac = ("<h2>Tương tác với khách <small>từ lúc bot khởi động " + _e(b.get("khoi_dong", "")) + "</small></h2>"
                     "<div class='stats'>" + "".join([
                         chi_so(b.get("tin_nhan_khach", 0), "Tin nhắn khách gửi"),
                         chi_so(b.get("da_gui_tra_loi", 0), "Bot đã trả lời", "xanh" if b.get("da_gui_tra_loi") else ""),
                         chi_so(b.get("binh_luan", 0), "Bình luận"),
                         chi_so(b.get("bo_qua_im_lang", 0), "Nhân viên đang xử lý"),
                         chi_so(b.get("loi", 0), "Lỗi", "do" if b.get("loi") else "")]) + "</div>"
                     "<p class='muted' style='margin:8px 2px 0;font-size:12.5px;color:var(--muted)'>Số liệu tính từ lần bot "
                     "khởi động gần nhất, nên sẽ về 0 sau mỗi lần máy chủ cập nhật.</p>")

    khach_html = ""
    if d.get("khach") is not None:
        dong = []
        for r in d["khach"]:
            ten = _e(r[3]) or "—"
            dong.append(f"<tr><td>{_e(r[0])}</td><td>{ten}</td><td class='sdt'>{_e(r[4]) or '—'}</td>"
                        f"<td>{_e(r[5])}</td><td>{_e(r[6])}</td><td><span class='badge s-cho'>{_e(r[7]) or 'Mới'}</span></td></tr>")
        khach_html = ("<h2>Khách quan tâm <small>để lại số điện thoại hoặc cần nhân viên</small></h2><div class='kh'>"
                      + ("<div class='scroll'><table><thead><tr><th>Thời gian</th><th>Tên</th><th>SĐT</th><th>Nhu cầu</th>"
                         "<th>Lý do chuyển</th><th>Trạng thái</th></tr></thead><tbody>" + "".join(dong) + "</tbody></table></div>"
                         if dong else "<div class='canhbao' style='border:0'>Chưa có khách nào để lại thông tin.</div>")
                      + "</div>")
    elif d.get("khach_loi"):
        khach_html = ("<h2>Khách quan tâm</h2><div class='canhbao'>Chưa đọc được tab <b>Khách hàng</b> trong Google Sheet ("
                      + _e(d["khach_loi"]) + ").</div>")

    chat_html = ""
    if d.get("hoi_thoai"):
        the_chat = []
        for c in d["hoi_thoai"]:
            tin = "".join(f"<div class='msg {t['tu']}'>{_e(t['noi_dung'])}</div>" for t in c["tin"])
            the_chat.append(f"<article class='chat'><h3>{_e(c['ten'])}<small>{_e(_gio_vn(c['luc']))}</small></h3>{tin}</article>")
        chat_html = "<h2>Tin nhắn gần đây <small>đọc trực tiếp từ Messenger</small></h2><div class='chats'>" + "".join(the_chat) + "</div>"
    elif d.get("hoi_thoai_loi"):
        chat_html = ("<h2>Tin nhắn gần đây</h2><div class='canhbao'>Chưa đọc được tin nhắn từ Messenger: "
                     + _e(d["hoi_thoai_loi"]) + "<br>Nếu báo thiếu quyền thì cần chờ Meta duyệt đơn xét duyệt.</div>")
    elif d.get("hoi_thoai") == []:
        chat_html = "<h2>Tin nhắn gần đây</h2><div class='canhbao'>Chưa có cuộc trò chuyện nào.</div>"

    che_do = {True: "Duyệt tay: bật", False: "Tự lên lịch", None: ""}[d.get("che_do_duyet")]
    ten_page = _e(d.get("page")) or "Fanpage"
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Golden Lion Fanpage</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;650;700;800&display=swap">
<style>{CSS}</style></head><body>
<div class="brand"><div class="in"><div class="logo"><div class="mark">GL</div>
<div><h1>Bảng điều khiển {ten_page}</h1><div class="sub">Golden Lion · Sư Tử Vàng</div></div></div>
<div class="live"><span><i class="dot"></i>Đang chạy</span><span class="pill">Cập nhật {_e(d['cap_nhat'])}</span>
{f'<span class="pill">{che_do}</span>' if che_do else ''}</div></div></div>
<div class="wrap">
<div class="stats">{stats}</div>{todo}
{tuong_tac}{khach_html}{chat_html}
<h2>Lịch bài đăng <small>{len(bai)} bài</small></h2>{ds_html}{kho_html}
<p class="foot">Trang này chỉ để xem, tự cập nhật mỗi lần tải lại. Muốn sửa hoặc duyệt bài, làm trong Google Sheet.</p>
</div></body></html>"""


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
