CSS = r"""
*,*::before,*::after{box-sizing:border-box}
:root{
  --ink:#08080A; --ink-2:#101014; --ink-3:#17171D; --ink-4:#202028;
  --gold:#C9A961; --gold-2:#E6D3A3; --gold-dim:rgba(201,169,97,.14);
  --paper:#FBFAF8; --paper-2:#F2EFEA; --line-d:rgba(255,255,255,.10); --line-l:rgba(8,8,10,.10);
  --tx-d:#F7F6F4; --tx-dm:rgba(247,246,244,.66); --tx-l:#14141A; --tx-lm:rgba(20,20,26,.62);
  --ok:#3FA46A; --warn:#D08A3E; --live:#4ADE80;
  --r:14px; --r-lg:20px; --mx:1240px;
  --sh:0 4px 24px rgba(0,0,0,.10),0 1px 3px rgba(0,0,0,.06);
  --sh-lg:0 24px 70px rgba(0,0,0,.34);
  --ff:'Inter Tight',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;font-family:var(--ff);background:var(--paper);color:var(--tx-l);
  font-size:17px;line-height:1.62;-webkit-font-smoothing:antialiased;overflow-x:hidden}
img{max-width:100%;height:auto;display:block}
a{color:inherit}
h1,h2,h3,h4{margin:0;line-height:1.08;letter-spacing:-.022em;font-weight:600}
h1{font-size:clamp(2.35rem,5.4vw,4.35rem)}
h2{font-size:clamp(1.85rem,3.6vw,2.9rem)}
h3{font-size:clamp(1.12rem,1.7vw,1.4rem)}
p{margin:0 0 1.05em}
.wrap{max-width:var(--mx);margin:0 auto;padding:0 clamp(20px,5vw,52px)}
.narrow{max-width:820px}
.sr{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
.skip{position:absolute;left:-9999px;top:0;z-index:999;background:var(--gold);color:var(--ink);padding:12px 20px;font-weight:600}
.skip:focus{left:12px;top:12px}
.num{font-variant-numeric:tabular-nums;font-feature-settings:"tnum"}

/* ---------- eyebrow / section head ---------- */
.eyebrow{display:inline-flex;align-items:center;gap:9px;font-size:.72rem;font-weight:600;
  letter-spacing:.17em;text-transform:uppercase;color:var(--gold);margin:0 0 20px}
.eyebrow::before{content:"";width:26px;height:1px;background:var(--gold);opacity:.65}
.dark .eyebrow{color:var(--gold-2)}
.lede{font-size:clamp(1.03rem,1.5vw,1.2rem);color:var(--tx-lm);max-width:64ch}
.dark .lede{color:var(--tx-dm)}
section{padding:clamp(64px,8vw,116px) 0;position:relative}
.dark{background:var(--ink);color:var(--tx-d)}
.dark h1,.dark h2,.dark h3{color:var(--tx-d)}
.tint{background:var(--paper-2)}

/* ---------- buttons ---------- */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:9px;
  font:inherit;font-size:1rem;font-weight:600;letter-spacing:-.01em;
  padding:15px 26px;min-height:52px;border-radius:11px;border:1px solid transparent;
  cursor:pointer;text-decoration:none;transition:transform .16s,box-shadow .16s,background .16s,border-color .16s;white-space:nowrap}
.btn:active{transform:translateY(1px)}
.btn-gold{background:linear-gradient(180deg,var(--gold-2),var(--gold));color:#221B08;
  box-shadow:0 8px 22px rgba(201,169,97,.3)}
.btn-gold:hover{box-shadow:0 12px 30px rgba(201,169,97,.42)}
.btn-dark{background:var(--ink);color:#fff}
.btn-dark:hover{background:var(--ink-3)}
.btn-ghost-d{background:rgba(255,255,255,.05);border-color:var(--line-d);color:var(--tx-d)}
.btn-ghost-d:hover{background:rgba(255,255,255,.11)}
.btn-ghost-l{background:#fff;border-color:var(--line-l);color:var(--tx-l)}
.btn-ghost-l:hover{border-color:rgba(8,8,10,.3)}
.btn-lg{font-size:1.06rem;padding:17px 32px;min-height:58px}
.btn-full{width:100%}
.btn[disabled]{opacity:.45;cursor:not-allowed}

/* ---------- announcement + header ---------- */
.announce{background:var(--ink-2);color:var(--tx-dm);font-size:.83rem;text-align:center;
  padding:9px 16px;border-bottom:1px solid var(--line-d)}
.announce b{color:var(--gold-2);font-weight:600}
.announce a{color:var(--tx-d);text-decoration:underline;text-underline-offset:3px}
header{position:sticky;top:0;z-index:90;background:rgba(8,8,10,.86);
  backdrop-filter:saturate(160%) blur(14px);border-bottom:1px solid var(--line-d)}
.nav{display:flex;align-items:center;gap:clamp(14px,2.4vw,34px);height:72px}
.logo{display:flex;align-items:center;gap:11px;text-decoration:none;color:#fff;font-weight:600;
  font-size:1.06rem;letter-spacing:-.02em;flex-shrink:0}
.logo-mk{width:34px;height:34px;border-radius:9px;background:linear-gradient(145deg,var(--gold-2),#9C7F3E);
  display:grid;place-items:center;color:#1A1405;font-weight:700;font-size:.95rem;flex-shrink:0}
.logo small{display:block;font-size:.6rem;letter-spacing:.15em;text-transform:uppercase;
  color:var(--gold);font-weight:500;line-height:1;margin-top:3px}
.nav-links{display:flex;gap:clamp(12px,1.8vw,26px);margin-left:auto;align-items:center}
.nav-links a{color:var(--tx-dm);text-decoration:none;font-size:.93rem;font-weight:500;
  padding:6px 0;border-bottom:1.5px solid transparent;transition:color .15s,border-color .15s}
.nav-links a:hover{color:var(--tx-d);border-color:var(--gold)}
.nav-cta{display:flex;align-items:center;gap:12px;flex-shrink:0}
.nav-tel{color:var(--tx-d);text-decoration:none;font-weight:600;font-size:.95rem;white-space:nowrap}
.nav-tel span{display:block;font-size:.62rem;letter-spacing:.12em;text-transform:uppercase;
  color:var(--gold);font-weight:500;line-height:1}
.burger{display:none;background:none;border:1px solid var(--line-d);border-radius:9px;
  width:44px;height:44px;color:#fff;cursor:pointer;font-size:1.1rem}

/* ---------- hero ---------- */
.hero{position:relative;background:var(--ink);color:var(--tx-d);overflow:hidden;
  padding:clamp(44px,6vw,80px) 0 clamp(56px,7vw,96px)}
.hero-bg{position:absolute;inset:0;z-index:0}
.hero-bg img{width:100%;height:100%;object-fit:cover;object-position:60% 45%;opacity:.5}
.hero-bg::after{content:"";position:absolute;inset:0;
  background:linear-gradient(103deg,var(--ink) 0%,rgba(8,8,10,.95) 34%,rgba(8,8,10,.62) 58%,rgba(8,8,10,.42) 100%)}
.hero-in{position:relative;z-index:1;display:grid;grid-template-columns:1.06fr .94fr;
  gap:clamp(32px,5vw,68px);align-items:center}
.hero h1{margin-bottom:20px}
.hero h1 em{font-style:normal;color:var(--gold-2)}
.hero-sub{font-size:clamp(1.04rem,1.55vw,1.24rem);color:var(--tx-dm);max-width:50ch;margin-bottom:26px}
.hero-chips{display:flex;flex-wrap:wrap;gap:9px;margin-bottom:8px}
.chip{display:inline-flex;align-items:center;gap:7px;background:rgba(255,255,255,.055);
  border:1px solid var(--line-d);border-radius:999px;padding:7px 14px;font-size:.83rem;
  color:var(--tx-dm);font-weight:500}
.chip svg{color:var(--gold);flex-shrink:0}
.stars{color:var(--gold);letter-spacing:1px}

/* ---------- quote widget ---------- */
.quote{background:#fff;color:var(--tx-l);border-radius:var(--r-lg);box-shadow:var(--sh-lg);
  overflow:hidden;border:1px solid rgba(255,255,255,.14)}
.quote-hd{background:var(--ink-2);color:#fff;padding:17px 24px;display:flex;
  align-items:center;justify-content:space-between;gap:12px}
.quote-hd strong{font-size:1.02rem;font-weight:600;letter-spacing:-.015em}
.quote-hd .pill{font-size:.68rem;letter-spacing:.13em;text-transform:uppercase;color:var(--gold-2);
  background:var(--gold-dim);padding:5px 11px;border-radius:999px;font-weight:600;white-space:nowrap}
.quote-bd{padding:24px}
.fld{margin-bottom:15px}
.fld label{display:block;font-size:.79rem;font-weight:600;letter-spacing:.02em;
  color:var(--tx-l);margin-bottom:7px}
.fld label .req{color:#C0392B}
.fld .hint{font-size:.76rem;color:var(--tx-lm);font-weight:400;margin-top:5px;display:block}
.ctl{width:100%;font:inherit;font-size:1rem;padding:13px 14px;min-height:50px;
  border:1.5px solid rgba(8,8,10,.16);border-radius:10px;background:#fff;color:var(--tx-l);
  transition:border-color .15s,box-shadow .15s;appearance:none}
.ctl:focus{outline:none;border-color:var(--gold);box-shadow:0 0 0 3px var(--gold-dim)}
.ctl.err{border-color:#C0392B;background:#FFF7F6}
select.ctl{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath fill='%2314141A' d='M1 1l5 5 5-5'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 14px center;padding-right:38px;cursor:pointer}
.fld-err{font-size:.79rem;color:#C0392B;margin-top:6px;font-weight:500;display:none}
.fld-err.on{display:block}
.seg{display:grid;grid-template-columns:1fr 1fr;gap:9px}
.seg input{position:absolute;opacity:0;pointer-events:none}
.seg label{display:block;text-align:center;padding:13px 10px;border:1.5px solid rgba(8,8,10,.16);
  border-radius:10px;cursor:pointer;font-size:.95rem;font-weight:600;margin:0;transition:all .15s;line-height:1.3}
.seg label small{display:block;font-size:.72rem;font-weight:500;color:var(--tx-lm);margin-top:2px}
.seg input:checked+label{border-color:var(--ink);background:var(--ink);color:#fff}
.seg input:checked+label small{color:rgba(255,255,255,.66)}
.seg input:focus-visible+label{box-shadow:0 0 0 3px var(--gold-dim)}
.quote-note{font-size:.78rem;color:var(--tx-lm);text-align:center;margin:13px 0 0;line-height:1.5}

/* quote result */
.result{border-top:1px solid var(--line-l);padding:22px 24px 24px;background:var(--paper);display:none}
.result.on{display:block;animation:rise .34s ease}
@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.result-top{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:16px}
.result-rt{font-size:.83rem;color:var(--tx-lm);line-height:1.5}
.result-rt b{color:var(--tx-l);display:block;font-size:.98rem;font-weight:600;margin-bottom:2px}
.price{font-size:clamp(2.6rem,6vw,3.5rem);font-weight:600;letter-spacing:-.045em;line-height:.94}
.price sup{font-size:.42em;font-weight:600;vertical-align:super;letter-spacing:0;margin-right:1px}
.price-lbl{font-size:.75rem;letter-spacing:.13em;text-transform:uppercase;color:var(--tx-lm);
  font-weight:600;margin-bottom:5px}
.save{display:inline-flex;align-items:center;gap:7px;background:rgba(63,164,106,.11);
  color:#2A7A4C;border:1px solid rgba(63,164,106,.28);border-radius:999px;
  padding:6px 13px;font-size:.82rem;font-weight:600;margin-top:9px}
.inc-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;margin:16px 0 18px;
  padding:15px 0;border-top:1px dashed var(--line-l);border-bottom:1px dashed var(--line-l)}
.inc-grid div{font-size:.83rem;color:var(--tx-lm);display:flex;align-items:center;gap:7px}
.inc-grid svg{color:var(--ok);flex-shrink:0}

/* ---------- trust bar ---------- */
.trust{background:var(--ink-2);border-top:1px solid var(--line-d);border-bottom:1px solid var(--line-d);
  padding:0;color:var(--tx-d)}
.trust-in{display:grid;grid-template-columns:repeat(5,1fr);gap:0}
.trust-i{padding:26px 22px;border-right:1px solid var(--line-d);text-align:center}
.trust-i:last-child{border-right:0}
.trust-i b{display:block;font-size:1.42rem;font-weight:600;letter-spacing:-.03em;margin-bottom:3px}
.trust-i span{font-size:.79rem;color:var(--tx-dm);letter-spacing:.03em;line-height:1.4;display:block}

/* ---------- generic grids/cards ---------- */
.g2{display:grid;grid-template-columns:1fr 1fr;gap:clamp(24px,3.4vw,48px)}
.g3{display:grid;grid-template-columns:repeat(3,1fr);gap:clamp(18px,2.4vw,30px)}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:clamp(16px,2vw,24px)}
.card{background:#fff;border:1px solid var(--line-l);border-radius:var(--r);padding:26px;box-shadow:var(--sh)}
.dark .card{background:var(--ink-3);border-color:var(--line-d);box-shadow:none}
.hd{margin-bottom:clamp(30px,4vw,52px);max-width:70ch}
.hd.ctr{margin-left:auto;margin-right:auto;text-align:center}
.hd.ctr .eyebrow::before{display:none}
.hd h2{margin-bottom:14px}

/* step cards */
.step{position:relative;padding-top:8px}
.step-n{width:40px;height:40px;border-radius:11px;background:var(--gold-dim);border:1px solid rgba(201,169,97,.4);
  color:var(--gold);display:grid;place-items:center;font-weight:700;font-size:1.02rem;margin-bottom:16px}
.dark .step-n{color:var(--gold-2)}
.step h3{margin-bottom:9px}
.step p{color:var(--tx-lm);font-size:.96rem;margin:0}
.dark .step p{color:var(--tx-dm)}

/* ---------- comparison table ---------- */
.cmp{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line-l);
  border-radius:var(--r);overflow:hidden;box-shadow:var(--sh)}
.cmp th,.cmp td{padding:15px 18px;text-align:left;border-bottom:1px solid var(--line-l);font-size:.95rem}
.cmp thead th{background:var(--ink);color:#fff;font-weight:600;font-size:.87rem;
  letter-spacing:.03em;border-bottom:0}
.cmp thead th:first-child{width:34%}
.cmp .us{background:rgba(201,169,97,.07);font-weight:600;position:relative}
.cmp thead .us{background:var(--ink-3);color:var(--gold-2)}
.cmp tbody tr:last-child td{border-bottom:0}
.cmp td:first-child{color:var(--tx-lm);font-weight:500}
.yes{color:var(--ok);font-weight:600}
.no{color:#B3452F;font-weight:500}
.tbl-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}

/* ---------- rates table ---------- */
.rates{width:100%;border-collapse:collapse;background:#fff;font-size:.95rem}
.rates caption{text-align:left;padding:0 0 14px;font-size:.86rem;color:var(--tx-lm)}
.rates th,.rates td{padding:13px 16px;text-align:left;border-bottom:1px solid var(--line-l)}
.rates thead th{background:var(--ink);color:#fff;font-size:.8rem;letter-spacing:.06em;
  text-transform:uppercase;font-weight:600;position:sticky;top:0;z-index:2}
.rates tbody th{font-weight:600;color:var(--tx-l)}
.rates tbody th small{display:block;font-weight:400;font-size:.78rem;color:var(--tx-lm);
  margin-top:2px;letter-spacing:0;text-transform:none}
.rates .rr{background:var(--paper-2)}
.rates .rr th{font-size:.74rem;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);
  padding:11px 16px;font-weight:600}
.rates .p{font-weight:600;font-size:1.06rem;white-space:nowrap}
.rates .was{color:var(--tx-lm);text-decoration:line-through;font-weight:400;
  font-size:.83rem;margin-left:6px;text-decoration-thickness:1px}
.rates .sv{color:#2A7A4C;font-weight:600;font-size:.83rem;white-space:nowrap}
.rates tbody tr:hover:not(.rr){background:rgba(201,169,97,.055)}
.rates .act a{font-size:.85rem;font-weight:600;color:var(--tx-l);text-decoration:none;
  border-bottom:1.5px solid var(--gold);white-space:nowrap}
.rates-wrap{border:1px solid var(--line-l);border-radius:var(--r);overflow:auto;
  max-height:none;box-shadow:var(--sh);background:#fff}

/* included list */
.inc-list{display:grid;grid-template-columns:1fr 1fr;gap:2px 26px;margin:0;padding:0;list-style:none}
.inc-list li{display:flex;gap:12px;padding:13px 0;border-bottom:1px solid var(--line-l);align-items:flex-start}
.inc-list svg{color:var(--ok);flex-shrink:0;margin-top:3px}
.inc-list b{display:block;font-size:.96rem;font-weight:600;margin-bottom:1px}
.inc-list span{font-size:.86rem;color:var(--tx-lm);line-height:1.5}

/* ---------- vehicles ---------- */
.veh{background:#fff;border:1px solid var(--line-l);border-radius:var(--r);overflow:hidden;
  box-shadow:var(--sh);display:flex;flex-direction:column;position:relative}
.veh.rec{border-color:var(--gold);border-width:2px;box-shadow:0 16px 44px rgba(201,169,97,.2)}
.veh-badge{position:absolute;top:14px;right:14px;z-index:2;background:var(--gold);color:#221B08;
  font-size:.67rem;font-weight:700;letter-spacing:.11em;text-transform:uppercase;
  padding:6px 12px;border-radius:999px}
.veh-img{aspect-ratio:16/10;background:var(--ink-3);overflow:hidden}
.veh-img img{width:100%;height:100%;object-fit:cover}
.veh-bd{padding:22px;display:flex;flex-direction:column;flex:1}
.veh h3{margin-bottom:3px}
.veh .ex{font-size:.83rem;color:var(--tx-lm);margin-bottom:12px;letter-spacing:.01em}
.veh p{font-size:.93rem;color:var(--tx-lm);margin-bottom:16px}
.veh ul{list-style:none;margin:0 0 20px;padding:0;font-size:.89rem}
.veh ul li{padding:6px 0;display:flex;gap:9px;align-items:center;color:var(--tx-lm)}
.veh ul svg{color:var(--gold);flex-shrink:0}
.veh-ft{margin-top:auto;padding-top:18px;border-top:1px solid var(--line-l)}
.veh-pr{display:flex;align-items:baseline;gap:7px;margin-bottom:14px}
.veh-pr b{font-size:1.65rem;font-weight:600;letter-spacing:-.035em}
.veh-pr span{font-size:.82rem;color:var(--tx-lm)}

/* ---------- booking flow ---------- */
.book-shell{background:#fff;border-radius:var(--r-lg);box-shadow:var(--sh-lg);overflow:hidden;
  max-width:840px;margin:0 auto;color:var(--tx-l)}
.prog{display:flex;background:var(--ink-2);padding:0;overflow:hidden}
.prog-i{flex:1;padding:15px 8px;text-align:center;font-size:.78rem;font-weight:600;
  color:rgba(255,255,255,.4);border-bottom:2.5px solid transparent;position:relative;
  letter-spacing:.03em;transition:all .2s}
.prog-i.on{color:#fff;border-bottom-color:var(--gold)}
.prog-i.done{color:var(--gold-2);border-bottom-color:rgba(201,169,97,.45)}
.prog-i em{display:block;font-style:normal;font-size:.66rem;font-weight:500;
  letter-spacing:.1em;text-transform:uppercase;opacity:.72;margin-bottom:2px}
.stepv{display:none;padding:clamp(24px,4vw,38px)}
.stepv.on{display:block;animation:rise .3s ease}
.stepv h3{margin-bottom:6px}
.stepv .sd{color:var(--tx-lm);font-size:.94rem;margin-bottom:24px}
.f2{display:grid;grid-template-columns:1fr 1fr;gap:0 15px}
.f3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:0 15px}
.nav-btns{display:flex;gap:12px;margin-top:26px;padding-top:22px;border-top:1px solid var(--line-l)}
.nav-btns .btn{flex:1}
.nav-btns .btn.back{flex:0 0 auto}

/* summary rail */
.summ{background:var(--paper);border:1px solid var(--line-l);border-radius:var(--r);padding:18px 20px;margin-bottom:22px}
.summ-r{display:flex;justify-content:space-between;gap:14px;padding:7px 0;font-size:.92rem}
.summ-r span{color:var(--tx-lm)}
.summ-r b{font-weight:600;text-align:right}
.summ-tot{border-top:1.5px solid var(--line-l);margin-top:9px;padding-top:13px;font-size:1.12rem}
.summ-tot b{font-size:1.5rem;letter-spacing:-.03em}

/* vehicle picker rows */
.vpick{display:grid;gap:11px;margin-bottom:6px}
.vrow{position:relative}
.vrow input{position:absolute;opacity:0;pointer-events:none}
.vrow label{display:flex;align-items:center;gap:16px;padding:16px;border:1.5px solid rgba(8,8,10,.16);
  border-radius:12px;cursor:pointer;transition:all .15s;margin:0}
.vrow input:checked+label{border-color:var(--gold);border-width:2px;padding:15px;background:rgba(201,169,97,.055)}
.vrow input:focus-visible+label{box-shadow:0 0 0 3px var(--gold-dim)}
.vrow-ic{width:52px;height:52px;border-radius:11px;background:var(--ink);color:var(--gold);
  display:grid;place-items:center;flex-shrink:0}
.vrow-tx{flex:1;min-width:0}
.vrow-tx b{display:block;font-size:1rem;font-weight:600}
.vrow-tx span{font-size:.83rem;color:var(--tx-lm)}
.vrow-pr{text-align:right;flex-shrink:0}
.vrow-pr b{display:block;font-size:1.24rem;font-weight:600;letter-spacing:-.03em}
.vrow-pr span{font-size:.75rem;color:var(--tx-lm)}

/* payment */
.pay-sec{border:1px solid var(--line-l);border-radius:var(--r);padding:20px;margin-bottom:18px;background:#fff}
.pay-hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;gap:12px}
.pay-hd b{font-size:.98rem}
.cards{display:flex;gap:6px;align-items:center}
.cards i{width:32px;height:21px;border-radius:4px;background:var(--paper-2);
  border:1px solid var(--line-l);font-size:.55rem;font-style:normal;font-weight:700;
  display:grid;place-items:center;color:var(--tx-lm);letter-spacing:-.02em}
.secure{display:flex;align-items:center;gap:8px;font-size:.82rem;color:var(--tx-lm);
  background:var(--paper);border:1px dashed var(--line-l);border-radius:10px;padding:12px 14px;margin-top:4px}
.secure svg{color:var(--ok);flex-shrink:0}
.hook{background:#FFFBF2;border:1px solid rgba(208,138,62,.32);border-left:3px solid var(--warn);
  border-radius:9px;padding:13px 15px;font-size:.83rem;color:#7A5320;margin-top:16px;line-height:1.55}
.hook b{color:#5E3F17}
.hook code{background:rgba(208,138,62,.13);padding:1px 5px;border-radius:4px;font-size:.93em;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace}

/* confirmed */
.conf{text-align:center;padding:clamp(30px,5vw,48px) clamp(20px,4vw,38px)}
.conf-ic{width:74px;height:74px;border-radius:50%;background:rgba(63,164,106,.13);
  border:2px solid rgba(63,164,106,.4);color:var(--ok);display:grid;place-items:center;
  margin:0 auto 22px;animation:pop .45s cubic-bezier(.34,1.56,.64,1)}
@keyframes pop{0%{transform:scale(.5);opacity:0}100%{transform:scale(1);opacity:1}}
.conf h3{font-size:clamp(1.5rem,3vw,2rem);margin-bottom:10px}
.ref{display:inline-block;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  background:var(--ink);color:var(--gold-2);padding:10px 18px;border-radius:9px;
  font-size:1.06rem;letter-spacing:.09em;margin:6px 0 20px;font-weight:600}
.conf-grid{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line-l);
  border:1px solid var(--line-l);border-radius:var(--r);overflow:hidden;margin:22px 0;text-align:left}
.conf-grid div{background:#fff;padding:15px 17px}
.conf-grid span{display:block;font-size:.71rem;letter-spacing:.11em;text-transform:uppercase;
  color:var(--tx-lm);font-weight:600;margin-bottom:4px}
.conf-grid b{font-size:.99rem;font-weight:600}
.overnight{background:var(--ink);color:var(--tx-d);border-radius:var(--r);padding:19px 22px;
  text-align:left;display:flex;gap:15px;align-items:flex-start;margin:22px 0}
.overnight svg{color:var(--gold);flex-shrink:0;margin-top:2px}
.overnight b{display:block;margin-bottom:4px;font-size:.99rem}
.overnight p{margin:0;font-size:.88rem;color:var(--tx-dm)}

/* ---------- tracking ---------- */
.track-grid{display:grid;grid-template-columns:1.32fr 1fr;gap:24px;align-items:start}
.map-card{background:var(--ink-3);border:1px solid var(--line-d);border-radius:var(--r-lg);overflow:hidden}
.map-hd{display:flex;align-items:center;justify-content:space-between;gap:14px;
  padding:16px 20px;border-bottom:1px solid var(--line-d);flex-wrap:wrap}
.live-dot{display:inline-flex;align-items:center;gap:8px;font-size:.76rem;font-weight:600;
  letter-spacing:.11em;text-transform:uppercase;color:var(--live)}
.live-dot i{width:8px;height:8px;border-radius:50%;background:var(--live);
  box-shadow:0 0 0 0 rgba(74,222,128,.75);animation:pulse 2s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(74,222,128,.65)}70%{box-shadow:0 0 0 10px rgba(74,222,128,0)}100%{box-shadow:0 0 0 0 rgba(74,222,128,0)}}
#map{height:410px;width:100%;background:var(--ink-4)}
.map-fb{height:410px;display:grid;place-items:center;text-align:center;padding:30px;
  color:var(--tx-dm);font-size:.9rem}
.eta{display:flex;align-items:baseline;gap:9px}
.eta b{font-size:1.85rem;font-weight:600;letter-spacing:-.035em;color:var(--gold-2)}
.eta span{font-size:.79rem;color:var(--tx-dm);letter-spacing:.06em;text-transform:uppercase}
.drv{display:flex;gap:15px;align-items:center;padding:17px 20px;border-top:1px solid var(--line-d);flex-wrap:wrap}
.drv-av{width:52px;height:52px;border-radius:50%;background:linear-gradient(145deg,var(--gold-2),#8E7235);
  display:grid;place-items:center;font-weight:700;color:#1A1405;font-size:1.06rem;flex-shrink:0}
.drv-tx{flex:1;min-width:120px}
.drv-tx b{display:block;font-size:1rem}
.drv-tx span{font-size:.83rem;color:var(--tx-dm)}
.drv-veh{text-align:right;font-size:.83rem;color:var(--tx-dm);line-height:1.5}
.drv-veh b{display:block;color:var(--tx-d);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  letter-spacing:.06em;font-size:.92rem}

/* chat */
.chat{background:var(--ink-3);border:1px solid var(--line-d);border-radius:var(--r-lg);
  display:flex;flex-direction:column;height:530px;overflow:hidden}
.chat-hd{padding:15px 18px;border-bottom:1px solid var(--line-d);display:flex;
  align-items:center;justify-content:space-between;gap:10px;flex-shrink:0}
.chat-hd b{font-size:.97rem}
.chat-hd small{display:block;font-size:.75rem;color:var(--tx-dm);font-weight:400;margin-top:1px}
.chat-log{flex:1;overflow-y:auto;padding:18px;display:flex;flex-direction:column;gap:11px}
.msg{max-width:82%;padding:11px 15px;border-radius:15px;font-size:.91rem;line-height:1.5;
  animation:rise .25s ease;word-wrap:break-word}
.msg.me{align-self:flex-end;background:linear-gradient(180deg,var(--gold-2),var(--gold));
  color:#221B08;border-bottom-right-radius:5px;font-weight:500}
.msg.them{align-self:flex-start;background:var(--ink-4);color:var(--tx-d);
  border:1px solid var(--line-d);border-bottom-left-radius:5px}
.msg time{display:block;font-size:.68rem;opacity:.6;margin-top:4px;letter-spacing:.03em}
.msg.sys{align-self:center;max-width:100%;background:none;border:0;color:var(--tx-dm);
  font-size:.78rem;text-align:center;padding:3px 0}
.typing{align-self:flex-start;display:flex;gap:4px;padding:13px 16px;background:var(--ink-4);
  border:1px solid var(--line-d);border-radius:15px;border-bottom-left-radius:5px}
.typing i{width:6px;height:6px;border-radius:50%;background:var(--tx-dm);animation:blink 1.4s infinite}
.typing i:nth-child(2){animation-delay:.2s}
.typing i:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,60%,100%{opacity:.28}30%{opacity:1}}
.quick{display:flex;gap:7px;padding:0 18px 12px;flex-wrap:wrap;flex-shrink:0}
.quick button{background:rgba(255,255,255,.055);border:1px solid var(--line-d);color:var(--tx-dm);
  font:inherit;font-size:.79rem;padding:7px 12px;border-radius:999px;cursor:pointer;transition:all .15s}
.quick button:hover{background:rgba(255,255,255,.12);color:var(--tx-d)}
.chat-in{display:flex;gap:9px;padding:14px 18px;border-top:1px solid var(--line-d);flex-shrink:0}
.chat-in input{flex:1;background:var(--ink-4);border:1px solid var(--line-d);color:var(--tx-d);
  font:inherit;font-size:.93rem;padding:12px 15px;border-radius:999px;min-height:46px}
.chat-in input:focus{outline:none;border-color:var(--gold)}
.chat-in input::placeholder{color:rgba(247,246,244,.4)}
.chat-in button{width:46px;height:46px;border-radius:50%;border:0;flex-shrink:0;
  background:linear-gradient(180deg,var(--gold-2),var(--gold));color:#221B08;cursor:pointer;
  display:grid;place-items:center}

/* ---------- departure planner ---------- */
.plan-grid{display:grid;grid-template-columns:1fr 1fr;gap:clamp(20px,2.6vw,34px);align-items:start}
.plan-card{background:#fff;border:1px solid var(--line-l);border-radius:var(--r-lg);
  box-shadow:var(--sh);overflow:hidden}
.plan-hd{background:var(--ink-2);color:#fff;padding:16px 22px;display:flex;
  align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.plan-hd strong{font-size:1rem;font-weight:600}
.plan-modes{display:flex;gap:6px;background:rgba(255,255,255,.07);padding:4px;border-radius:999px}
.plan-modes button{background:none;border:0;color:var(--tx-dm);font:inherit;font-size:.84rem;
  font-weight:600;padding:8px 15px;border-radius:999px;cursor:pointer;transition:all .15s;white-space:nowrap}
.plan-modes button.on{background:var(--gold);color:#221B08}
.plan-bd{padding:22px}
.chk{display:flex;align-items:flex-start;gap:10px;margin:2px 0 4px;cursor:pointer;font-size:.9rem}
.chk input{width:20px;height:20px;margin:1px 0 0;accent-color:var(--gold);flex-shrink:0;cursor:pointer}
.chk span{color:var(--tx-lm)}
.chk b{color:var(--tx-l);font-weight:600;display:block;font-size:.93rem}

.plan-out{background:var(--ink);color:var(--tx-d);border-radius:var(--r-lg);
  padding:0;overflow:hidden;display:none;border:1px solid var(--line-d)}
.plan-out.on{display:block;animation:rise .34s ease}
.plan-top{padding:26px 26px 22px;border-bottom:1px solid var(--line-d);
  background:radial-gradient(ellipse 80% 120% at 30% 0%,rgba(201,169,97,.16),transparent 70%)}
.plan-top .lbl{font-size:.73rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--gold);font-weight:600;margin-bottom:11px}
.plan-leave{font-size:clamp(1.7rem,3.4vw,2.5rem);font-weight:600;letter-spacing:-.035em;
  line-height:1.05;color:var(--gold-2);margin-bottom:8px}
.plan-top .sub{font-size:.9rem;color:var(--tx-dm)}
.pb{padding:8px 26px 22px}
.pb-row{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;
  padding:13px 0;border-bottom:1px solid var(--line-d)}
.pb-row:last-child{border-bottom:0}
.pb-row b{font-size:.93rem;font-weight:600;display:block}
.pb-row span{font-size:.82rem;color:var(--tx-dm);display:block;margin-top:2px;line-height:1.5}
.pb-v{font-size:.93rem !important;color:var(--tx-d) !important;font-weight:600;
  white-space:nowrap;font-variant-numeric:tabular-nums;margin-top:0 !important}
.pb-tot{border-top:1.5px solid rgba(201,169,97,.4);margin-top:6px;padding-top:15px;align-items:center}
.pb-tot b{font-size:1.02rem}
.pb-tot>b:last-child{color:var(--gold-2);font-size:1.3rem;letter-spacing:-.03em}
.plan-ft{padding:0 26px 26px}
.plan-empty{padding:38px 26px;text-align:center;color:var(--tx-lm);font-size:.93rem;
  border:1px dashed var(--line-l);border-radius:var(--r-lg);background:#fff}
.rec-box{background:#F3F9F5;border:1px solid rgba(63,164,106,.32);border-left:3px solid var(--ok);
  border-radius:9px;padding:14px 16px;margin:2px 0 16px;display:none}
.rec-box .t{font-size:.88rem;color:#255E3E;line-height:1.6;margin-bottom:11px}
.rec-box .t b{color:#17402A}
@media(max-width:1080px){.plan-grid{grid-template-columns:1fr}}

/* ---------- events ---------- */
.ev-hd{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;
  margin-bottom:26px;flex-wrap:wrap}
.tabs{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:22px}
.tab{background:rgba(255,255,255,.05);border:1px solid var(--line-d);color:var(--tx-dm);
  font:inherit;font-size:.87rem;font-weight:500;padding:9px 16px;border-radius:999px;
  cursor:pointer;transition:all .15s;display:inline-flex;align-items:center;gap:7px}
.tab:hover{color:var(--tx-d);background:rgba(255,255,255,.1)}
.tab.on{background:var(--gold);border-color:var(--gold);color:#221B08;font-weight:600}
.tab .n{font-size:.72rem;opacity:.7;font-variant-numeric:tabular-nums}
.ev-list{display:grid;gap:10px;min-height:180px}
.ev{display:flex;gap:18px;align-items:center;background:var(--ink-3);border:1px solid var(--line-d);
  border-radius:var(--r);padding:16px 20px;transition:border-color .15s;animation:rise .3s ease}
.ev:hover{border-color:rgba(201,169,97,.42)}
.ev-dt{text-align:center;flex-shrink:0;width:56px}
.ev-dt b{display:block;font-size:1.42rem;font-weight:600;letter-spacing:-.035em;line-height:1;color:var(--gold-2)}
.ev-dt span{display:block;font-size:.68rem;letter-spacing:.13em;text-transform:uppercase;
  color:var(--tx-dm);margin-top:3px}
.ev-tx{flex:1;min-width:0}
.ev-tx b{display:block;font-size1rem;font-size:1rem;font-weight:600;margin-bottom:3px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ev-tx span{font-size:.84rem;color:var(--tx-dm);display:flex;gap:9px;align-items:center;flex-wrap:wrap}
.ev-tx span i{font-style:normal;color:var(--gold);font-size:.72rem}
.ev-cta{flex-shrink:0}
.ev-cta .btn{padding:11px 18px;min-height:44px;font-size:.88rem}
.ev-src{font-size:.75rem;color:var(--tx-dm);margin-top:16px;display:flex;
  align-items:center;gap:8px;flex-wrap:wrap;line-height:1.6}
.ev-src a{color:var(--gold-2)}
.ev-empty{text-align:center;padding:40px 24px;color:var(--tx-dm);border:1px dashed var(--line-d);
  border-radius:var(--r);font-size:.92rem}
.skel{height:76px;border-radius:var(--r);background:linear-gradient(90deg,var(--ink-3) 25%,var(--ink-4) 50%,var(--ink-3) 75%);
  background-size:200% 100%;animation:shim 1.4s infinite;border:1px solid var(--line-d)}
@keyframes shim{0%{background-position:200% 0}100%{background-position:-200% 0}}

/* feed connector */
.conn{background:var(--ink-3);border:1px solid var(--line-d);border-radius:var(--r);padding:22px}
.conn h4{margin:0 0 8px;font-size:1.02rem;font-weight:600}
.conn p{font-size:.88rem;color:var(--tx-dm);margin-bottom:16px}
.conn-row{display:flex;gap:9px;flex-wrap:wrap}
.conn-row input{flex:1;min-width:210px;background:var(--ink-4);border:1px solid var(--line-d);
  color:var(--tx-d);font:inherit;font-size:.92rem;padding:12px 15px;border-radius:10px;min-height:48px}
.conn-row input:focus{outline:none;border-color:var(--gold)}
.conn-ok{display:flex;align-items:center;gap:9px;font-size:.86rem;color:var(--live);font-weight:500}

/* ---------- reviews ---------- */
.rev{background:#fff;border:1px solid var(--line-l);border-radius:var(--r);padding:26px;
  display:flex;flex-direction:column;box-shadow:var(--sh)}
.rev-st{color:var(--gold);letter-spacing:2px;margin-bottom:13px;font-size:.95rem}
.rev p{font-size:.99rem;line-height:1.65;flex:1;margin-bottom:18px}
.rev-by{display:flex;align-items:center;gap:12px;padding-top:16px;border-top:1px solid var(--line-l)}
.rev-av{width:42px;height:42px;border-radius:50%;background:var(--ink);color:var(--gold-2);
  display:grid;place-items:center;font-weight:600;font-size:.95rem;flex-shrink:0}
.rev-by b{display:block;font-size:.94rem;font-weight:600}
.rev-by span{font-size:.81rem;color:var(--tx-lm)}

/* ---------- faq ---------- */
.faq{max-width:880px;margin:0 auto}
.faq details{border-bottom:1px solid var(--line-l);padding:0}
.faq summary{cursor:pointer;padding:21px 44px 21px 0;font-size:1.06rem;font-weight:600;
  letter-spacing:-.015em;position:relative;list-style:none;transition:color .15s}
.faq summary::-webkit-details-marker{display:none}
.faq summary:hover{color:#000}
.faq summary::after{content:"";position:absolute;right:6px;top:50%;width:11px;height:11px;
  border-right:2px solid var(--gold);border-bottom:2px solid var(--gold);
  transform:translateY(-70%) rotate(45deg);transition:transform .22s}
.faq details[open] summary::after{transform:translateY(-30%) rotate(225deg)}
.faq .ans{padding:0 40px 24px 0;color:var(--tx-lm);font-size:.99rem;line-height:1.7}
.faq .ans p:last-child{margin-bottom:0}

/* ---------- cta band ---------- */
.band{background:var(--ink);color:var(--tx-d);text-align:center;position:relative;overflow:hidden}
.band::before{content:"";position:absolute;inset:0;
  background:radial-gradient(ellipse 62% 88% at 50% 0%,rgba(201,169,97,.15),transparent 68%)}
.band .wrap{position:relative;z-index:1}
.band h2{margin-bottom:16px}
.band .lede{margin:0 auto 30px}
.band-btns{display:flex;gap:13px;justify-content:center;flex-wrap:wrap}
.guar{display:inline-flex;align-items:center;gap:10px;margin-top:26px;font-size:.89rem;
  color:var(--tx-dm);background:rgba(255,255,255,.05);border:1px solid var(--line-d);
  border-radius:999px;padding:10px 20px}
.guar svg{color:var(--gold)}

/* ---------- soon / waitlist ---------- */
.soon{display:flex;gap:24px;align-items:center;background:var(--ink-3);border:1px solid var(--line-d);
  border-radius:var(--r-lg);padding:clamp(24px,3.5vw,38px);flex-wrap:wrap}
.soon-tx{flex:1;min-width:260px}
.soon-tx h3{margin-bottom:9px}
.soon-tx p{color:var(--tx-dm);margin:0;font-size:.96rem}
.soon-fm{display:flex;gap:9px;flex-wrap:wrap;min-width:280px;flex:1}
.soon-fm input{flex:1;min-width:180px;background:var(--ink-4);border:1px solid var(--line-d);
  color:var(--tx-d);font:inherit;padding:14px 16px;border-radius:10px;min-height:52px}
.soon-fm input:focus{outline:none;border-color:var(--gold)}
.badge-soon{display:inline-block;background:var(--gold-dim);border:1px solid rgba(201,169,97,.4);
  color:var(--gold-2);font-size:.68rem;font-weight:700;letter-spacing:.13em;text-transform:uppercase;
  padding:5px 11px;border-radius:999px;margin-bottom:13px}

/* ---------- footer ---------- */
footer{background:var(--ink-2);color:var(--tx-dm);padding:clamp(48px,6vw,76px) 0 0;
  border-top:1px solid var(--line-d);font-size:.92rem}
.ft-top{display:grid;grid-template-columns:1.5fr 1fr 1fr 1fr;gap:clamp(24px,3.4vw,44px);
  padding-bottom:40px}
.ft-top h4{color:var(--tx-d);font-size:.78rem;letter-spacing:.14em;text-transform:uppercase;
  margin:0 0 16px;font-weight:600}
.ft-top ul{list-style:none;margin:0;padding:0}
.ft-top li{margin-bottom:9px}
.ft-top a{color:var(--tx-dm);text-decoration:none;transition:color .15s}
.ft-top a:hover{color:var(--gold-2)}
.ft-ab p{font-size:.9rem;line-height:1.65;margin-bottom:16px;max-width:38ch}
.ft-nap{font-size:.87rem;line-height:1.8;font-style:normal}
.ft-nap a{color:var(--tx-d);font-weight:600}
.ft-counties{padding:26px 0;border-top:1px solid var(--line-d)}
.ft-counties h4{color:var(--tx-d);font-size:.78rem;letter-spacing:.14em;text-transform:uppercase;
  margin:0 0 14px;font-weight:600}
.ft-cl{display:flex;flex-wrap:wrap;gap:7px 0;list-style:none;margin:0;padding:0}
.ft-cl li{font-size:.85rem}
.ft-cl li::after{content:"·";margin:0 9px;opacity:.4}
.ft-cl li:last-child::after{display:none}
.ft-cl a{color:var(--tx-dm);text-decoration:none}
.ft-cl a:hover{color:var(--gold-2);text-decoration:underline;text-underline-offset:3px}
.ft-bt{border-top:1px solid var(--line-d);padding:22px 0;display:flex;
  justify-content:space-between;gap:18px;flex-wrap:wrap;font-size:.83rem}
.ft-bt a{color:var(--tx-dm);text-decoration:none;margin-left:18px}
.ft-bt a:first-child{margin-left:0}
.ph{color:var(--warn);font-size:.78rem;background:rgba(208,138,62,.13);
  border:1px dashed rgba(208,138,62,.42);border-radius:6px;padding:2px 7px;
  display:inline-block;margin-top:9px;letter-spacing:.02em}

/* ---------- sticky mobile bar ---------- */
.mbar{position:fixed;bottom:0;left:0;right:0;z-index:80;display:none;gap:9px;padding:10px 12px;
  background:rgba(8,8,10,.95);backdrop-filter:blur(14px);border-top:1px solid var(--line-d);
  padding-bottom:calc(10px + env(safe-area-inset-bottom))}
.mbar .btn{flex:1;min-height:50px}

/* ---------- exit popup ---------- */
.pop-bd{position:fixed;inset:0;z-index:200;background:rgba(8,8,10,.72);
  backdrop-filter:blur(5px);display:none;place-items:center;padding:20px}
.pop-bd.on{display:grid;animation:fade .22s ease}
@keyframes fade{from{opacity:0}to{opacity:1}}
.pop{background:#fff;border-radius:var(--r-lg);max-width:480px;width:100%;
  box-shadow:var(--sh-lg);overflow:hidden;position:relative;animation:rise .32s ease}
.pop-x{position:absolute;top:12px;right:12px;width:38px;height:38px;border-radius:50%;
  border:1px solid var(--line-l);background:#fff;cursor:pointer;font-size:1.16rem;
  color:var(--tx-lm);display:grid;place-items:center;z-index:2;line-height:1}
.pop-x:hover{background:var(--paper-2);color:var(--tx-l)}
.pop-in{padding:34px 30px 28px}
.pop h3{font-size:1.5rem;margin-bottom:10px;max-width:22ch}
.pop p{font-size:.96rem;color:var(--tx-lm);margin-bottom:20px}
.pop-no{display:block;width:100%;text-align:center;background:none;border:0;color:var(--tx-lm);
  font:inherit;font-size:.87rem;padding:13px 0 0;cursor:pointer;text-decoration:underline;
  text-underline-offset:3px}

/* toast */
.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(120%);
  z-index:300;background:var(--ink);color:var(--tx-d);border:1px solid var(--line-d);
  border-radius:999px;padding:13px 24px;font-size:.9rem;font-weight:500;
  box-shadow:var(--sh-lg);transition:transform .32s cubic-bezier(.34,1.4,.64,1);
  display:flex;align-items:center;gap:10px;max-width:calc(100vw - 32px)}
.toast.on{transform:translateX(-50%) translateY(0)}
.toast svg{color:var(--live);flex-shrink:0}

/* ---------- responsive ---------- */
@media(max-width:1080px){
  .hero-in{grid-template-columns:1fr;gap:34px}
  .quote{max-width:560px}
  .track-grid{grid-template-columns:1fr}
  .chat{height:460px}
  .trust-in{grid-template-columns:repeat(3,1fr)}
  .trust-i:nth-child(3){border-right:0}
  .trust-i:nth-child(n+4){border-top:1px solid var(--line-d)}
  .ft-top{grid-template-columns:1fr 1fr}
}
@media(max-width:860px){
  .nav-links{display:none}
  .nav-links.open{display:flex;position:absolute;top:72px;left:0;right:0;background:var(--ink-2);
    flex-direction:column;padding:18px 24px;gap:2px;border-bottom:1px solid var(--line-d);
    box-shadow:var(--sh-lg)}
  .nav-links.open a{padding:12px 0;width:100%;border-bottom:1px solid var(--line-d)}
  .burger{display:grid;place-items:center;margin-left:auto}
  .nav-cta .nav-tel{display:none}
  .nav-cta .btn{display:none}
  .g3,.g4,.g2{grid-template-columns:1fr}
  .f2,.f3,.seg{grid-template-columns:1fr}
  .inc-list,.inc-grid,.conf-grid{grid-template-columns:1fr}
  .mbar{display:flex}
  body{padding-bottom:72px}
  .prog-i{font-size:0;padding:13px 4px}
  .prog-i em{font-size:.62rem;margin:0}
  .prog-i.on{font-size:0}
  .ev{flex-wrap:wrap;gap:13px}
  .ev-cta{width:100%}
  .ev-cta .btn{width:100%}
  .drv-veh{text-align:left;width:100%}
  .cmp thead th:first-child{width:auto}
}
@media(max-width:560px){
  .trust-in{grid-template-columns:1fr 1fr}
  .trust-i:nth-child(2){border-right:0}
  .trust-i:nth-child(n+3){border-top:1px solid var(--line-d)}
  .trust-i:nth-child(odd){border-right:1px solid var(--line-d)}
  .trust-i:last-child{grid-column:1/-1;border-right:0}
  .ft-top{grid-template-columns:1fr}
  .band-btns .btn{width:100%}
  .nav-btns{flex-direction:column-reverse}
}
@media(prefers-reduced-motion:reduce){
  *{animation-duration:.01ms !important;animation-iteration-count:1 !important;
    transition-duration:.01ms !important;scroll-behavior:auto !important}
}
@media print{header,.mbar,.pop-bd,.announce{display:none}}

/* leaflet dark tweak */
.leaflet-container{background:var(--ink-4)!important;font-family:var(--ff)!important}
.leaflet-tile{filter:saturate(.35) brightness(.62) contrast(1.08)}
.leaflet-control-attribution{background:rgba(8,8,10,.75)!important;color:var(--tx-dm)!important;font-size:9px!important}
.leaflet-control-attribution a{color:var(--gold-2)!important}
.leaflet-bar{border:1px solid var(--line-d)!important}
.leaflet-bar a{background:var(--ink-3)!important;color:var(--tx-d)!important;border-color:var(--line-d)!important}
.leaflet-bar a:hover{background:var(--ink-4)!important}
.car-mk{display:grid;place-items:center;width:38px;height:38px;border-radius:50%;
  background:var(--gold);color:#221B08;box-shadow:0 0 0 6px rgba(201,169,97,.24),0 4px 14px rgba(0,0,0,.4);
  font-size:1rem;transition:transform .9s linear}
.pin-mk{display:grid;place-items:center;width:26px;height:26px;border-radius:50%;
  background:var(--ink-3);border:2px solid var(--gold-2);color:var(--gold-2);font-size:.7rem;font-weight:700}
"""
