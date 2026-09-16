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

function muscleOf(name: string): string {
  const n = name.toLowerCase();
  if (/(press|bench|dips|pushup|overhead|ohp|lateral|tricep|shoulder|chest)/.test(n)) return "push";
  if (/(row|pullup|pulldown|curl|chinup|bicep|lat|rear delt)/.test(n)) return "pull";
  if (/(squat|deadlift|leg|lunge|calf|rdl|hip)/.test(n)) return "legs";
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
.wrap{max-width:880px;margin:0 auto;}
.kick{font-family:"IBM Plex Sans",sans-serif;font-size:.8rem;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:#75603a;margin-bottom:8px;}
h1{font-size:2.6rem;letter-spacing:-.02em;margin-bottom:6px;}
.sub{font-family:"IBM Plex Sans",sans-serif;color:#4e5148;margin-bottom:26px;}
h2{font-size:1.35rem;margin:34px 0 10px;}
.card{background:#fffdf7;border:1px solid #d9d3c0;border-radius:14px;padding:16px;margin:12px 0;}
canvas{width:100%;height:230px;display:block;}
.legend{display:flex;flex-wrap:wrap;gap:8px 16px;margin-top:10px;font-family:"IBM Plex Sans",sans-serif;font-size:.85rem;}
.chip{display:inline-flex;align-items:center;gap:7px;}
button.chip{background:none;border:1px solid transparent;border-radius:8px;padding:4px 8px;cursor:pointer;color:inherit;font-family:inherit;font-size:.85rem;}
button.chip.off{opacity:.35;}
.sw{width:22px;height:4px;border-radius:2px;display:inline-block;}
.cap{font-family:"IBM Plex Sans",sans-serif;font-size:.88rem;color:#4e5148;margin-top:10px;}
.notes{font-family:"IBM Plex Sans",sans-serif;font-size:.88rem;color:#4e5148;margin-top:10px;}
.notes li{margin-bottom:4px;margin-left:20px;}
.calcard{max-width:430px;}
.calhead{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;font-family:"IBM Plex Sans",sans-serif;}
.calhead b{font-size:1rem;}
.calhead button{background:none;border:none;padding:6px;cursor:pointer;color:inherit;display:flex;}
.calhead button svg{width:18px;height:18px;}
.cal{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;font-family:"IBM Plex Sans",sans-serif;font-size:.82rem;}
.cal .dw{font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;color:#4e5148;text-align:center;padding:3px 0;}
.cal .cd{aspect-ratio:1;border-radius:9px;background:#f5f2e9;display:flex;align-items:center;justify-content:center;color:#6e695c;position:relative;text-decoration:none;}
.cal .cd.t{background:#2f7d33;color:#fff;font-weight:600;}
.cal .cd.today{outline:2px solid #7a5a34;outline-offset:-2px;}
.cal .cd.fut{background:none;}
.cal .cd.pr::after{content:"";position:absolute;bottom:4px;left:50%;margin-left:-3px;width:6px;height:6px;border-radius:50%;background:#8a5a00;}
.sesstop{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;}
.sesspg{display:flex;gap:2px;}
.iconbtn{display:inline-flex;padding:8px;border-radius:10px;color:inherit;}
.iconbtn:hover{background:rgba(127,122,110,.16);text-decoration:none;}
.iconbtn svg{width:22px;height:22px;display:block;}
#viewSession h1{font-size:2rem;}
.exgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px;margin-top:14px;}
.card.ex{padding:10px 14px;}
.ex h3{font-size:1rem;margin-bottom:4px;}
.ex table{font-size:.85rem;}
.ex td,.ex th{padding:4px 8px;}
.prbadge{display:inline-flex;vertical-align:-2px;margin-left:6px;color:#8a5a00;}
.prbadge svg{width:14px;height:14px;display:block;}
a{color:#7a5a34;text-decoration:none;}
a:visited{color:#7a5a34;}
a:hover{text-decoration:underline;}
.ex td:nth-child(1),.ex td:nth-child(2),.ex td:nth-child(3){white-space:nowrap;}
@media (prefers-color-scheme:dark){
.cal .dw{color:#b0aca2;}
.cal .cd{background:#171514;color:#7f7a6e;}
.cal .cd.t{background:#2f7d33;color:#fff;}
.cal .cd.fut{background:none;}
.cal .cd.pr::after{background:#e6c400;}
.prbadge{background:none;color:#e6c400;}
.iconbtn{color:#f0ede6;}
a{color:#f2a35e;}
a:visited{color:#f2a35e;}
}
table{width:100%;border-collapse:collapse;font-family:"IBM Plex Sans",sans-serif;font-size:.95rem;}
td,th{padding:7px 10px;border-bottom:1px solid #e5dfcd;text-align:left;}
thead th{font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;color:#4e5148;}
.empty{font-family:"IBM Plex Sans",sans-serif;color:#6e695c;padding:18px 4px;}
@media (prefers-color-scheme:dark){
body{background:#080807;color:#f0ede6;}
.stat,.card{background:#111010;border-color:#232120;}
.sub,.stat span,.cap,.notes,.legend,thead th{color:#b0aca2;}
h2{color:#f0ede6;}
td,th{border-color:#232120;}
.dot{background:#232120;}
.dot.t{background:#2f7d33;}
}
</style></head><body><div class="wrap" id="viewDash">
<div class="kick">reps</div>
<h1>Training dashboard</h1>
<div class="sub" id="sub">loading</div>
<h2>Estimated 1RM trend</h2>
<div class="card"><canvas id="chTrend" width="860" height="230"></canvas><div class="legend" id="legTrend"></div><div class="cap">Best set per session. Dots under the axis mark sessions with notes.</div><ul class="notes" id="noteList"></ul></div>
<h2>Bodyweight</h2>
<div class="card"><canvas id="chBw" width="860" height="230"></canvas><div class="cap">Morning weigh ins, as logged in chat.</div></div>
<h2>Weekly volume by muscle</h2>
<div class="card"><canvas id="chMus" width="860" height="230"></canvas><div class="legend" id="legMus"></div></div>
<h2>Training calendar</h2>
<div class="card calcard"><div class="calhead"><button id="calPrev" type="button" aria-label="Previous month"><svg viewBox="0 0 16 16" width="18" height="18"><path d="M10 3 L5 8 L10 13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button><b id="calTitle"></b><button id="calNext" type="button" aria-label="Next month"><svg viewBox="0 0 16 16" width="18" height="18"><path d="M6 3 L11 8 L6 13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button></div><div class="cal" id="cal"></div><div class="cap">Tap a highlighted day for the session. Gold dot marks a PR day.</div></div>
<h2>Best sets</h2>
<div class="card"><table id="prs"><thead><tr><th>lift</th><th>best set by e1RM</th><th>date</th></tr></thead></table></div>
</div>
<div class="wrap" id="viewSession" hidden>
<div class="sesstop"><a class="iconbtn" href="#/" aria-label="back to dashboard"><svg viewBox="0 0 16 16" width="22" height="22"><path d="M14 8H3M7 4L3 8l4 4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></a><span class="sesspg"><a class="iconbtn" id="sessPrev" href="#/" aria-label="previous session"><svg viewBox="0 0 16 16" width="22" height="22"><path d="M10 3 L5 8 L10 13" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></a><a class="iconbtn" id="sessNext" href="#/" aria-label="next session"><svg viewBox="0 0 16 16" width="22" height="22"><path d="M6 3 L11 8 L6 13" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></a></span></div>
<h1 id="sessTitle">Session</h1>
<div id="sessNotes"></div>
<div id="sessBody" class="exgrid"></div>
</div>
<script>
const DARK = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
const LC = DARK ? ["#f2a35e", "#7cc47f", "#e6c400", "#f09696"] : ["#7a5a34", "#2f7d33", "#8a5a00", "#b3261e"];
const TC = DARK ? "#cfc9bc" : "#4e5148";
const GC = DARK ? "#3a3733" : "#d9d3c0";
const MC = DARK
  ? { push: "#f2a35e", pull: "#7cc47f", legs: "#6cb6ff", other: "#8a8578" }
  : { push: "#7a5a34", pull: "#2f7d33", legs: "#375f8f", other: "#bbb" };
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
let HIDDEN = new Set();
try {
  HIDDEN = new Set(JSON.parse(localStorage.getItem("reps-hidden") || "[]"));
} catch (e) {}
async function main(){
  SNAP = await (await fetch("snapshot")).json();
  render();
  let rt = null;
  window.addEventListener("resize", () => {
    if (rt) clearTimeout(rt);
    rt = setTimeout(render, 250);
  });
}
function render(){
  const snap = SNAP;
  const W = snap.workouts || [];
  const S = snap.sets || [];
  const BW = snap.bodyweight || [];
  document.getElementById("sub").textContent = W.length
    ? W.length + " sessions, latest " + W.map(w => w.date).sort().pop()
    : "no sync yet, log your first session";
  const wdates = W.map(w => w.date).sort();
  const lastW = wdates.length ? wdates[wdates.length - 1] : null;
  const byDate = {};
  for (const s of S) { const d = s.created.slice(0, 10); (byDate[d] = byDate[d] || []).push(s); }
  const e1 = s => s.weight * (1 + s.reps / 30);
  const counts = {};
  for (const s of S) counts[s.exercise] = (counts[s.exercise] || 0) + 1;
  const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 4).map(e => e[0]);
  const days = Object.keys(byDate).sort();
  const series = top.map(t => days.map(d => {
    const sets = byDate[d].filter(s => s.exercise === t);
    if (!sets.length) return null;
    return Math.max.apply(null, sets.map(e1));
  }));
  TREND = { days, series, top };
  drawTrend();
  const noted = {};
  for (const w of W) if (w.notes) noted[w.date] = w.notes;
  for (const s of S) {
    if (s.note && s.note.toLowerCase().indexOf("grindy") > -1) {
      const d = s.created.slice(0, 10);
      noted[d] = (noted[d] ? noted[d] + " / " : "") + s.exercise + ": " + s.note;
    }
  }
  const nl = document.getElementById("noteList");
  nl.innerHTML = "";
  Object.keys(noted).sort().slice(-6).forEach(d => {
    const li = document.createElement("li"); li.textContent = d + ": " + noted[d]; nl.appendChild(li);
  });
  bwline(document.getElementById("chBw"), BW);
  const groups = ["push", "pull", "legs", "other"];
  const weeks = {};
  for (const s of S) {
    const k = weekKey(s.created.slice(0, 10));
    weeks[k] = weeks[k] || { push: 0, pull: 0, legs: 0, other: 0 };
    weeks[k][muscleOf(s.exercise)] += 1;
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
  for (const w of W) dayDetail[w.date] = [];
  for (const s of S) {
    const d = s.created.slice(0, 10);
    (dayDetail[d] = dayDetail[d] || []).push(s.exercise + " " + s.weight + "x" + s.reps);
  }
  const startView = lastW || new Date().toISOString().slice(0, 10);
  D = { W, S, BW };
  PR = computePRs(W, S);
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
    const a = document.createElement("td"); a.textContent = k;
    const b2 = document.createElement("td"); b2.textContent = p.s.weight + " x " + p.s.reps + " (e1RM " + p.ev.toFixed(1) + ")";
    const c2 = document.createElement("td"); c2.textContent = wdate[p.s.workout_id] || "";
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
  if (ds && isDate(ds) && D) showSession(ds);
  else {
    document.getElementById("viewDash").hidden = false;
    document.getElementById("viewSession").hidden = true;
    document.title = "reps dashboard";
  }
}
function showSession(ds) {
  document.getElementById("viewDash").hidden = true;
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
    prev.setAttribute("aria-label", "previous session " + dates[ix - 1]);
  } else prev.style.visibility = "hidden";
  if (ix >= 0 && ix < dates.length - 1) {
    next.style.visibility = "";
    next.href = "#/s/" + dates[ix + 1];
    next.setAttribute("aria-label", "next session " + dates[ix + 1]);
  } else next.style.visibility = "hidden";
  if (!ws.length) {
    title.textContent = ds;
    document.title = ds + " no session";
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
      h.textContent = ex;
      wrap.appendChild(h);
      const tbl = document.createElement("table");
      tbl.className = "sess";
      const head = document.createElement("tr");
      ["set", "weight", "e1RM", "note"].forEach(t => {
        const th = document.createElement("th");
        th.textContent = t;
        head.appendChild(th);
      });
      tbl.appendChild(head);
      byEx[ex].forEach((s, i) => {
        const tr = document.createElement("tr");
        const ev = s.weight * (1 + s.reps / 30);
        const cells = [String(i + 1), s.weight + " x " + s.reps, ev.toFixed(1), s.note || ""];
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
        tbl.appendChild(tr);
      });
      wrap.appendChild(tbl);
      body.appendChild(wrap);
    });
  });
  document.title = ds + " training";
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", route);
function muscleOf(n) {
  n = n.toLowerCase();
  if (/(press|bench|dips|pushup|overhead|ohp|lateral|tricep|shoulder|chest)/.test(n)) return "push";
  if (/(row|pullup|pulldown|curl|chinup|bicep|lat|rear delt)/.test(n)) return "pull";
  if (/(squat|deadlift|leg|lunge|calf|rdl|hip)/.test(n)) return "legs";
  return "other";
}
function renderCal(year, month, dayDetail) {
  const names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  document.getElementById("calTitle").textContent = names[month] + " " + year;
  const box = document.getElementById("cal");
  box.innerHTML = "";
  ["M", "T", "W", "T", "F", "S", "S"].forEach(d => {
    const h = document.createElement("div"); h.className = "dw"; h.textContent = d; box.appendChild(h);
  });
  const first = new Date(year, month, 1);
  let lead = first.getDay() - 1;
  if (lead < 0) lead = 6;
  for (let i = 0; i < lead; i += 1) box.appendChild(document.createElement("div"));
  const days = new Date(year, month + 1, 0).getDate();
  const todayS = new Date().toISOString().slice(0, 10);
  for (let d = 1; d <= days; d += 1) {
    const key = year + "-" + String(month + 1).padStart(2, "0") + "-" + String(d).padStart(2, "0");
    const trained = dayDetail[key] && dayDetail[key].length > 0;
    const isPR = PR && PR.prDates.has(key);
    const el = document.createElement(trained ? "a" : "div");
    if (trained) el.href = "#/s/" + key;
    el.className = "cd" + (trained ? " t" : "") + (isPR ? " pr" : "") + (key === todayS ? " today" : "") + (key > todayS ? " fut" : "");
    el.textContent = String(d);
    el.title = trained ? key + ": " + dayDetail[key].join(", ") : key;
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
function drawTrend() {
  const vis = TREND.top.map((t, i) => i).filter(i => !HIDDEN.has(TREND.top[i]));
  line(document.getElementById("chTrend"), TREND.days, vis.map(i => ({ v: TREND.series[i], c: i })));
  const lt = document.getElementById("legTrend");
  lt.innerHTML = "";
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
      if (HIDDEN.has(t)) HIDDEN.delete(t); else HIDDEN.add(t);
      try {
        localStorage.setItem("reps-hidden", JSON.stringify(Array.from(HIDDEN)));
      } catch (e) {}
      drawTrend();
    });
    lt.appendChild(b);
  });
}
function line(cv, labels, items) {
  const f = fit(cv);
  const g = f.g, W = f.W, H = f.H, P = 46;
  let mn = Infinity, mx = 0, any = false;
  for (const it of items) for (const v of it.v) if (v !== null) { any = true; if (v < mn) mn = v; if (v > mx) mx = v; }
  if (!any) {
    g.fillStyle = TC; g.font = "600 14px sans-serif";
    g.fillText("no sets yet", P + 10, H / 2);
    return;
  }
  const pad = (mx - mn) * 0.2 || 1;
  mn = Math.max(0, mn - pad); mx += pad;
  g.clearRect(0, 0, W, H);
  g.font = "600 12px sans-serif";
  for (let i = 0; i <= 4; i += 1) {
    const v = mn + (mx - mn) * i / 4;
    const y = H - P - (H - P - 16) * i / 4;
    g.strokeStyle = GC; g.lineWidth = 1;
    g.beginPath(); g.moveTo(P, y); g.lineTo(W - 8, y); g.stroke();
    g.fillStyle = TC;
    putText(g, W, fmtV(v), 4, y + 4, "left");
  }
  const n = items.length ? items[0].v.length : 0;
  const px = i => P + (W - P - 8) * (n <= 1 ? 1 : i / (n - 1));
  const py = v => H - P - (H - P - 16) * ((v - mn) / (mx - mn));
  items.forEach(it => {
    const s = it.v;
    const col = LC[it.c % LC.length];
    const pts = [];
    for (let i = 0; i < s.length; i += 1) if (s[i] !== null) pts.push(i);
    if (!pts.length) return;
    g.strokeStyle = col; g.lineWidth = 3; g.lineJoin = "round"; g.beginPath();
    pts.forEach((pi, k) => { if (k === 0) g.moveTo(px(pi), py(s[pi])); else g.lineTo(px(pi), py(s[pi])); });
    g.stroke();
    g.fillStyle = col;
    pts.forEach(pi => { g.beginPath(); g.arc(px(pi), py(s[pi]), 4, 0, 7); g.fill(); });
    const first = pts[0], last = pts[pts.length - 1];
    putText(g, W, fmtV(s[first]), px(first) + 8, py(s[first]) - 10, first > n / 2 ? "right" : "left");
    if (last !== first) putText(g, W, fmtV(s[last]), px(last) - 8, py(s[last]) - 10, "right");
  });
  g.fillStyle = TC;
  if (labels.length) {
    putText(g, W, labels[0], P, H - 8, "left");
    putText(g, W, labels[labels.length - 1], W - 8, H - 8, "right");
  }
}
function bwline(cv, rows) {
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
  g.clearRect(0, 0, W, H);
  g.font = "600 12px sans-serif";
  for (let i = 0; i <= 4; i += 1) {
    const v = mn + (mx - mn) * i / 4;
    const y = H - P - (H - P - 16) * i / 4;
    g.strokeStyle = GC; g.lineWidth = 1;
    g.beginPath(); g.moveTo(P, y); g.lineTo(W - 8, y); g.stroke();
    g.fillStyle = TC;
    putText(g, W, fmtV(v), 4, y + 4, "left");
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
    putText(g, W, r.kg.toFixed(1), px(i), py(r.kg) - 12, "center");
    g.fillStyle = LC[0];
  });
  g.fillStyle = TC;
  putText(g, W, rows[0].date, P, H - 8, "left");
  putText(g, W, rows[rows.length - 1].date, W - 8, H - 8, "right");
}
function stacked(cv, labels, weeks) {
  const f = fit(cv);
  const g = f.g, W = f.W, H = f.H, P = 46;
  g.clearRect(0, 0, W, H);
  const groups = ["push", "pull", "legs", "other"];
  let mx = 1;
  weeks.forEach(w => {
    const t = groups.reduce((a, k) => a + w[k], 0);
    if (t > mx) mx = t;
  });
  const bw = (W - P - 8) / Math.max(1, weeks.length);
  const area = H - P - 42;
  g.font = "600 12px sans-serif";
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
