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
*{box-sizing:border-box}[hidden]{display:none!important}
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
.post{background:var(--card);border:1px solid var(--line);border-radius:14px;display:grid;grid-template-columns:168px minmax(0,1fr);
overflow:hidden;box-shadow:var(--shadow)}
.thumb{background:var(--bar-bg);display:grid;place-items:center;color:var(--muted);font-size:12px;text-align:center;padding:6px;
min-height:96px;position:relative}
.thumb img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.pb{padding:12px 14px;min-width:0;display:flex;flex-direction:column;gap:6px}
.row{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;justify-content:space-between}
.when{font-weight:700;font-variant-numeric:tabular-nums}.loai{font-size:13px;color:var(--muted)}.dich{font-size:12.5px;color:var(--muted)}.dich b{color:var(--ink);font-weight:650}
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
.chats{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);max-height:360px;overflow-y:auto}
.chat{border-bottom:1px solid var(--line)}.chat:last-child{border-bottom:0}
.chat summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:minmax(0,170px) minmax(0,1fr) auto;gap:6px 12px;
align-items:baseline;padding:10px 14px;width:auto;color:var(--ink);font-weight:500}
.chat summary::-webkit-details-marker{display:none}.chat summary:hover{background:var(--bg)}
.chat summary b{font-weight:650;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.chat summary .cuoi{color:var(--muted);font-size:13.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.chat summary small{color:var(--muted);font-size:12px;white-space:nowrap}
.chat[open] summary{background:var(--bg)}.chat .noidung{padding:4px 14px 12px}
@media (max-width:520px){.chat summary{grid-template-columns:minmax(0,1fr) auto}.chat summary .cuoi{grid-column:1/-1;order:3}}
.msg{max-width:88%;padding:6px 10px;border-radius:12px;font-size:13.5px;margin:4px 0;overflow-wrap:anywhere;white-space:pre-wrap}
.msg.khach{background:var(--bar-bg);border-bottom-left-radius:4px}
.msg.page{background:var(--gold-bg);color:var(--ink);margin-left:auto;border-bottom-right-radius:4px}
.msg.page::before{content:"Page/bot · ";font-size:11px;color:var(--gold-ink);font-weight:650}
.canhbao{background:var(--card);border:1px dashed var(--line);border-radius:14px;padding:14px 16px;color:var(--muted);font-size:14px}
.tabs{max-width:1080px;margin:0 auto;padding:0 12px;display:flex;gap:2px;overflow-x:auto;scrollbar-width:none}
.tabs::-webkit-scrollbar{display:none}
.tab{font:inherit;font-size:14px;font-weight:600;color:color-mix(in srgb,var(--bg) 72%,transparent);background:none;border:0;
padding:10px 14px;border-bottom:3px solid transparent;cursor:pointer;white-space:nowrap;display:flex;gap:7px;align-items:center}
.tab:hover{color:var(--bg)}.tab[aria-selected="true"]{color:var(--bg);border-bottom-color:var(--gold)}
.tab:focus-visible{outline:2px solid var(--gold);outline-offset:-2px;border-radius:6px}
.dau{font-style:normal;font-size:11.5px;font-weight:700;background:var(--gold);color:#1a1200;border-radius:99px;padding:0 7px;line-height:18px}
.brand .in{padding-bottom:6px}.panel h2:first-child{margin-top:22px}.panel>.stats:first-child{margin-top:22px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 14px}
.chip{font:inherit;font-size:13px;font-weight:600;border:1px solid var(--line);background:var(--card);color:var(--ink);
border-radius:99px;padding:5px 12px;cursor:pointer;display:flex;gap:6px;align-items:center}
.chip i{font-style:normal;color:var(--muted);font-variant-numeric:tabular-nums}
.chip.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}.chip.on i{color:inherit;opacity:.8}
.chip:focus-visible,.cl:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
.ln{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center;padding:10px 0;border-bottom:1px solid var(--line)}
.ln:last-child{border-bottom:0}.ln .loai{flex:1;min-width:120px}
.split{display:grid;grid-template-columns:minmax(220px,340px) minmax(0,1fr);gap:12px;align-items:start}
.cls{background:var(--card);border:1px solid var(--line);border-radius:14px;max-height:520px;overflow-y:auto;box-shadow:var(--shadow)}
.cl{display:block;width:100%;text-align:left;font:inherit;background:none;border:0;border-bottom:1px solid var(--line);
padding:10px 14px;cursor:pointer;color:var(--ink)}.cl:last-child{border-bottom:0}.cl:hover{background:var(--bg)}
.cl.on{background:var(--gold-bg)}.cl .r1{display:flex;justify-content:space-between;gap:8px}.cl small{color:var(--muted);font-size:12px}
.cl .cuoi{display:block;color:var(--muted);font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cdt{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;min-height:200px;box-shadow:var(--shadow)}
.cdt h3{margin:0 0 8px;font-size:15px;display:flex;justify-content:space-between;gap:8px}.cdt h3 small{font-weight:500;color:var(--muted);font-size:12px}
@media (max-width:700px){.split{grid-template-columns:1fr}.cls{max-height:240px}}
.tcol{display:flex;flex-direction:column;gap:8px;padding:8px;background:var(--bar-bg);min-width:0}
.thumb{border-radius:10px;overflow:hidden;aspect-ratio:4/3;min-height:0}.vd{position:absolute;right:6px;bottom:6px;background:rgba(0,0,0,.72);
color:#fff;font-size:11px;font-weight:700;border-radius:6px;padding:1px 7px;letter-spacing:.04em}
.thumb.phong{cursor:zoom-in}.thumb.phong:hover{filter:brightness(1.05)}.thumb.phong:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
dialog#xem-anh{border:1px solid var(--line);border-radius:16px;padding:0;width:min(1100px,calc(100vw - 24px));max-height:calc(100vh - 24px);
background:var(--card);color:var(--ink);box-shadow:0 20px 60px rgba(0,0,0,.35)}dialog#xem-anh::backdrop{background:rgba(10,14,20,.6)}
.xa{display:flex;flex-direction:column;max-height:calc(100vh - 24px)}.xa header{padding:12px 18px;border-bottom:1px solid var(--line);
display:flex;justify-content:space-between;align-items:center;gap:10px}.xa h3{margin:0;font-size:16px}
.xa-than{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:0;overflow:hidden;min-height:0}
.xa-anh{background:var(--bar-bg);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;padding:14px;min-height:260px}
.xa-anh img{max-width:100%;max-height:calc(100vh - 170px);object-fit:contain;border-radius:10px}
.xa-ct{font-size:13px;color:var(--muted);text-align:center}.xa-chu{padding:16px 20px;overflow-y:auto;max-height:calc(100vh - 100px)}
.xa-van{white-space:pre-wrap;overflow-wrap:anywhere;font-size:15px;line-height:1.6;margin-top:6px}.xa .ghi{color:var(--muted);font-size:13px;font-weight:600}
@media (max-width:760px){.xa-than{grid-template-columns:1fr;overflow-y:auto}.xa-chu{max-height:none}.xa-anh img{max-height:50vh}}
.ghi-nho{font-size:12px;color:var(--muted);line-height:1.35;padding:0 2px}.tcol .bt{width:100%;padding:5px 6px;font-size:12.5px}
dialog#hop-anh{border:1px solid var(--line);border-radius:16px;padding:0;width:min(920px,calc(100vw - 24px));max-height:calc(100vh - 32px);
background:var(--card);color:var(--ink);box-shadow:0 20px 60px rgba(0,0,0,.35)}
dialog#hop-anh::backdrop{background:rgba(10,14,20,.55)}
.hop{display:flex;flex-direction:column;max-height:calc(100vh - 32px)}.hop header{padding:14px 18px;border-bottom:1px solid var(--line);
display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;justify-content:space-between}
.hop h3{margin:0;font-size:16px}.hop .luoi{padding:14px 18px;overflow-y:auto;display:grid;gap:10px;
grid-template-columns:repeat(auto-fill,minmax(130px,1fr))}
.hop footer{padding:12px 18px;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px;justify-content:space-between;align-items:center}
.o{position:relative;border:2px solid transparent;border-radius:12px;overflow:hidden;cursor:pointer;aspect-ratio:1;background:var(--bar-bg);
padding:0;display:block;width:100%}.o img{width:100%;height:100%;object-fit:cover;display:block}.o.on{border-color:var(--gold);box-shadow:0 0 0 2px var(--gold)}
.o .tn{position:absolute;left:0;right:0;bottom:0;background:rgba(0,0,0,.6);color:#fff;font-size:11px;padding:2px 6px;overflow:hidden;
text-overflow:ellipsis;white-space:nowrap;text-align:left}.hop select{font:inherit;font-size:14px;border:1px solid var(--line);border-radius:8px;
background:var(--card);color:var(--ink);padding:5px 8px}.hop .ghi{color:var(--muted);font-size:13px}
.ht{display:flex;gap:12px;align-items:flex-start;padding:12px 0;border-bottom:1px solid var(--line)}.ht:last-child{border-bottom:0}
.ht .cham{width:10px;height:10px;border-radius:50%;margin-top:6px;flex:none;background:var(--ok)}.ht.hong .cham{background:var(--loi)}
.ht .ct{font-size:13.5px;color:var(--muted);overflow-wrap:anywhere}.ht.hong .ct{color:var(--loi)}.ht .hd{font-size:13px;margin-top:3px}
.acts{display:flex;flex-wrap:wrap;gap:8px;margin-top:2px}
button.bt{font:inherit;font-size:13px;font-weight:650;border:1px solid var(--line);background:var(--card);color:var(--ink);
border-radius:9px;padding:5px 12px;cursor:pointer}button.bt:hover{background:var(--bg)}
button.bt.chinh{background:var(--gold);border-color:var(--gold);color:#1a1200}button.bt.chinh:hover{filter:brightness(.95)}
button.bt:disabled{opacity:.55;cursor:wait}button.bt:focus-visible,select.chon:focus-visible,textarea.sua:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
textarea.sua{width:100%;min-height:150px;margin-top:6px;padding:10px 12px;border:1px solid var(--line);border-radius:10px;
background:var(--bg);color:var(--ink);font:14px/1.5 inherit;resize:vertical}
select.chon{font:inherit;font-size:13px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);padding:3px 6px}
#toast{position:fixed;left:50%;bottom:calc(20px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);background:var(--ink);
color:var(--bg);padding:9px 16px;border-radius:10px;font-size:14px;box-shadow:0 6px 20px rgba(0,0,0,.25);z-index:9;max-width:90vw}
#toast.loi{background:var(--loi);color:#fff}
.foot{margin-top:28px;font-size:13px;color:var(--muted)}
.empty{background:var(--card);border:1px dashed var(--line);border-radius:14px;padding:22px;color:var(--muted)}
@media (max-width:520px){.post{grid-template-columns:112px minmax(0,1fr)}.k{grid-template-columns:1fr 36px}.k .track{grid-column:1/-1;order:3}}
"""

JS = r"""
<div id="toast" hidden></div>
<script>
(function(){
  var toast=document.getElementById('toast'),t0;
  function bao(m,loi){toast.textContent=m;toast.className=loi?'loi':'';toast.hidden=false;clearTimeout(t0);t0=setTimeout(function(){toast.hidden=true},3500)}
  function gui(lenh,nut,sau){
    if(nut)nut.disabled=true;
    fetch('/api/thao-tac',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-GL':'1'},body:JSON.stringify(lenh)})
      .then(function(r){return r.json().then(function(j){return{ok:r.ok,j:j}})})
      .then(function(x){
        if(!x.ok){bao(x.j.loi||'Không lưu được',true);if(nut)nut.disabled=false;return}
        if(x.j.thong_bao){bao(x.j.thong_bao);if(nut)nut.disabled=false;return}
        if(sau){bao('Đã đổi');sau();if(nut)nut.disabled=false;return}
        bao('Đã lưu');setTimeout(function(){location.reload()},700)})
      .catch(function(){bao('Mất kết nối, thử lại sau',true);if(nut)nut.disabled=false});
  }


  var xa=document.getElementById('xem-anh');
  if(xa){
    var xi=document.getElementById('xa-img'),xct=document.getElementById('xa-ct'),xc=document.getElementById('xa-chu');
    function moXem(t){
      var card=t.closest('.post'),f=t.dataset.fid,vd=t.dataset.video==='1';
      xi.src='/api/anh/'+f+'?s=1400';xi.hidden=false;xi.onerror=function(){xi.hidden=true;xct.textContent='Chưa xem trước được ảnh này.'};
      xct.innerHTML='';
      var a=document.createElement('a');a.href='https://drive.google.com/file/d/'+f+'/view';a.target='_blank';a.rel='noopener';
      a.textContent=vd?'Mở video trên Google Drive để xem đầy đủ':'Mở ảnh gốc trên Google Drive';xct.appendChild(a);
      var tx=card?card.querySelector('.pv-full'):null;xc.textContent=tx?tx.textContent:'';
      xa.showModal();
    }
    document.addEventListener('click',function(e){var t=e.target.closest('.thumb.phong');if(t)moXem(t)});
    document.addEventListener('keydown',function(e){if((e.key==='Enter'||e.key===' ')&&e.target.matches&&e.target.matches('.thumb.phong')){e.preventDefault();moXem(e.target)}});
    document.getElementById('xa-dong').addEventListener('click',function(){xa.close()});
    xa.addEventListener('click',function(e){if(e.target===xa)xa.close()});
  }
  var hop=document.getElementById('hop-anh');
  if(hop){
    var luoi=document.getElementById('hop-luoi'),chon=document.getElementById('hop-thu-muc'),ghi=document.getElementById('hop-ghi'),
        dung=document.getElementById('hop-dung'),maBai=null,fileId=null;
    function taiThuMuc(){
      luoi.textContent='Đang tải…';fileId=null;dung.disabled=true;
      fetch('/api/kho/'+encodeURIComponent(chon.value),{credentials:'same-origin'}).then(function(r){return r.json()}).then(function(ds){
        luoi.textContent='';
        if(!ds.length||ds.loi){ghi.textContent=ds.loi||'Thư mục này chưa có ảnh/video.';return}
        ghi.textContent=ds.length+' file. Bấm một ảnh để chọn.';
        ds.forEach(function(f){
          var o=document.createElement('button');o.type='button';o.className='o';o.title=f.ten;
          var im=document.createElement('img');im.loading='lazy';im.alt=f.ten;im.src='/api/anh/'+f.id+'?s=320';im.onerror=function(){im.remove()};
          var tn=document.createElement('span');tn.className='tn';tn.textContent=(f.video?'VIDEO · ':'')+f.ten;
          o.appendChild(im);o.appendChild(tn);
          o.addEventListener('click',function(){
            [].forEach.call(luoi.children,function(x){x.classList.remove('on')});o.classList.add('on');fileId=f.id;dung.disabled=false});
          luoi.appendChild(o)});
      }).catch(function(){luoi.textContent='';ghi.textContent='Không tải được danh sách ảnh.'});
    }
    document.addEventListener('click',function(e){
      var b=e.target.closest('.doi-anh');if(!b)return;
      maBai=b.dataset.ma;hop.showModal();taiThuMuc();
    });
    chon.addEventListener('change',taiThuMuc);
    document.getElementById('hop-dong').addEventListener('click',function(){hop.close()});
    function capNhatKhung(fid){
      var nut=document.querySelector('.doi-anh[data-ma="'+maBai+'"]'),card=nut&&nut.closest('.post'),th=card&&card.querySelector('.thumb');
      if(th){
        th.textContent='';
        if(fid){var im=document.createElement('img');im.alt='Ảnh sẽ đăng kèm bài';im.src='/api/anh/'+fid+'?s=400';th.appendChild(im);
          th.dataset.fid=fid;th.dataset.video='0';th.classList.add('phong');th.setAttribute('role','button');th.tabIndex=0}
        else{th.innerHTML='<span>Chưa có ảnh/video.<br>Đăng chỉ chữ.</span>';th.classList.remove('phong');delete th.dataset.fid}
      }
      hop.close();
    }
    dung.addEventListener('click',function(){if(fileId){var f=fileId;gui({hanh:'bai_media',ma_bai:maBai,file_id:f},dung,function(){capNhatKhung(f)})}});
    document.getElementById('hop-bo').addEventListener('click',function(){gui({hanh:'bai_media',ma_bai:maBai,file_id:''},this,function(){capNhatKhung('')})});
  }
  document.addEventListener('click',function(e){
    var b=e.target.closest('button[data-hanh]');if(!b)return;
    var h=b.dataset.hanh;
    if(h==='email_thu')gui({hanh:h},b);
    else if(h==='bai_trang_thai')gui({hanh:h,ma_bai:b.dataset.ma,trang_thai:b.dataset.tt},b);
    else if(h==='bai_noi_dung'){var ta=document.getElementById('nd-'+b.dataset.ma);gui({hanh:h,ma_bai:b.dataset.ma,noi_dung:ta?ta.value:''},b)}
  });
  document.addEventListener('change',function(e){
    var s=e.target.closest('select[data-hanh="khach_trang_thai"]');if(!s)return;
    gui({hanh:'khach_trang_thai',dong:s.dataset.dong,trang_thai:s.value},null);
  });
})();
</script>"""


JS_TAB = r"""
<script>
(function(){
  var tabs=[].slice.call(document.querySelectorAll('.tab')),panels=[].slice.call(document.querySelectorAll('.panel'));
  function mo(k,doi){
    if(!document.getElementById('p-'+k))k='tong-quan';
    tabs.forEach(function(t){t.setAttribute('aria-selected',t.dataset.tab===k?'true':'false');t.tabIndex=t.dataset.tab===k?0:-1});
    panels.forEach(function(p){p.hidden=p.id!=='p-'+k});
    if(doi){try{history.replaceState(null,'','#'+k)}catch(e){}}
  }
  tabs.forEach(function(t,i){
    t.addEventListener('click',function(){mo(t.dataset.tab,true)});
    t.addEventListener('keydown',function(e){
      var j=e.key==='ArrowRight'?i+1:e.key==='ArrowLeft'?i-1:-1;if(j<0)return;
      j=(j+tabs.length)%tabs.length;tabs[j].focus();mo(tabs[j].dataset.tab,true);e.preventDefault()});
  });
  mo((location.hash||'').slice(1)||'tong-quan',false);
  window.addEventListener('hashchange',function(){mo((location.hash||'').slice(1)||'tong-quan',false)});
  document.addEventListener('click',function(e){
    var c=e.target.closest('.chip[data-loc]');
    if(c){
      document.querySelectorAll('.chip').forEach(function(x){x.classList.toggle('on',x===c)});
      document.querySelectorAll('.post').forEach(function(p){p.hidden=c.dataset.loc!=='Tất cả'&&p.dataset.tt!==c.dataset.loc});
    }
    var l=e.target.closest('.cl[data-i]');
    if(l){
      document.querySelectorAll('.cl').forEach(function(x){x.classList.toggle('on',x===l)});
      document.querySelectorAll('.cr').forEach(function(x){x.hidden=x.dataset.i!==l.dataset.i});
    }
  });
})();
</script>"""

_LOP = {"Chờ duyệt": "s-cho", "Duyệt": "s-duyet", "Đã lên lịch": "s-ok", "Lỗi": "s-loi", "Bỏ": "s-bo"}
_LOP_KHACH = {"Mới": "s-cho", "Đã gọi": "s-duyet", "Báo giá": "s-duyet", "Chốt đơn": "s-ok", "Không mua": "s-bo"}
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


def _anh_nho(link: str, qua_may_chu: bool = False) -> str:
    """Ảnh xem trước. Trên bảng điều khiển trực tiếp lấy qua máy chủ (không cần đăng nhập Google);
    bản xuất tĩnh dùng ảnh nhỏ của Drive (hiện khi người xem có quyền xem file)."""
    m = _DRIVE_ID.search(link or "")
    if not m:
        return "<span>Chưa có ảnh/video.<br>Đăng chỉ chữ.</span>"
    nguon = (f"/api/anh/{m.group(1)}" if qua_may_chu
             else f"https://drive.google.com/thumbnail?id={m.group(1)}&sz=w400")
    return (f"<span>Đang tải ảnh…</span><img loading='lazy' alt='Ảnh hoặc video sẽ đăng kèm bài' referrerpolicy='no-referrer' "
            f"src='{nguon}' onerror=\"this.previousElementSibling.textContent='Chưa xem trước được. Mở bài trên Facebook để xem ảnh đã gắn.';this.remove()\">")


_DUOI_VIDEO = re.compile(r"\.(mp4|mov|m4v|avi|mkv|webm)\b", re.IGNORECASE)


def dung_html(d: dict) -> str:
    """d: cap_nhat(str), page(str), che_do_duyet(bool|None), sheet_url(str), bai(list), kho(list)."""
    bai = sorted(d["bai"], key=lambda b: (b["ngay"], b["gio"]))
    dem = Counter(b["trang_thai"] for b in bai)
    kho_trong = [k["ten"] for k in d["kho"] if k["so_file"] == 0 and not k["ten"].startswith("_")]
    cho_phan_loai = next((k["so_file"] for k in d["kho"] if k["ten"] == "_chua-phan-loai"), 0)
    xem_lai = next((k["so_file"] for k in d["kho"] if k["ten"] == "_can-xem-lai"), 0)

    viec = []
    sua_ngay = bool(d.get("sua_duoc"))
    sheet = (f'<a href="{_e(d["sheet_url"])}" target="_blank" rel="noopener">mở Google Sheet</a>'
             if d.get("sheet_url") else "Google Sheet")
    if dem["Chờ duyệt"]:
        viec.append(f"<b>{dem['Chờ duyệt']}</b> bài đang chờ duyệt: bấm <b>Xem và sửa bài</b> để chỉnh chữ nếu cần, rồi bấm <b>Duyệt bài</b> ngay ở mục Lịch bài đăng bên dưới."
                    if sua_ngay else f"<b>{dem['Chờ duyệt']}</b> bài đang chờ duyệt: {sheet}, sửa nội dung nếu cần rồi chọn trạng thái <b>Duyệt</b>.")
    if dem["Lỗi"]:
        viec.append(f"<b>{dem['Lỗi']}</b> bài bị lỗi: xem dòng lỗi màu đỏ trong thẻ bài, sửa rồi bấm <b>Duyệt lại</b>."
                    if sua_ngay else f"<b>{dem['Lỗi']}</b> bài bị lỗi: xem cột Ghi chú trong {sheet}.")
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

    ten_page = _e(d.get("page")) or "Fanpage"

    def link_fb(b):
        if b.get("facebook_id"):
            return (f" · <a href='https://www.facebook.com/{_e(b['facebook_id'])}' target='_blank' rel='noopener'>"
                    "Xem trên Facebook</a>")
        return ""

    sua = bool(d.get("sua_duoc"))

    def nut(ma, tt, nhan, chinh=False):
        return (f"<button type='button' class='bt{' chinh' if chinh else ''}' data-hanh='bai_trang_thai' "
                f"data-ma='{_e(ma)}' data-tt='{tt}'>{nhan}</button>")

    def hanh_dong_bai(b):
        if not sua:
            return ""
        tt, ma = b["trang_thai"], b["ma_bai"]
        if tt == "Chờ duyệt":
            nut_ = nut(ma, "Duyệt", "Duyệt bài", True) + nut(ma, "Bỏ", "Bỏ bài")
        elif tt == "Duyệt":
            nut_ = nut(ma, "Chờ duyệt", "Đưa về chờ duyệt") + nut(ma, "Bỏ", "Bỏ bài")
        elif tt in ("Bỏ", "Lỗi"):
            nut_ = nut(ma, "Duyệt", "Duyệt lại" if tt == "Lỗi" else "Khôi phục và duyệt", True)
        else:
            return ""
        return f"<div class='acts'>{nut_}</div>"

    def sua_noi_dung(b):
        if not sua or b["trang_thai"] not in ("Chờ duyệt", "Duyệt", "Bỏ", "Lỗi"):
            return ""
        return (f"<textarea class='sua' id='nd-{_e(b['ma_bai'])}'>{_e(b['noi_dung'])}</textarea>"
                f"<div class='acts'><button type='button' class='bt' data-hanh='bai_noi_dung' data-ma='{_e(b['ma_bai'])}'>"
                "Lưu nội dung</button></div>")

    def phong_attr(b):
        m = _DRIVE_ID.search(b.get("media") or "")
        if not (sua and m):
            return ""
        return (f"data-fid='{m.group(1)}' data-video='{1 if _DUOI_VIDEO.search(b.get('ghi_chu') or '') else 0}' "
                "role='button' tabindex='0' title='Bấm để xem ảnh to cạnh nội dung bài'")

    def la_video(b):
        return "<span class='vd'>VIDEO</span>" if _DUOI_VIDEO.search(b.get("ghi_chu") or "") else ""

    def nut_doi_anh(b):
        if sua and b["trang_thai"] == "Đã lên lịch":
            return "<div class='ghi-nho'>Đã lên lịch. Muốn đổi ảnh, sửa trong Meta Business Suite.</div>"
        if not (sua and d.get("kho") and b["trang_thai"] in ("Chờ duyệt", "Duyệt", "Lỗi", "Bỏ")):
            return ""
        return f"<button type='button' class='bt doi-anh' data-ma='{_e(b['ma_bai'])}'>Đổi ảnh/video</button>"

    the = []
    for b in bai:
        ghi_chu = (f"<div class='note{' loi' if b['trang_thai'] == 'Lỗi' else ''}'>{_e(b['ghi_chu'])}</div>"
                   if b.get("ghi_chu") and b["trang_thai"] != "Đã lên lịch" else "")
        lop = _LOP.get(b["trang_thai"], "s-moi")
        xem_anh = f"<a href='{_e(b['media'])}' target='_blank' rel='noopener'>Mở ảnh/video</a>" if b.get("media") else ""
        the.append(
            f"<article class='post' data-tt='{_e(b['trang_thai'] or 'Chưa có')}'><div class='tcol'><div class='thumb{' phong' if sua and _DRIVE_ID.search(b.get('media') or '') else ''}' "
            f"{phong_attr(b)}>{_anh_nho(b.get('media'), sua)}{la_video(b)}</div>{nut_doi_anh(b)}</div>"
            f"<div class='pb'>"
            f"<div class='row'><span class='when'>{_e(_ngay(b['ngay']))} · {_e(b['gio'])}</span>"
            f"<span class='badge {lop}'>{_e(b['trang_thai'] or 'Chưa có')}</span></div>"
            f"<div class='loai'>{_e(b['loai'])}</div>"
            f"<div class='dich'>Đăng lên Fanpage <b>{ten_page}</b>{link_fb(b)}</div><div class='pv'>{_e(b['noi_dung'])}</div><div class='pv-full' hidden>{_e(b['noi_dung'])}</div>{ghi_chu}{hanh_dong_bai(b)}"
            f"<details><summary>{'Xem và sửa bài' if sua_noi_dung(b) else 'Xem cả bài'}</summary>"
            f"{sua_noi_dung(b) or ('<div class=body>' + _e(b['noi_dung']) + '</div>')}"
            f"<div style='margin-top:6px;font-size:13px'>{xem_anh}</div></details></div></article>")
    loc = "".join(f"<button type='button' class='chip{' on' if t == 'Tất cả' else ''}' data-loc='{t}'>{t}"
                  f"<i>{len(bai) if t == 'Tất cả' else dem.get(t, 0)}</i></button>"
                  for t in ("Tất cả", "Chờ duyệt", "Duyệt", "Đã lên lịch", "Lỗi", "Bỏ"))
    ds_html = ((f"<div class='chips' role='group' aria-label='Lọc bài theo trạng thái'>{loc}</div>"
                "<div class='grid'>" + "".join(the) + "</div>") if the else
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

    def trang_thai_khach(r):
        hien = (r[7] or "Mới").strip()
        if sua and len(r) > 9:
            tuy = "".join(f"<option{' selected' if t == hien else ''}>{t}</option>"
                          for t in ("Mới", "Đã gọi", "Báo giá", "Chốt đơn", "Không mua"))
            return f"<select class='chon' data-hanh='khach_trang_thai' data-dong='{int(r[9])}' aria-label='Trạng thái khách'>{tuy}</select>"
        return f"<span class='badge {_LOP_KHACH.get(hien, 's-moi')}'>{_e(hien)}</span>"

    khach_html = ""
    if d.get("khach") is not None:
        dong = []
        for r in d["khach"]:
            ten = _e(r[3]) or "—"
            dong.append(f"<tr><td>{_e(r[0])}</td><td>{ten}</td><td class='sdt'>{_e(r[4]) or '—'}</td>"
                        f"<td>{_e(r[5])}</td><td>{_e(r[6])}</td><td>{trang_thai_khach(r)}</td></tr>")
        dem_kh = Counter((r[7] or "Mới").strip() for r in d["khach"])
        phieu = "".join(f"<span class='badge {_LOP_KHACH.get(t, 's-moi')}'>{t}: {dem_kh.get(t, 0)}</span> "
                        for t in ("Mới", "Đã gọi", "Báo giá", "Chốt đơn", "Không mua"))
        khach_html = ("<h2>Khách quan tâm <small>để lại số điện thoại hoặc cần nhân viên</small></h2>"
                      f"<div style='margin:-4px 0 10px;display:flex;flex-wrap:wrap;gap:6px'>{phieu}</div><div class='kh'>"
                      + ("<div class='scroll'><table><thead><tr><th>Thời gian</th><th>Tên</th><th>SĐT</th><th>Nhu cầu</th>"
                         "<th>Lý do chuyển</th><th>Trạng thái</th></tr></thead><tbody>" + "".join(dong) + "</tbody></table></div>"
                         if dong else "<div class='canhbao' style='border:0'>Chưa có khách nào để lại thông tin.</div>")
                      + "</div>")
    elif d.get("khach_loi"):
        khach_html = ("<h2>Khách quan tâm</h2><div class='canhbao'>Chưa đọc được tab <b>Khách hàng</b> trong Google Sheet ("
                      + _e(d["khach_loi"]) + ").</div>")

    chat_html = ""
    if d.get("hoi_thoai"):
        ds_ten, ds_chat = [], []
        for i, c in enumerate(d["hoi_thoai"]):
            cuoi = c["tin"][-1] if c["tin"] else {"tu": "khach", "noi_dung": ""}
            ai = "Bot/Page: " if cuoi["tu"] == "page" else ""
            ds_ten.append(f"<button type='button' class='cl{' on' if i == 0 else ''}' data-i='{i}'><span class='r1'><b>{_e(c['ten'])}</b>"
                          f"<small>{_e(_gio_vn(c['luc']))}</small></span><span class='cuoi'>{ai}{_e(cuoi['noi_dung'])}</span></button>")
            tin = "".join(f"<div class='msg {t['tu']}'>{_e(t['noi_dung'])}</div>" for t in c["tin"])
            ds_chat.append(f"<div class='cr' data-i='{i}'{'' if i == 0 else ' hidden'}><h3>{_e(c['ten'])}"
                           f"<small>{_e(_gio_vn(c['luc']))}</small></h3>{tin}</div>")
        chat_html = ("<div class='split'><div class='cls' role='list'>" + "".join(ds_ten) + "</div><div class='cdt'>"
                     + "".join(ds_chat) + "</div></div>")
    elif d.get("hoi_thoai_loi"):
        chat_html = ("<div class='canhbao'>Chưa đọc được tin nhắn từ Messenger: " + _e(d["hoi_thoai_loi"])
                     + "<br>Nếu báo thiếu quyền thì cần chờ Meta duyệt đơn xét duyệt.</div>")
    elif d.get("hoi_thoai") == []:
        chat_html = "<div class='canhbao'>Chưa có cuộc trò chuyện nào.</div>"
    else:
        chat_html = "<div class='canhbao'>Chưa có dữ liệu tin nhắn.</div>"


    ten_kho = [k["ten"] for k in d.get("kho", [])]
    hop = ""
    if sua and ten_kho:
        tuy = "".join(f"<option value='{_e(t)}'>{_e(t)}</option>" for t in ten_kho)
        hop = (f"<dialog id='hop-anh' aria-labelledby='hop-tieu-de'><div class='hop'><header><h3 id='hop-tieu-de'>Chọn ảnh hoặc video cho bài</h3>"
               f"<label>Thư mục kho: <select id='hop-thu-muc'>{tuy}</select></label></header>"
               "<div class='luoi' id='hop-luoi'></div><footer><span class='ghi' id='hop-ghi'>Bấm một ảnh để chọn.</span>"
               "<span class='acts'><button type='button' class='bt' id='hop-bo'>Bỏ ảnh (chỉ đăng chữ)</button>"
               "<button type='button' class='bt' id='hop-dong'>Đóng</button>"
               "<button type='button' class='bt chinh' id='hop-dung' disabled>Dùng ảnh/video này</button></span></footer></div></dialog>")
    xem_to = ""
    if sua:
        xem_to = ("<dialog id='xem-anh' aria-labelledby='xa-tieu-de'><div class='xa'><header><h3 id='xa-tieu-de'>Ảnh/video và nội dung bài</h3>"
                  "<button type='button' class='bt' id='xa-dong'>Đóng</button></header><div class='xa-than'>"
                  "<div class='xa-anh'><img id='xa-img' alt='Ảnh hoặc video sẽ đăng kèm bài'><div class='xa-ct' id='xa-ct'></div></div>"
                  "<div class='xa-chu'><div class='ghi'>Nội dung bài sẽ đăng</div><div id='xa-chu' class='xa-van'></div></div></div></div></dialog>")
    he_thong = d.get("he_thong") or []
    ht_hong = sum(1 for x in he_thong if not x["ok"])
    ht_html = ""
    if he_thong:
        dong_ht = "".join(
            f"<div class='ht {'ok' if x['ok'] else 'hong'}'><span class='cham'></span><div><b>{_e(x['ten'])}</b>"
            f"<div class='ct'>{_e(x['chi_tiet'])}</div>"
            f"{('<div class=hd>' + _e(x['huong_dan']) + '</div>') if x.get('huong_dan') else ''}"
            f"{('<div class=acts><button type=button class=bt data-hanh=email_thu>Gửi thư thử</button></div>') if sua and x.get('nut') == 'email_thu' else ''}"
            "</div></div>" for x in he_thong)
        ht_html = ("<h2>Tình trạng hệ thống <small>kiểm tra mỗi lần mở trang</small></h2>"
                   + (f"<div class='todo'><b class='t'>{ht_hong} bộ phận cần chú ý</b>Xem dòng màu đỏ bên dưới.</div>" if ht_hong
                      else "<div class='todo ok'><b class='t'>Mọi bộ phận đang chạy tốt</b></div>")
                   + "<div class='kho' style='margin-top:12px'>" + dong_ht + "</div>")
    che_do = {True: "Duyệt tay: bật", False: "Tự lên lịch", None: ""}[d.get("che_do_duyet")]
    sap_toi = [b for b in bai if b["trang_thai"] in ("Chờ duyệt", "Duyệt", "Đã lên lịch")][:4]
    sap_html = "".join(
        f"<div class='ln'><span class='when'>{_e(_ngay(b['ngay']))} · {_e(b['gio'])}</span><span class='loai'>{_e(b['loai'])}</span>"
        f"<span class='badge {_LOP.get(b['trang_thai'], 's-moi')}'>{_e(b['trang_thai'])}</span></div>" for b in sap_toi)
    sap_html = f"<h2>Bài sắp đăng</h2><div class='kho'>{sap_html}</div>" if sap_html else ""
    n_khach_moi = sum(1 for r in (d.get("khach") or []) if (r[7] or "Mới").strip() == "Mới")
    n_kho = cho_phan_loai + xem_lai
    tabs = [("tong-quan", "Tổng quan", 0), ("bai-dang", "Bài đăng", dem["Chờ duyệt"]),
            ("khach-hang", "Khách hàng", n_khach_moi), ("tin-nhan", "Tin nhắn", 0), ("kho-anh", "Kho ảnh", n_kho)] + ([("he-thong", "Hệ thống", ht_hong)] if he_thong else [])
    thanh_tab = "".join(
        f"<button type='button' role='tab' class='tab' id='t-{k}' data-tab='{k}' aria-controls='p-{k}'>{ten}"
        f"{f'<i class=dau>{n}</i>' if n else ''}</button>" for k, ten, n in tabs)
    noi_dung_tab = {
        "tong-quan": f"<div class='stats'>{stats}</div>{todo}{tuong_tac}{sap_html}",
        "bai-dang": f"<h2>Lịch bài đăng <small>{len(bai)} bài · đăng lên Fanpage {ten_page}</small></h2>{ds_html}",
        "khach-hang": khach_html or "<div class='canhbao'>Chưa có dữ liệu khách hàng.</div>",
        "tin-nhan": f"<h2>Tin nhắn gần đây <small>đọc trực tiếp từ Messenger, bấm một cuộc để xem</small></h2>{chat_html}",
        "he-thong": ht_html,
        "kho-anh": kho_html or ("<div class='canhbao'>Đang đếm ảnh trong kho, vài chục giây nữa sẽ có số liệu. Tải lại trang sau ít phút.</div>"
                                if d.get("kho_dang_dem") else
                                "<div class='canhbao'>Chưa có dữ liệu kho ảnh (cần cấu hình DRIVE_KHO_ID trên máy chủ).</div>"),
    }
    panels = "".join(f"<section class='panel' role='tabpanel' id='p-{k}' aria-labelledby='t-{k}' hidden>{noi_dung_tab[k]}</section>"
                     for k, _, _ in tabs)
    chu_cuoi = ("Duyệt bài xong, app tự lên lịch đăng trong vòng 1 giờ. Bài đã lên lịch thì sửa hoặc hủy trong Meta Business Suite."
                if sua else "Trang này chỉ để xem, tự cập nhật mỗi lần tải lại. Muốn sửa hoặc duyệt bài, làm trong Google Sheet.")
    js = JS_TAB + (JS if sua else "")
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Golden Lion Fanpage</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;650;700;800&display=swap">
<style>{CSS}</style></head><body>
<div class="brand"><div class="in"><div class="logo"><div class="mark">GL</div>
<div><h1>Bảng điều khiển {ten_page}</h1><div class="sub">Golden Lion · Sư Tử Vàng</div></div></div>
<div class="live"><span><i class="dot"></i>Đang chạy</span><span class="pill">Cập nhật {_e(d['cap_nhat'])}</span>
{f'<span class="pill">{che_do}</span>' if che_do else ''}</div></div>
<nav class="tabs" role="tablist" aria-label="Các mục">{thanh_tab}</nav></div>
<div class="wrap">{panels}<p class="foot">{chu_cuoi}</p></div>{hop}{xem_to}{js}</body></html>"""


def dem_kho(cfg, drive, kho_id: str) -> list[dict]:
    """Số file trong từng thư mục kho. Tốn nhiều lần gọi Drive nên nơi gọi nên nhớ kết quả vài chục phút."""
    from .kho_anh import KhoDrive

    if not kho_id:
        return []
    kho = KhoDrive(drive, kho_id)
    ten_thu_muc = sorted({n for n in _ten_thu_muc_kho(cfg)}) + ["_chua-phan-loai", "_can-xem-lai"]
    dem = []
    for ten in ten_thu_muc:
        tm = kho.id_thu_muc(ten)
        dem.append({"ten": ten, "so_file": len(kho.liet_ke_de_quy(tm)) if tm else 0})
    return dem


def thu_thap(cfg, drive, sheets, sheet_id: str, kho_id: str, ten_page: str = "", dem_kho_san=None) -> dict:
    """Gom dữ liệu thật từ Google Sheet và Drive. dem_kho_san: số file kho đã đếm sẵn (đỡ đếm lại)."""
    from .duyet_bai import SheetDuyet

    sheet = SheetDuyet(sheets, sheet_id)
    bai = [{"ma_bai": r.ma_bai, "ngay": r.ngay, "gio": r.gio, "loai": r.loai_bai, "noi_dung": r.noi_dung,
            "media": r.media, "trang_thai": r.trang_thai.strip(), "ghi_chu": r.ghi_chu, "facebook_id": r.facebook_id}
           for r in sheet.doc_tat_ca()]
    dem = dem_kho_san if dem_kho_san is not None else dem_kho(cfg, drive, kho_id)
    return {"cap_nhat": datetime.now(cfg.mui_gio).strftime("%H:%M %d/%m/%Y"), "page": ten_page,
            "che_do_duyet": sheet.che_do_duyet(cfg["che_do_duyet"]),
            "sheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}", "bai": bai, "kho": dem}


def _ten_thu_muc_kho(cfg):
    from .du_lieu import doc_du_lieu

    du_lieu = doc_du_lieu(cfg.file_du_lieu, cfg.get("cot_bo_qua"))
    tm = cfg["thu_muc"]
    return ([sp.thu_muc for sp in du_lieu.san_pham if sp.thu_muc] + [tm["anh_chung"], *tm["theo_nganh"].values(),
            "video-demo", "khach-hang", "nha-may"])
