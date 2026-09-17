interface Env {
  SNAPSHOTS: R2Bucket;
  SYNC_SECRET: string;
}

const BLANK = {
  note: "no sync yet, run sync from the CLI after a session",
  workouts: [],
  sets: [],
  bodyweight: [],
};

const GROUPS = ["chest", "back", "shoulders", "biceps", "triceps", "quads", "hamstrings", "glutes", "abs"];

function muscleOf(name: string): string {
  const n = name.toLowerCase();
  if (/(leg curl|nordic|hamstring|good morning|romanian|rdl|deadlift)/.test(n)) return "hamstrings";
  if (/(tricep|pushdown|skull)/.test(n)) return "triceps";
  if (/(bench|chest|fly|pushup|push up|dips|incline)/.test(n)) return "chest";
  if (/(overhead|ohp|shoulder|lateral|rear delt|face pull|arnold)/.test(n)) return "shoulders";
  if (/(pullup|chinup|pulldown|pendlay|pullover| lat | rows| row )/.test(" " + n + " ")) return "back";
  if (/(bicep|curl|hammer|preacher)/.test(n)) return "biceps";
  if (/(squat|leg press|lunge|leg extension|hack)/.test(n)) return "quads";
  if (/(hip thrust|glute|hip abduct)/.test(n)) return "glutes";
  if (/(crunch|plank|leg raise|knee raise|hanging|abs|core|ab wheel)/.test(n)) return "abs";
  return "other";
}

const PAGE = `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>reps dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{background:#f5f2e9;color:#1f211c;font-family:"IBM Plex Serif",Georgia,serif;line-height:1.6;padding:40px 24px 90px;}
.wrap{max-width:1240px;margin:0 auto;}
.cols2{display:grid;grid-template-columns:1fr 1fr;gap:0 20px;}
@media (max-width:900px){.cols2{grid-template-columns:1fr;}}
.kick{font-family:"IBM Plex Sans",sans-serif;font-size:.8rem;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:#75603a;margin-bottom:8px;}
h1{font-size:2.6rem;letter-spacing:-.02em;margin-bottom:6px;}
.sub{font-family:"IBM Plex Sans",sans-serif;color:#4e5148;margin-bottom:26px;}
h2{font-size:1.35rem;margin:34px 0 10px;}
.card{background:#fffdf7;border:1px solid #d9d3c0;border-radius:14px;padding:16px;margin:12px 0;}
canvas{width:100%;height:250px;display:block;}
.legend{display:flex;flex-wrap:wrap;gap:8px 16px;margin-top:10px;font-family:"IBM Plex Sans",sans-serif;font-size:.85rem;}
#legTrend{max-height:132px;overflow-y:auto;}
.minigrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px 12px;}
.mini{min-width:0;}
.mini canvas{width:100%;height:110px;display:block;cursor:pointer;}
.minititle{display:flex;justify-content:space-between;align-items:baseline;gap:8px;font-family:"IBM Plex Sans",sans-serif;font-size:.85rem;margin-bottom:2px;}
.minititle a{color:inherit;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.minititle span{font-family:"JetBrains Mono",monospace;color:#4e5148;flex:none;}
@media (prefers-color-scheme:dark){
.minititle span{color:#b0aca2;}
}
button.chip.mini{border:1px solid #d9d3c0;font-weight:600;}
@media (prefers-color-scheme:dark){
button.chip.mini{border-color:#3a3733;}
}
.chip{display:inline-flex;align-items:center;gap:7px;}
button.chip{background:none;border:1px solid transparent;border-radius:8px;padding:4px 8px;cursor:pointer;color:inherit;font-family:inherit;font-size:.85rem;}
button.chip.off{opacity:.35;}
.sw{width:22px;height:4px;border-radius:2px;display:inline-block;}
.cap{font-family:"IBM Plex Sans",sans-serif;font-size:.88rem;color:#4e5148;margin-top:10px;}
.notes{font-family:"IBM Plex Sans",sans-serif;font-size:.88rem;color:#4e5148;margin-top:10px;}
.notes li{margin-bottom:4px;margin-left:20px;}
.calcard{min-width:0;}
.calhead{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;font-family:"IBM Plex Sans",sans-serif;}
.calhead b{font-size:1.05rem;font-weight:600;letter-spacing:-.01em;}
.calhead button{background:none;border:none;border-radius:8px;padding:6px;cursor:pointer;color:inherit;display:flex;}
.calhead button:hover{background:rgba(127,122,110,.16);}
.calhead button svg{width:18px;height:18px;}
.cal{display:grid;grid-template-columns:repeat(7,1fr);gap:4px;font-family:"IBM Plex Sans",sans-serif;font-size:.86rem;}
.cal .dw{font-size:.66rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#8a8478;text-align:center;padding:4px 0;}
.cal .cd{min-height:36px;height:36px;width:36px;margin:0 auto;border-radius:9px;display:flex;align-items:center;justify-content:center;color:#6e695c;position:relative;text-decoration:none;font-weight:500;}
.cal a.cd.t{background:#2f7d33;color:#fff;font-weight:600;}
.cal a.cd.t:hover{background:#27692b;text-decoration:none;}
.cal .cd.today{box-shadow:inset 0 0 0 2px #7a5a34;}
.cal a.cd.t.today{box-shadow:inset 0 0 0 2px rgba(255,255,255,.85);}
.cal .cd.fut{opacity:.32;}
.cal .prt{position:absolute;top:-6px;right:-8px;width:13px;height:13px;color:#8a5a00;pointer-events:none;}
.cal .prt svg{width:13px;height:13px;display:block;}
.cal a.cd.t .prt{color:#ffe45e;}
.sesstop{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;}
.sesspg{display:flex;gap:2px;}
.iconbtn{display:inline-flex;padding:8px;border-radius:10px;color:inherit;}
.iconbtn:hover{background:rgba(127,122,110,.16);text-decoration:none;}
.iconbtn svg{width:22px;height:22px;display:block;}
#viewSession h1{font-size:2rem;}
.exgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px;margin-top:14px;}
.card.ex{padding:10px 14px;}
.ex h3{font-size:1rem;margin-bottom:4px;}
.ex h3 a{color:inherit;}
.ex table{font-size:.85rem;}
.ex td,.ex th{padding:4px 8px;}
.prbadge{display:inline-flex;vertical-align:-2px;margin-left:6px;color:#8a5a00;}
.prbadge svg{width:14px;height:14px;display:block;}
a{color:#7a5a34;text-decoration:none;}
a:visited{color:#7a5a34;}
a:hover{text-decoration:underline;}
#prs td a,#liftPRs td a{color:inherit;}
.ex td:nth-child(1),.ex td:nth-child(2),.ex td:nth-child(3){white-space:nowrap;}
.setnotes{margin-top:8px;font-size:.82rem;font-family:"IBM Plex Sans",sans-serif;color:#4e5148;}
.setnotes div{margin-top:4px;}
.setnotes b{margin-right:6px;}
@media (prefers-color-scheme:dark){
.cal .dw{color:#b0aca2;}
.cal .cd{color:#7f7a6e;}
.cal a.cd.t{background:#3d9a42;color:#fff;}
.cal a.cd.t:hover{background:#4cb052;}
.cal .cd.today{box-shadow:inset 0 0 0 2px #f0ede6;}
.cal a.cd.t.today{box-shadow:inset 0 0 0 2px rgba(255,255,255,.9);}
.cal .prt{color:#e6c400;}
.cal a.cd.t .prt{color:#ffe45e;}
.prbadge{background:none;color:#e6c400;}
.setnotes{color:#b0aca2;}
.iconbtn{color:#f0ede6;}
a{color:#f2a35e;}
a:visited{color:#f2a35e;}
}
table{width:100%;border-collapse:collapse;font-family:"IBM Plex Sans",sans-serif;font-size:.95rem;}
td,th{padding:7px 10px;border-bottom:1px solid #e5dfcd;text-align:left;}
thead th{font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;color:#4e5148;}
.empty{font-family:"IBM Plex Sans",sans-serif;color:#6e695c;padding:18px 4px;}
.tip{position:fixed;z-index:60;pointer-events:none;background:#fffdf7;border:1px solid #d9d3c0;border-radius:10px;padding:8px 12px;font-family:"IBM Plex Sans",sans-serif;font-size:.82rem;box-shadow:0 8px 24px rgba(0,0,0,.18);max-width:260px;}
.tip .tt{font-weight:600;margin-bottom:4px;}
.tip .tr{display:flex;align-items:center;gap:7px;margin-top:2px;}
.tip .sw{width:14px;height:3px;border-radius:2px;display:inline-block;flex:none;}
@media (prefers-color-scheme:dark){
body{background:#080807;color:#f0ede6;}
.stat,.card{background:#111010;border-color:#232120;}
.sub,.stat span,.cap,.notes,.legend,thead th{color:#b0aca2;}
h2{color:#f0ede6;}
td,th{border-color:#232120;}
.dot{background:#232120;}
.dot.t{background:#2f7d33;}
.tip{background:#171514;border-color:#3a3733;color:#f0ede6;}
}
</style></head><body><div class="wrap" id="viewDash">
<div class="kick">reps</div>
<h1>Training dashboard</h1>
<div class="sub" id="sub">loading</div>
<div><h2>Estimated 1RM trend</h2>
<div class="card"><div class="minigrid" id="trendGrid"></div><div class="legend" id="legTrend"></div><div class="cap">Best set per session, each lift on its own scale. Tap a lift for detail.</div></div></div>
<div class="cols2">
<div><h2>Weekly volume by muscle</h2>
<div class="card"><canvas id="chMus" width="860" height="250"></canvas><div class="legend" id="legMus"></div><div class="cap">One set can count for several muscles.</div></div>
<h2>Bodyweight</h2>
<div class="card"><canvas id="chBw" width="860" height="250"></canvas><div class="cap">Morning weigh ins, as logged in chat.</div></div></div>
<div><h2>Training calendar</h2>
<div class="card calcard"><div class="calhead"><button id="calPrev" type="button" aria-label="Previous month"><svg viewBox="0 0 16 16" width="18" height="18"><path d="M10 3 L5 8 L10 13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button><b id="calTitle"></b><button id="calNext" type="button" aria-label="Next month"><svg viewBox="0 0 16 16" width="18" height="18"><path d="M6 3 L11 8 L6 13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button></div><div class="cal" id="cal"></div><div class="cap">Tap a highlighted day for the session. Trophy marks a PR day.</div><div class="cap">Recent notes</div><ul class="notes" id="noteList"></ul></div></div>
</div>
<h2>Best sets</h2>
<div class="card"><table id="prs"><thead><tr><th>lift</th><th>best set by e1RM</th><th>date</th></tr></thead></table></div>
</div>
<div class="wrap" id="viewSession" hidden>
<div class="sesstop"><a class="iconbtn" href="#/" aria-label="back to dashboard"><svg viewBox="0 0 16 16" width="22" height="22"><path d="M14 8H3M7 4L3 8l4 4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></a><span class="sesspg"><a class="iconbtn" id="sessPrev" href="#/" aria-label="previous session"><svg viewBox="0 0 16 16" width="22" height="22"><path d="M10 3 L5 8 L10 13" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></a><a class="iconbtn" id="sessNext" href="#/" aria-label="next session"><svg viewBox="0 0 16 16" width="22" height="22"><path d="M6 3 L11 8 L6 13" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></a></span></div>
<h1 id="sessTitle">Session</h1>
<div id="sessNotes"></div>
<div id="sessBody" class="exgrid"></div>
</div>
<div class="wrap" id="viewLift" hidden>
<div class="sesstop"><a class="iconbtn" href="#/" aria-label="back to dashboard"><svg viewBox="0 0 16 16" width="22" height="22"><path d="M14 8H3M7 4L3 8l4 4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></a></div>
<h1 id="liftTitle">Lift</h1>
<div class="sub" id="liftSub"></div>
<div class="card"><canvas id="chLift" width="860" height="260"></canvas><div class="cap">Top set weight per session. Trophies mark sessions with an e1RM PR. Tap a point to open the session.</div></div>
<h2>PR history</h2>
<div class="card"><table id="liftPRs"><thead><tr><th>date</th><th>set</th><th>e1RM</th></tr></thead></table></div>
</div>
<script>
try { history.scrollRestoration = "manual"; } catch (e) {}
const LC = [];
for (let i = 0; i < 24; i += 1) {
  const h = Math.round((i * 137.5) % 360);
  LC.push("hsl(" + h + ",72%,62%)");
}
const TC = "#cfc9bc";
const GC = "#3a3733";
const MC = { chest: "#ffa726", back: "#66bb6a", shoulders: "#e6c400", biceps: "#42a5f5", triceps: "#ef5350", quads: "#ab47bc", hamstrings: "#26c6da", glutes: "#ec407a", abs: "#b0bec5" };
function fit(cv) {
  const dpr = window.devicePixelRatio || 1;
  const w = Math.max(50, cv.clientWidth), h = Math.max(50, cv.clientHeight);
  cv.width = Math.round(w * dpr);
  cv.height = Math.round(h * dpr);
  const g = cv.getContext("2d");
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { g, W: w, H: h };
}
function putText(g, W, str, x, y, align) {
  g.textAlign = align || "left";
  const w = g.measureText(str).width;
  if (align === "center") x = Math.min(Math.max(x, w / 2 + 2), W - w / 2 - 2);
  else if (align === "right") x = Math.min(x, W - 2);
  else x = Math.min(x, W - w - 2);
  g.fillText(str, Math.max(x, 2), y);
}
let SNAP = null;
let TREND = { days: [], series: [], top: [] };
let D = null;
let PR = null;
let VIEW = "dash";
let DASHY = 0;
let LIFTPTS = [];
const STARC = "#e6c400";
let TIP = null;
let BWDATA = [];
let LIFTDATA = null;
function tipRow(color, text) {
  const row = document.createElement("div");
  row.className = "tr";
  if (color) {
    const sw = document.createElement("span");
    sw.className = "sw";
    sw.style.background = color;
    row.appendChild(sw);
  }
  row.appendChild(document.createTextNode(text));
  return row;
}
function showTip(title, rows, x, y) {
  if (!TIP) {
    TIP = document.createElement("div");
    TIP.className = "tip";
    TIP.style.display = "none";
    document.body.appendChild(TIP);
  }
  TIP.innerHTML = "";
  const tt = document.createElement("div");
  tt.className = "tt";
  tt.textContent = title;
  TIP.appendChild(tt);
  rows.forEach(r => TIP.appendChild(tipRow(r[0], r[1])));
  TIP.style.display = "block";
  const w = TIP.offsetWidth;
  TIP.style.left = (x + 18 + w > window.innerWidth ? x - w - 18 : x + 18) + "px";
  TIP.style.top = (y + 20) + "px";
}
function hideTip() {
  if (TIP) TIP.style.display = "none";
}
function sliceIdx(x, cw, n) {
  if (n <= 1) return 0;
  const i = Math.round((x - 46) / ((cw - 46 - 8) / (n - 1)));
  return Math.min(n - 1, Math.max(0, i));
}
let HIDDEN = new Set();
let HADHIDDEN = false;
try {
  const raw = localStorage.getItem("reps-hidden");
  if (raw !== null) {
    HADHIDDEN = true;
    HIDDEN = new Set(JSON.parse(raw));
  }
} catch (e) {}
function saveHidden() {
  try {
    localStorage.setItem("reps-hidden", JSON.stringify(Array.from(HIDDEN)));
  } catch (e) {}
}
async function main(){
  SNAP = await (await fetch("snapshot")).json();
  render();
  let rt = null;
  window.addEventListener("resize", () => {
    if (rt) clearTimeout(rt);
    rt = setTimeout(render, 250);
  });
  const ch = document.getElementById("chLift");
  const near = ev => {
    const r = ch.getBoundingClientRect();
    const x = ev.clientX - r.left, y = ev.clientY - r.top;
    let bp = null, bd = 1e9;
    LIFTPTS.forEach(p => {
      const d = Math.abs(p.x - x) + Math.abs(p.y - y);
      if (d < bd) { bd = d; bp = p; }
    });
    return bd < 34 ? bp : null;
  };
  ch.addEventListener("click", ev => {
    const p = near(ev);
    if (p) location.hash = "#/s/" + p.date;
  });
  ch.addEventListener("mousemove", ev => {
    ch.style.cursor = near(ev) ? "pointer" : "default";
  });
  const bwCv = document.getElementById("chBw");
  bwCv.addEventListener("mousemove", ev => {
    if (!BWDATA.length) return;
    const r = bwCv.getBoundingClientRect();
    const idx = sliceIdx(ev.clientX - r.left, r.width, BWDATA.length);
    bwline(bwCv, BWDATA, idx);
    showTip(BWDATA[idx].date, [[null, BWDATA[idx].kg.toFixed(1) + " kg"]], ev.clientX, ev.clientY);
  });
  bwCv.addEventListener("mouseleave", () => { hideTip(); bwline(bwCv, BWDATA, -1); });
  const liftCv = document.getElementById("chLift");
  liftCv.addEventListener("mousemove", ev => {
    if (!LIFTDATA) return;
    const r = liftCv.getBoundingClientRect();
    const x = ev.clientX - r.left;
    let bi = -1, bd = 1e9;
    LIFTPTS.forEach((p, i) => {
      const d = Math.abs(p.x - x);
      if (d < bd) { bd = d; bi = i; }
    });
    if (bi < 0 || bd > 40) {
      hideTip();
      liftChart(liftCv, LIFTDATA.pts, LIFTDATA.ex, -1);
      liftCv.style.cursor = "default";
      return;
    }
    liftChart(liftCv, LIFTDATA.pts, LIFTDATA.ex, bi);
    const p = LIFTDATA.pts[bi];
    showTip(p.date, [[null, p.w + " x " + p.r + " (e1RM " + p.ev.toFixed(1) + ")" + (p.pr ? " PR" : "")]], ev.clientX, ev.clientY);
    liftCv.style.cursor = "pointer";
  });
  liftCv.addEventListener("mouseleave", () => {
    hideTip();
    if (LIFTDATA) liftChart(liftCv, LIFTDATA.pts, LIFTDATA.ex, -1);
    liftCv.style.cursor = "default";
  });
}
function render(){
  const snap = SNAP;
  const W = snap.workouts || [];
  const S = snap.sets || [];
  const BW = snap.bodyweight || [];
  document.getElementById("sub").textContent = W.length
    ? W.length + " sessions, latest " + fmtD(W.map(w => w.date).sort().pop())
    : "no sync yet, log your first session";
  const wdates = W.map(w => w.date).sort();
  const lastW = wdates.length ? wdates[wdates.length - 1] : null;
  const wdate0 = {};
  for (const w of W) wdate0[w.id] = w.date;
  const wday = s => wdate0[s.workout_id] || s.created.slice(0, 10);
  const T = S.filter(s => s.weight > 0);
  const byDate = {};
  for (const s of T) { const d = wday(s); (byDate[d] = byDate[d] || []).push(s); }
  const e1 = s => s.weight * (1 + s.reps / 30);
  const counts = {};
  for (const s of T) counts[s.exercise] = (counts[s.exercise] || 0) + 1;
  const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).map(e => e[0]);
  Array.from(HIDDEN).forEach(n => { if (top.indexOf(n) < 0) HIDDEN.delete(n); });
  if (!HADHIDDEN) top.slice(8).forEach(n => HIDDEN.add(n));
  saveHidden();
  const days = Object.keys(byDate).sort();
  const series = top.map(t => days.map(d => {
    const sets = byDate[d].filter(s => s.exercise === t);
    if (!sets.length) return null;
    return Math.max.apply(null, sets.map(e1));
  }));
  TREND = { days, series, top };
  PR = computePRs(W, S);
  refreshTrend();
  const noted = {};
  for (const w of W) if (w.notes) noted[w.date] = w.notes;
  for (const s of S) {
    if (s.note && s.note.toLowerCase().indexOf("grindy") > -1) {
      const d = wday(s);
      noted[d] = (noted[d] ? noted[d] + " / " : "") + s.exercise + ": " + s.note;
    }
  }
  const nl = document.getElementById("noteList");
  nl.innerHTML = "";
  Object.keys(noted).sort().slice(-6).forEach(d => {
    const li = document.createElement("li"); li.textContent = fmtD(d) + ": " + noted[d]; nl.appendChild(li);
  });
  bwline(document.getElementById("chBw"), BW);
  BWDATA = BW;
  const groups = GROUPS;
  const blank = () => ({ chest: 0, back: 0, shoulders: 0, biceps: 0, triceps: 0, quads: 0, hamstrings: 0, glutes: 0, abs: 0 });
  const weeks = {};
  for (const s of S) {
    const k = weekKey(wday(s));
    weeks[k] = weeks[k] || blank();
    const stored = (s.muscles || "").split(",").map(x => x.trim().toLowerCase()).filter(x => x);
    const gs = stored.length ? stored : [muscleOf(s.exercise)];
    gs.forEach(g => { if (g in weeks[k]) weeks[k][g] += 1; });
  }
  stacked(document.getElementById("chMus"), Object.keys(weeks).sort(), Object.keys(weeks).sort().map(k => weeks[k]));
  const lm = document.getElementById("legMus");
  lm.innerHTML = "";
  const mc = MC;
  groups.forEach(g => {
    const sp = document.createElement("span"); sp.className = "chip";
    const sw = document.createElement("span"); sw.className = "sw"; sw.style.background = mc[g];
    sp.appendChild(sw); sp.appendChild(document.createTextNode(g)); lm.appendChild(sp);
  });
  const dayDetail = {};
  for (const w of W) dayDetail[w.date] = dayDetail[w.date] || [];
  for (const s of S) {
    const d = wday(s);
    (dayDetail[d] = dayDetail[d] || []).push(s.exercise + " " + s.weight + "x" + s.reps);
  }
  const startView = lastW || new Date().toISOString().slice(0, 10);
  D = { W, S, BW };
  let viewY = parseInt(startView.slice(0, 4), 10);
  let viewM = parseInt(startView.slice(5, 7), 10) - 1;
  const drawCal = () => renderCal(viewY, viewM, dayDetail);
  document.getElementById("calPrev").addEventListener("click", () => {
    viewM -= 1;
    if (viewM < 0) { viewM = 11; viewY -= 1; }
    drawCal();
  });
  document.getElementById("calNext").addEventListener("click", () => {
    viewM += 1;
    if (viewM > 11) { viewM = 0; viewY += 1; }
    drawCal();
  });
  drawCal();
  const wdate = {};
  for (const w of W) wdate[w.id] = w.date;
  const prs = {};
  for (const s of S) {
    const k = s.exercise;
    const ev = s.weight * (1 + s.reps / 30);
    if (!prs[k] || ev > prs[k].ev) prs[k] = { s, ev };
  }
  const tbl = document.getElementById("prs");
  while (tbl.rows.length > 1) tbl.deleteRow(1);
  Object.keys(prs).sort().forEach(k => {
    const p = prs[k];
    const tr = document.createElement("tr");
    const a = document.createElement("td");
    const al = document.createElement("a");
    al.href = "#/l/" + encodeURIComponent(k);
    al.textContent = k;
    a.appendChild(al);
    const b2 = document.createElement("td"); b2.textContent = p.s.weight + " x " + p.s.reps + " (e1RM " + p.ev.toFixed(1) + ")";
    const c2 = document.createElement("td"); c2.textContent = fmtD(wdate[p.s.workout_id] || "");
    tr.appendChild(a); tr.appendChild(b2); tr.appendChild(c2); tbl.appendChild(tr);
  });
  route();
}
function computePRs(W, S) {
  const wdate = {};
  for (const w of W) wdate[w.id] = w.date;
  const order = S.slice().sort((a, b) => a.created < b.created ? -1 : a.created > b.created ? 1 : a.id - b.id);
  const best = {}, seen = new Set(), prIds = new Set(), prDates = new Set();
  order.forEach(s => {
    const ev = s.weight * (1 + s.reps / 30);
    if (!seen.has(s.exercise)) { seen.add(s.exercise); best[s.exercise] = ev; return; }
    if (ev > best[s.exercise]) { best[s.exercise] = ev; prIds.add(s.id); prDates.add(wdate[s.workout_id]); }
  });
  return { prIds, prDates };
}
function isDate(s) {
  if (!s || s.length !== 10 || s.charAt(4) !== "-" || s.charAt(7) !== "-") return false;
  for (let i = 0; i < 10; i += 1) {
    if (i === 4 || i === 7) continue;
    const c = s.charAt(i);
    if (c < "0" || c > "9") return false;
  }
  return true;
}
function route() {
  const h = location.hash || "";
  const ds = h.slice(0, 4) === "#/s/" ? h.slice(4, 14) : "";
  const lift = h.slice(0, 4) === "#/l/" ? decodeURIComponent(h.slice(4)) : "";
  if (ds && isDate(ds) && D) {
    if (VIEW === "dash") DASHY = window.scrollY;
    VIEW = "sess";
    showSession(ds);
  } else if (lift && D) {
    if (VIEW === "dash") DASHY = window.scrollY;
    VIEW = "lift";
    showLift(lift);
  } else {
    const restore = VIEW !== "dash";
    VIEW = "dash";
    document.getElementById("viewDash").hidden = false;
    document.getElementById("viewSession").hidden = true;
    document.getElementById("viewLift").hidden = true;
    document.title = "reps dashboard";
    if (restore) window.scrollTo(0, DASHY);
  }
}
function showSession(ds) {
  document.getElementById("viewDash").hidden = true;
  document.getElementById("viewLift").hidden = true;
  const v = document.getElementById("viewSession");
  v.hidden = false;
  const title = document.getElementById("sessTitle");
  const notes = document.getElementById("sessNotes");
  const body = document.getElementById("sessBody");
  const prev = document.getElementById("sessPrev");
  const next = document.getElementById("sessNext");
  notes.innerHTML = "";
  body.innerHTML = "";
  const ws = D.W.filter(w => w.date === ds);
  const dates = Array.from(new Set(D.W.map(w => w.date))).sort();
  const ix = dates.indexOf(ds);
  if (ix > 0) {
    prev.style.visibility = "";
    prev.href = "#/s/" + dates[ix - 1];
    prev.setAttribute("aria-label", "previous session " + fmtD(dates[ix - 1]));
  } else prev.style.visibility = "hidden";
  if (ix >= 0 && ix < dates.length - 1) {
    next.style.visibility = "";
    next.href = "#/s/" + dates[ix + 1];
    next.setAttribute("aria-label", "next session " + fmtD(dates[ix + 1]));
  } else next.style.visibility = "hidden";
  if (!ws.length) {
    title.textContent = fmtD(ds);
    document.title = fmtD(ds) + " no session";
    window.scrollTo(0, 0);
    return;
  }
  title.textContent = new Date(ds + "T12:00:00").toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });
  const wnotes = ws.map(w => w.notes).filter(n => n);
  if (wnotes.length) {
    const d = document.createElement("div");
    d.className = "card";
    d.textContent = wnotes.join(" / ");
    notes.appendChild(d);
  }
  ws.forEach(w => {
    const sets = D.S.filter(s => s.workout_id === w.id);
    const order = [], byEx = {};
    sets.forEach(s => {
      (byEx[s.exercise] = byEx[s.exercise] || []).push(s);
      if (order.indexOf(s.exercise) < 0) order.push(s.exercise);
    });
    order.forEach(ex => {
      const wrap = document.createElement("div");
      wrap.className = "card ex";
      const h = document.createElement("h3");
      const hl = document.createElement("a");
      hl.href = "#/l/" + encodeURIComponent(ex);
      hl.textContent = ex;
      h.appendChild(hl);
      wrap.appendChild(h);
      const tbl = document.createElement("table");
      tbl.className = "sess";
      const thead = document.createElement("thead");
      const head = document.createElement("tr");
      ["set", "weight", "e1RM"].forEach(t => {
        const th = document.createElement("th");
        th.setAttribute("scope", "col");
        th.textContent = t;
        head.appendChild(th);
      });
      thead.appendChild(head);
      tbl.appendChild(thead);
      const tbody = document.createElement("tbody");
      tbl.appendChild(tbody);
      const sn = [];
      byEx[ex].forEach((s, i) => {
        const tr = document.createElement("tr");
        const ev = s.weight * (1 + s.reps / 30);
        const cells = [String(i + 1), s.weight + " x " + s.reps, ev.toFixed(1)];
        cells.forEach(c => {
          const td = document.createElement("td");
          td.textContent = c;
          tr.appendChild(td);
        });
        if (PR.prIds.has(s.id)) {
          const b = document.createElement("span");
          b.className = "prbadge";
          b.title = "personal record";
          b.innerHTML = '<svg viewBox="0 0 16 16"><path d="M5 1.5h6v4.2a3 3 0 0 1-6 0V1.5z" fill="currentColor"/><path d="M5 2.5H3.2a2.8 2.8 0 0 0 2.9 3.6M11 2.5h1.8a2.8 2.8 0 0 1-2.9 3.6" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M8 8.7v2.1M6.2 12.8h3.6M5.4 14.5h5.2" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>';
          tr.children[1].appendChild(b);
        }
        if (s.note) sn.push([i + 1, s.note]);
        tbody.appendChild(tr);
      });
      wrap.appendChild(tbl);
      if (sn.length) {
        const nd = document.createElement("div");
        nd.className = "setnotes";
        sn.forEach(pair => {
          const ln = document.createElement("div");
          const b = document.createElement("b");
          b.textContent = pair[0];
          ln.appendChild(b);
          ln.appendChild(document.createTextNode(pair[1]));
          nd.appendChild(ln);
        });
        wrap.appendChild(nd);
      }
      body.appendChild(wrap);
    });
  });
  document.title = fmtD(ds) + " training";
  window.scrollTo(0, 0);
}
function showLift(ex) {
  document.getElementById("viewDash").hidden = true;
  document.getElementById("viewSession").hidden = true;
  const v = document.getElementById("viewLift");
  v.hidden = false;
  const title = document.getElementById("liftTitle");
  const sub = document.getElementById("liftSub");
  const tbl = document.getElementById("liftPRs");
  while (tbl.rows.length > 1) tbl.deleteRow(1);
  title.textContent = ex;
  document.title = ex;
  const sets = D.S.filter(s => s.exercise === ex);
  if (!sets.length) {
    sub.textContent = "never logged";
    LIFTPTS = [];
    LIFTDATA = null;
    liftChart(document.getElementById("chLift"), [], ex);
    window.scrollTo(0, 0);
    return;
  }
  const wdate = {};
  for (const w of D.W) wdate[w.id] = w.date;
  const byDate = {};
  sets.forEach(s => {
    const d = wdate[s.workout_id];
    (byDate[d] = byDate[d] || []).push(s);
  });
  const pts = Object.keys(byDate).sort().map(d => {
    const top = byDate[d].slice().sort((a, b) => b.weight - a.weight || b.reps - a.reps)[0];
    return { date: d, w: top.weight, r: top.reps, ev: top.weight * (1 + top.reps / 30), pr: byDate[d].some(s => PR.prIds.has(s.id)) };
  });
  const best = pts.slice().sort((a, b) => b.ev - a.ev)[0];
  sub.textContent = "best " + best.w + " x " + best.r + " (e1RM " + best.ev.toFixed(1) + ") on " + fmtD(best.date);
  LIFTDATA = { pts, ex };
  liftChart(document.getElementById("chLift"), pts, ex);
  const order = D.S.slice().sort((a, b) => a.created < b.created ? -1 : a.created > b.created ? 1 : a.id - b.id);
  const seen = new Set(), top2 = { ev: 0 };
  order.forEach(s => {
    if (s.exercise !== ex) return;
    const ev = s.weight * (1 + s.reps / 30);
    if (!seen.has(ex)) { seen.add(ex); top2.ev = ev; return; }
    if (ev > top2.ev) {
      top2.ev = ev;
      const tr = document.createElement("tr");
      const a = document.createElement("td");
      const al = document.createElement("a");
      al.href = "#/s/" + wdate[s.workout_id];
      al.textContent = fmtD(wdate[s.workout_id]);
      a.appendChild(al);
      const b2 = document.createElement("td");
      b2.textContent = s.weight + " x " + s.reps;
      const c2 = document.createElement("td");
      c2.textContent = ev.toFixed(1);
      tr.appendChild(a); tr.appendChild(b2); tr.appendChild(c2);
      tbl.appendChild(tr);
    }
  });
  window.scrollTo(0, 0);
}
function trophy(g, x, y, r, color) {
  const s = r / 8;
  g.save();
  g.translate(x, y);
  g.scale(s, s);
  g.fillStyle = color;
  g.strokeStyle = color;
  g.lineWidth = 1.4;
  g.lineCap = "round";
  g.beginPath();
  g.moveTo(-3, -6.5);
  g.lineTo(3, -6.5);
  g.lineTo(3, -2.3);
  g.arc(0, -2.3, 3, 0, Math.PI, false);
  g.closePath();
  g.fill();
  g.beginPath();
  g.arc(-3.6, -4.2, 1.8, Math.PI * 0.4, Math.PI * 1.4, true);
  g.stroke();
  g.beginPath();
  g.arc(3.6, -4.2, 1.8, Math.PI * 1.6, Math.PI * 0.6, true);
  g.stroke();
  g.beginPath();
  g.moveTo(0, 0.7);
  g.lineTo(0, 2.8);
  g.moveTo(-1.8, 4.8);
  g.lineTo(1.8, 4.8);
  g.moveTo(-2.6, 6.5);
  g.lineTo(2.6, 6.5);
  g.stroke();
  g.restore();
}
function liftChart(cv, pts, ex, hover) {
  const f = fit(cv);
  const g = f.g, W = f.W, H = f.H, P = 46;
  g.clearRect(0, 0, W, H);
  g.font = "600 12px sans-serif";
  LIFTPTS = [];
  if (!pts.length) {
    g.fillStyle = TC;
    putText(g, W, "no sets logged for this lift yet", P, H / 2, "left");
    return;
  }
  const d0 = pts[0].date;
  const todayS = new Date().toISOString().slice(0, 10);
  const d1 = pts[pts.length - 1].date > todayS ? pts[pts.length - 1].date : todayS;
  const t0 = new Date(d0 + "T12:00:00").getTime();
  const t1 = new Date(d1 + "T12:00:00").getTime();
  const span = Math.max(1, t1 - t0);
  const px = dt => P + (W - P - 8) * ((new Date(dt + "T12:00:00").getTime() - t0) / span);
  let mn = Infinity, mx = 0;
  pts.forEach(p => { if (p.w < mn) mn = p.w; if (p.w > mx) mx = p.w; });
  const pad = (mx - mn) * 0.25 || Math.max(1, mx * 0.05);
  mn = Math.max(0, mn - pad);
  mx += pad;
  const t = niceTicks(mn, mx, 4);
  mn = t.lo; mx = t.hi;
  const py = v => H - P - (H - P - 18) * ((v - mn) / (mx - mn));
  const nt = Math.round((t.hi - t.lo) / t.step);
  for (let i = 0; i <= nt; i += 1) {
    const v = parseFloat((t.lo + i * t.step).toPrecision(12));
    const y = H - P - (H - P - 18) * i / nt;
    g.strokeStyle = GC; g.lineWidth = 1;
    g.beginPath(); g.moveTo(P, y); g.lineTo(W - 8, y); g.stroke();
    if (i % 2 === 0 || i === nt) {
      g.fillStyle = TC;
      putText(g, W, fmtTick(v, t.step), 4, y + 4, "left");
    }
  }
  let ci = TREND.top.indexOf(ex);
  if (ci < 0) ci = 0;
  const col = LC[ci % LC.length];
  g.strokeStyle = col; g.lineWidth = 3; g.lineJoin = "round";
  g.beginPath();
  pts.forEach((p, i) => { if (i === 0) g.moveTo(px(p.date), py(p.w)); else g.lineTo(px(p.date), py(p.w)); });
  g.stroke();
  pts.forEach(p => {
    const x = px(p.date), y = py(p.w);
    LIFTPTS.push({ x, y, date: p.date });
    if (p.pr) trophy(g, x, y - 14, 7, STARC);
    else { g.fillStyle = col; g.beginPath(); g.arc(x, y, 4, 0, 7); g.fill(); }
  });
  g.fillStyle = TC;
  putText(g, W, fmtD(pts[0].date), P, H - 8, "left");
  putText(g, W, fmtD(pts[pts.length - 1].date), W - 8, H - 8, "right");
  putText(g, W, fmtV(pts[0].w) + " start", P + 4, py(pts[0].w) - 12, "left");
  const last = pts[pts.length - 1];
  putText(g, W, fmtV(last.w) + " now", W - 8, last.pr ? py(last.w) + 24 : py(last.w) - 12, "right");
  if (hover !== undefined && hover >= 0 && hover < pts.length) {
    const p = pts[hover];
    const x = px(p.date);
    g.strokeStyle = TC; g.globalAlpha = 0.45; g.lineWidth = 1;
    g.beginPath(); g.moveTo(x, 14); g.lineTo(x, H - P); g.stroke();
    g.globalAlpha = 1;
    if (p.pr) trophy(g, x, py(p.w) - 14, 10, STARC);
    else {
      g.fillStyle = col;
      g.beginPath(); g.arc(x, py(p.w), 6, 0, 7); g.fill();
    }
  }
}
window.addEventListener("hashchange", route);
const GROUPS = ["chest", "back", "shoulders", "biceps", "triceps", "quads", "hamstrings", "glutes", "abs"];
function muscleOf(n) {
  n = n.toLowerCase();
  if (/(leg curl|nordic|hamstring|good morning|romanian|rdl|deadlift)/.test(n)) return "hamstrings";
  if (/(tricep|pushdown|skull)/.test(n)) return "triceps";
  if (/(bench|chest|fly|pushup|push up|dips|incline)/.test(n)) return "chest";
  if (/(overhead|ohp|shoulder|lateral|rear delt|face pull|arnold)/.test(n)) return "shoulders";
  if (/(pullup|chinup|pulldown|pendlay|pullover| lat | rows| row )/.test(" " + n + " ")) return "back";
  if (/(bicep|curl|hammer|preacher)/.test(n)) return "biceps";
  if (/(squat|leg press|lunge|leg extension|hack)/.test(n)) return "quads";
  if (/(hip thrust|glute|hip abduct)/.test(n)) return "glutes";
  if (/(crunch|plank|leg raise|knee raise|hanging|abs|core|ab wheel)/.test(n)) return "abs";
  return "other";
}
// Unmapped lifts fall into other and are excluded from the volume chart. Extend the patterns above when the split changes, mirroring MEMORY.md Tracked muscles.
function renderCal(year, month, dayDetail) {
  const names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  document.getElementById("calTitle").textContent = names[month] + " " + year;
  const box = document.getElementById("cal");
  box.innerHTML = "";
  hideTip();
  ["M", "T", "W", "T", "F", "S", "S"].forEach(d => {
    const h = document.createElement("div"); h.className = "dw"; h.textContent = d; box.appendChild(h);
  });
  const first = new Date(year, month, 1);
  let lead = first.getDay() - 1;
  if (lead < 0) lead = 6;
  for (let i = 0; i < lead; i += 1) box.appendChild(document.createElement("div"));
  const days = new Date(year, month + 1, 0).getDate();
  const todayS = new Date().toISOString().slice(0, 10);
  const wByDate = {};
  if (D && D.W) for (const w of D.W) { (wByDate[w.date] = wByDate[w.date] || []).push(w); }
  const sByDate = {};
  const wid2date = {};
  if (D && D.W) for (const w of D.W) wid2date[w.id] = w.date;
  if (D && D.S) for (const s of D.S) {
    const d = wid2date[s.workout_id] || (s.created || "").slice(0, 10);
    (sByDate[d] = sByDate[d] || []).push(s);
  }
  for (let d = 1; d <= days; d += 1) {
    const key = year + "-" + String(month + 1).padStart(2, "0") + "-" + String(d).padStart(2, "0");
    const trained = dayDetail[key] && dayDetail[key].length > 0;
    const isPR = PR && PR.prDates.has(key);
    const el = document.createElement(trained ? "a" : "div");
    if (trained) el.href = "#/s/" + key;
    el.className = "cd" + (trained ? " t" : "") + (key === todayS ? " today" : "") + (key > todayS ? " fut" : "");
    el.textContent = String(d);
    if (isPR) {
      const tr = document.createElement("span");
      tr.className = "prt";
      tr.title = "personal record";
      tr.innerHTML = '<svg viewBox="0 0 16 16"><path d="M5 1.5h6v4.2a3 3 0 0 1-6 0V1.5z" fill="currentColor"/><path d="M5 2.5H3.2a2.8 2.8 0 0 0 2.9 3.6M11 2.5h1.8a2.8 2.8 0 0 1-2.9 3.6" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M8 8.7v2.1M6.2 12.8h3.6M5.4 14.5h5.2" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>';
      el.appendChild(tr);
    }
    if (trained) {
      el.addEventListener("click", hideTip);
      el.addEventListener("mousemove", ev => {
        const sets = sByDate[key] || [];
        const order = [];
        const byEx = {};
        sets.forEach(s => {
          (byEx[s.exercise] = byEx[s.exercise] || []).push(s);
          if (order.indexOf(s.exercise) < 0) order.push(s.exercise);
        });
        const rows = [];
        order.slice(0, 6).forEach(ex => {
          const g = byEx[ex];
          const top = g.slice().sort((a, b) => b.weight - a.weight || b.reps - a.reps)[0];
          const hasPR = g.some(s => PR && PR.prIds.has(s.id));
          rows.push([hasPR ? "#e6c400" : null, ex + " " + g.length + " x " + top.weight + "x" + top.reps + (hasPR ? " PR" : "")]);
        });
        if (order.length > 6) rows.push([null, "+" + (order.length - 6) + " more lifts"]);
        const wnotes = (wByDate[key] || []).map(w => w.notes).filter(n => n);
        if (wnotes.length && rows.length < 7) {
          const n = wnotes.join(" / ");
          rows.push([null, n.length > 90 ? n.slice(0, 90) + "..." : n]);
        }
        const title = new Date(key + "T12:00:00").toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" }) + (isPR ? "  PR" : "");
        showTip(title, rows.length ? rows : [[null, "tap to open"]], ev.clientX, ev.clientY);
      });
      el.addEventListener("mouseleave", hideTip);
    }
    box.appendChild(el);
  }
}
function shift(dstr, n) {
  const d = new Date(dstr + "T12:00:00");
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}
function weekKey(dstr) {
  const d = new Date(dstr + "T12:00:00");
  const one = new Date(d.getFullYear(), 0, 1);
  const wk = Math.ceil((((d - one) / 86400000) + one.getDay() + 1) / 7);
  return d.getFullYear() + " W" + wk;
}
function fmtV(v) {
  return v >= 100 ? String(Math.round(v)) : v.toFixed(1);
}
function fmtD(dstr) {
  const M = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return M[parseInt(dstr.slice(5, 7), 10) - 1] + " " + parseInt(dstr.slice(8, 10), 10);
}
function niceTicks(mn, mx, count) {
  let span = mx - mn;
  if (!(span > 0)) span = Math.abs(mx) || 1;
  const raw = span / count;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const cands = [1, 2, 2.5, 5, 10];
  let step = 10 * mag;
  for (let i = 0; i < cands.length; i += 1) {
    if (raw / (cands[i] * mag) <= count) { step = cands[i] * mag; break; }
  }
  step = parseFloat(step.toPrecision(12));
  const lo = parseFloat((Math.floor(mn / step) * step).toPrecision(12));
  const hi = parseFloat((Math.ceil(mx / step) * step).toPrecision(12));
  return { lo, hi: hi <= lo ? lo + step : hi, step };
}
function fmtTick(v, step) {
  const dec = step >= 1 ? 0 : Math.min(2, -Math.floor(Math.log10(step) + 1e-9));
  return v.toFixed(dec);
}
function refreshTrend() {
  drawTrendChips();
  drawMinis();
}
function drawMinis() {
  const grid = document.getElementById("trendGrid");
  grid.innerHTML = "";
  const shown = TREND.top.map((t, i) => i).filter(i => !HIDDEN.has(TREND.top[i]));
  if (!shown.length) {
    const e = document.createElement("div");
    e.className = "empty";
    e.textContent = "everything hidden, use All to bring lifts back";
    grid.appendChild(e);
    return;
  }
  const wd = {};
  for (const w of SNAP.workouts) wd[w.id] = w.date;
  const prDate = {};
  for (const s of SNAP.sets) {
    if (PR && PR.prIds.has(s.id)) (prDate[s.exercise] = prDate[s.exercise] || {})[wd[s.workout_id] || ""] = true;
  }
  const jobs = [];
  shown.forEach(i => {
    const t = TREND.top[i];
    const vals = TREND.series[i];
    const wrap = document.createElement("div");
    wrap.className = "mini";
    const h = document.createElement("div");
    h.className = "minititle";
    const al = document.createElement("a");
    al.href = "#/l/" + encodeURIComponent(t);
    al.textContent = t;
    h.appendChild(al);
    wrap.appendChild(h);
    const cv = document.createElement("canvas");
    wrap.appendChild(cv);
    wrap.addEventListener("click", ev => {
      if (ev.target.tagName !== "A") location.hash = "#/l/" + encodeURIComponent(t);
    });
    grid.appendChild(wrap);
    const col = LC[i % LC.length], prs = prDate[t] || {};
    jobs.push([cv, vals, col, prs]);
    cv.addEventListener("mousemove", ev => {
      const r = cv.getBoundingClientRect();
      const n = vals.length;
      const pxi = k => 30 + (r.width - 30 - 6) * (n <= 1 ? 1 : k / (n - 1));
      let bi = -1, bd = 1e9;
      for (let k = 0; k < n; k += 1) {
        if (vals[k] === null) continue;
        const d = Math.abs(pxi(k) - (ev.clientX - r.left));
        if (d < bd) { bd = d; bi = k; }
      }
      if (bi < 0 || bd > 30) {
        hideTip();
        mini(cv, TREND.days, vals, col, prs);
        return;
      }
      mini(cv, TREND.days, vals, col, prs, bi);
      showTip(TREND.days[bi], [[col, fmtV(vals[bi]) + (prs[TREND.days[bi]] ? " PR" : "")]], ev.clientX, ev.clientY);
    });
    cv.addEventListener("mouseleave", () => {
      hideTip();
      mini(cv, TREND.days, vals, col, prs);
    });
  });
  jobs.forEach(j => mini(j[0], TREND.days, j[1], j[2], j[3]));
}
function mini(cv, days, vals, col, prs, hover) {
  const f = fit(cv);
  const g = f.g, W = f.W, H = f.H, P = 30;
  g.clearRect(0, 0, W, H);
  g.font = "600 11px sans-serif";
  const pts = [];
  for (let i = 0; i < vals.length; i += 1) if (vals[i] !== null) pts.push(i);
  if (!pts.length) {
    g.fillStyle = TC;
    putText(g, W, "no data", P, H / 2, "left");
    return;
  }
  let mn = Infinity, mx = 0;
  pts.forEach(pi => { const v = vals[pi]; if (v < mn) mn = v; if (v > mx) mx = v; });
  if (!(mx > mn)) mx = mn + 1;
  const pad = (mx - mn) * 0.3 || 1;
  mn = Math.max(0, mn - pad); mx += pad;
  const t = niceTicks(mn, mx, 2);
  mn = t.lo; mx = t.hi;
  const n = vals.length;
  const px = i => P + (W - P - 6) * (n <= 1 ? 1 : i / (n - 1));
  const py = v => H - 15 - (H - 15 - 6) * ((v - mn) / (mx - mn));
  const nt = Math.round((t.hi - t.lo) / t.step);
  for (let i = 0; i <= nt; i += 1) {
    const v = parseFloat((t.lo + i * t.step).toPrecision(12));
    const y = H - 15 - (H - 15 - 6) * i / nt;
    g.strokeStyle = GC; g.lineWidth = 1;
    g.beginPath(); g.moveTo(P, y); g.lineTo(W - 6, y); g.stroke();
    g.fillStyle = TC;
    putText(g, W, fmtTick(v, t.step), 2, y + 3, "left");
  }
  g.strokeStyle = col; g.lineWidth = 2.5; g.lineJoin = "round"; g.beginPath();
  pts.forEach((pi, k) => { if (k === 0) g.moveTo(px(pi), py(vals[pi])); else g.lineTo(px(pi), py(vals[pi])); });
  g.stroke();
  g.fillStyle = col;
  pts.forEach(pi => { g.beginPath(); g.arc(px(pi), py(vals[pi]), 2.5, 0, 7); g.fill(); });
  pts.forEach(pi => { if (prs[days[pi]]) trophy(g, px(pi), py(vals[pi]) - 9, 5, STARC); });
  const li = pts[pts.length - 1];
  g.fillStyle = col;
  if (li > n / 2) putText(g, W, fmtV(vals[li]), px(li) - 8, py(vals[li]) - 10, "right");
  else putText(g, W, fmtV(vals[li]), px(li) + 8, py(vals[li]) - 10, "left");
  if (hover !== undefined && hover >= 0 && hover < n && vals[hover] !== null) {
    const x = px(hover);
    g.strokeStyle = TC; g.globalAlpha = 0.45; g.lineWidth = 1;
    g.beginPath(); g.moveTo(x, 6); g.lineTo(x, H - 15); g.stroke();
    g.globalAlpha = 1;
    g.fillStyle = col;
    g.beginPath(); g.arc(x, py(vals[hover]), 5, 0, 7); g.fill();
  }
  g.fillStyle = TC;
  if (days.length > 1) {
    putText(g, W, fmtD(days[0]), P, H - 1, "left");
    putText(g, W, fmtD(days[days.length - 1]), W - 6, H - 1, "right");
  }
}
function drawTrendChips() {
  const lt = document.getElementById("legTrend");
  lt.innerHTML = "";
  [["All", false], ["None", true]].forEach(pair => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "chip mini";
    b.textContent = pair[0];
    b.addEventListener("click", () => {
      HADHIDDEN = true;
      if (pair[1]) TREND.top.forEach(t => HIDDEN.add(t));
      else HIDDEN.clear();
      saveHidden();
      refreshTrend();
    });
    lt.appendChild(b);
  });
  TREND.top.forEach((t, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "chip" + (HIDDEN.has(t) ? " off" : "");
    b.setAttribute("aria-pressed", HIDDEN.has(t) ? "false" : "true");
    const sw = document.createElement("span");
    sw.className = "sw";
    sw.style.background = LC[i % LC.length];
    b.appendChild(sw);
    b.appendChild(document.createTextNode(t));
    b.addEventListener("click", () => {
      HADHIDDEN = true;
      if (HIDDEN.has(t)) HIDDEN.delete(t); else HIDDEN.add(t);
      saveHidden();
      refreshTrend();
    });
    lt.appendChild(b);
  });
}
function bwline(cv, rows, hover) {
  const f = fit(cv);
  const g = f.g, W = f.W, H = f.H, P = 46;
  if (!rows.length) {
    g.clearRect(0, 0, W, H);
    g.fillStyle = TC; g.font = "600 14px sans-serif";
    g.fillText("no weigh ins yet, say your morning weight in chat", P, H / 2);
    return;
  }
  const vals = rows.map(r => r.kg);
  let mn = Math.min.apply(null, vals), mx = Math.max.apply(null, vals);
  const pad = (mx - mn) * 0.5 || 1;
  mn -= pad; mx += pad;
  const t = niceTicks(mn, mx, 3);
  mn = t.lo; mx = t.hi;
  g.clearRect(0, 0, W, H);
  g.font = "600 12px sans-serif";
  const nt = Math.round((t.hi - t.lo) / t.step);
  for (let i = 0; i <= nt; i += 1) {
    const v = parseFloat((t.lo + i * t.step).toPrecision(12));
    const y = H - P - (H - P - 18) * i / nt;
    g.strokeStyle = GC; g.lineWidth = 1;
    g.beginPath(); g.moveTo(P, y); g.lineTo(W - 8, y); g.stroke();
    if (i % 2 === 0 || i === nt) {
      g.fillStyle = TC;
      putText(g, W, fmtTick(v, t.step), 4, y + 4, "left");
    }
  }
  const px = i => P + (W - P - 8) * (rows.length === 1 ? 1 : i / (rows.length - 1));
  const py = v => H - P - (H - P - 16) * ((v - mn) / (mx - mn));
  g.strokeStyle = LC[0]; g.lineWidth = 3; g.lineJoin = "round"; g.beginPath();
  rows.forEach((r, i) => { if (i === 0) g.moveTo(px(i), py(r.kg)); else g.lineTo(px(i), py(r.kg)); });
  g.stroke();
  g.fillStyle = LC[0];
  g.textAlign = "center";
  rows.forEach((r, i) => {
    g.beginPath(); g.arc(px(i), py(r.kg), 5, 0, 7); g.fill();
    g.fillStyle = TC;
    if (i === 0) putText(g, W, r.kg.toFixed(1), px(i) + 8, py(r.kg) - 12, "left");
    else if (i === rows.length - 1) putText(g, W, r.kg.toFixed(1), px(i) - 8, py(r.kg) - 12, "right");
    else putText(g, W, r.kg.toFixed(1), px(i), py(r.kg) - 12, "center");
    g.fillStyle = LC[0];
  });
  g.fillStyle = TC;
  putText(g, W, fmtD(rows[0].date), P, H - 8, "left");
  putText(g, W, fmtD(rows[rows.length - 1].date), W - 8, H - 8, "right");
  if (hover !== undefined && hover >= 0 && hover < rows.length) {
    const x = px(hover);
    g.strokeStyle = TC; g.globalAlpha = 0.45; g.lineWidth = 1;
    g.beginPath(); g.moveTo(x, 14); g.lineTo(x, H - P); g.stroke();
    g.globalAlpha = 1;
    g.fillStyle = LC[0];
    g.beginPath(); g.arc(x, py(rows[hover].kg), 7, 0, 7); g.fill();
  }
}
function stacked(cv, labels, weeks) {
  const f = fit(cv);
  const g = f.g, W = f.W, H = f.H, P = 46;
  g.clearRect(0, 0, W, H);
  const groups = GROUPS;
  let mx = 1;
  weeks.forEach(w => {
    const t = groups.reduce((a, k) => a + w[k], 0);
    if (t > mx) mx = t;
  });
  const bw = (W - P - 8) / Math.max(1, weeks.length);
  const area = H - P - 42;
  const t = niceTicks(0, mx, 3);
  mx = t.hi;
  g.font = "600 12px sans-serif";
  const nt = Math.round((t.hi - t.lo) / t.step);
  for (let i = 0; i <= nt; i += 1) {
    const v = parseFloat((t.lo + i * t.step).toPrecision(12));
    const y = H - P - area * (i / nt);
    g.strokeStyle = GC; g.lineWidth = 1;
    g.beginPath(); g.moveTo(P, y); g.lineTo(W - 8, y); g.stroke();
    if (i % 2 === 0 || i === nt) {
      g.fillStyle = TC;
      putText(g, W, fmtTick(v, t.step), 4, y + 4, "left");
    }
  }
  weeks.forEach((w, i) => {
    let y0 = H - P;
    groups.forEach(gr => {
      const h = area * (w[gr] / mx);
      g.fillStyle = MC[gr];
      g.fillRect(P + i * bw + 3, y0 - h, bw - 6, h);
      y0 -= h;
    });
    const total = groups.reduce((a, k) => a + w[k], 0);
    const top = H - P - area * (total / mx);
    g.fillStyle = TC;
    putText(g, W, String(total), P + i * bw + bw / 2, top - 10, "center");
    putText(g, W, labels[i], P + i * bw + bw / 2, H - 8, "center");
  });
}
main();
</script></body></html>`;

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    if (req.method === "PUT" && url.pathname === "/sync") {
      const auth = req.headers.get("authorization") || "";
      if (!env.SYNC_SECRET || auth !== "Bearer " + env.SYNC_SECRET) {
        return Response.json({ error: "unauthorized" }, { status: 401 });
      }
      const raw = await req.text();
      if (raw.length > 2000000) {
        return Response.json({ error: "snapshot too large" }, { status: 413 });
      }
      try {
        JSON.parse(raw);
      } catch {
        return Response.json({ error: "not json" }, { status: 400 });
      }
      await env.SNAPSHOTS.put("snapshot.json", raw, {
        httpMetadata: { contentType: "application/json" },
      });
      return Response.json({ ok: true, bytes: raw.length });
    }
    if (url.pathname === "/snapshot") {
      const obj = await env.SNAPSHOTS.get("snapshot.json");
      if (!obj) return Response.json(BLANK);
      return new Response(obj.body, {
        headers: { "content-type": "application/json" },
      });
    }
    if (url.pathname !== "/") {
      return new Response("not found", { status: 404 });
    }
    return new Response(PAGE, { headers: { "content-type": "text/html" } });
  },
};
