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
.sw{width:22px;height:4px;border-radius:2px;display:inline-block;}
.cap{font-family:"IBM Plex Sans",sans-serif;font-size:.88rem;color:#4e5148;margin-top:10px;}
.notes{font-family:"IBM Plex Sans",sans-serif;font-size:.88rem;color:#4e5148;margin-top:10px;}
.notes li{margin-bottom:4px;margin-left:20px;}
.calhead{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;font-family:"IBM Plex Sans",sans-serif;}
.calhead button{background:none;border:1px solid #d9d3c0;border-radius:8px;padding:4px 12px;font-family:inherit;cursor:pointer;color:inherit;}
.cal{display:grid;grid-template-columns:repeat(7,1fr);gap:4px;font-family:"IBM Plex Sans",sans-serif;font-size:.85rem;}
.cal .dw{font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:#4e5148;text-align:center;padding:4px 0;}
.cal .cd{aspect-ratio:1.4;border-radius:8px;background:#f5f2e9;display:flex;align-items:center;justify-content:center;color:#6e695c;}
.cal .cd.t{background:#2f7d33;color:#fff;font-weight:600;}
.cal .cd.today{outline:2px solid #7a5a34;outline-offset:-2px;}
.cal .cd.fut{background:none;}
@media (prefers-color-scheme:dark){
.calhead button{border-color:#232120;}
.cal .dw{color:#b0aca2;}
.cal .cd{background:#171514;color:#7f7a6e;}
.cal .cd.t{background:#2f7d33;color:#fff;}
.cal .cd.fut{background:none;}
}
table{width:100%;border-collapse:collapse;font-family:"IBM Plex Sans",sans-serif;font-size:.95rem;}
td,th{padding:7px 10px;border-bottom:1px solid #e5dfcd;text-align:left;}
thead th{font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;color:#4e5148;}
.empty{font-family:"IBM Plex Sans",sans-serif;color:#6e695c;padding:18px 4px;}
@media (prefers-color-scheme:dark){
body{background:#080807;color:#f0ede6;}
.stat,.card{background:#111010;border-color:#232120;}
.sub,.stat span,.cap,.notes,thead th{color:#b0aca2;}
td,th{border-color:#232120;}
.dot{background:#232120;}
.dot.t{background:#2f7d33;}
}
</style></head><body><div class="wrap">
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
<div class="card"><div class="calhead"><button id="calPrev" type="button">prev</button><b id="calTitle"></b><button id="calNext" type="button">next</button></div><div class="cal" id="cal"></div><div class="cap">Highlighted days are trained. Hover for the session.</div></div>
<h2>Best sets</h2>
<div class="card"><table id="prs"><thead><tr><th>lift</th><th>best set</th><th>date</th></tr></thead></table></div>
</div>
<script>
async function main(){
  const snap = await (await fetch("snapshot")).json();
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
  line(document.getElementById("chTrend"), days, series);
  const lt = document.getElementById("legTrend");
  const cols = ["#7a5a34", "#2f7d33", "#8a5a00", "#b3261e"];
  top.forEach((t, i) => {
    const sp = document.createElement("span"); sp.className = "chip";
    const sw = document.createElement("span"); sw.className = "sw"; sw.style.background = cols[i % cols.length];
    sp.appendChild(sw); sp.appendChild(document.createTextNode(t)); lt.appendChild(sp);
  });
  const noted = {};
  for (const w of W) if (w.notes) noted[w.date] = w.notes;
  for (const s of S) {
    if (s.note && s.note.toLowerCase().indexOf("grindy") > -1) {
      const d = s.created.slice(0, 10);
      noted[d] = (noted[d] ? noted[d] + " / " : "") + s.exercise + ": " + s.note;
    }
  }
  const nl = document.getElementById("noteList");
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
  const mc = { push: "#7a5a34", pull: "#2f7d33", legs: "#375f8f", other: "#999" };
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
  for (const s of S) { const k = s.exercise; if (!prs[k] || s.weight > prs[k].weight) prs[k] = s; }
  const tbl = document.getElementById("prs");
  Object.keys(prs).sort().forEach(k => {
    const p = prs[k];
    const tr = document.createElement("tr");
    const a = document.createElement("td"); a.textContent = k;
    const b2 = document.createElement("td"); b2.textContent = p.weight + " x " + p.reps;
    const c2 = document.createElement("td"); c2.textContent = wdate[p.workout_id] || "";
    tr.appendChild(a); tr.appendChild(b2); tr.appendChild(c2); tbl.appendChild(tr);
  });
}
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
    const el = document.createElement("div");
    const trained = dayDetail[key] && dayDetail[key].length > 0;
    el.className = "cd" + (trained ? " t" : "") + (key === todayS ? " today" : "") + (key > todayS ? " fut" : "");
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
function axes(g, W, H, P) {
  g.clearRect(0, 0, W, H);
  g.strokeStyle = "#d9d3c0";
  for (let i = 0; i < 4; i += 1) {
    const y = P + (H - 2 * P) * i / 3;
    g.beginPath(); g.moveTo(P, y); g.lineTo(W - 8, y); g.stroke();
  }
}
function line(cv, labels, series) {
  const g = cv.getContext("2d");
  const W = cv.width, H = cv.height, P = 28;
  axes(g, W, H, P);
  let mx = 0;
  for (const s of series) for (const v of s) if (v !== null && v > mx) mx = v;
  mx = mx || 1;
  const cols = ["#7a5a34", "#2f7d33", "#8a5a00", "#b3261e"];
  const px = i => P + (W - P - 8) * (series[0].length === 1 ? 1 : i / (series[0].length - 1));
  series.forEach((s, si) => {
    g.strokeStyle = cols[si % cols.length]; g.lineWidth = 2.5; g.beginPath();
    let started = false;
    for (let i = 0; i < s.length; i += 1) {
      if (s[i] === null) { started = false; continue; }
      const y = H - P - (H - 2 * P) * (s[i] / mx);
      if (!started) { g.moveTo(px(i), y); started = true; } else g.lineTo(px(i), y);
    }
    g.stroke();
  });
  g.fillStyle = "#6e695c"; g.font = "11px sans-serif";
  if (labels.length) {
    g.fillText(labels[0], P, H - 8);
    g.fillText(labels[labels.length - 1], W - 64, H - 8);
  }
}
function bwline(cv, rows) {
  const g = cv.getContext("2d");
  const W = cv.width, H = cv.height, P = 28;
  axes(g, W, H, P);
  if (!rows.length) {
    g.fillStyle = "#6e695c"; g.font = "14px sans-serif";
    g.fillText("no weigh ins yet, say your morning weight in chat", P + 10, H / 2);
    return;
  }
  const vals = rows.map(r => r.kg);
  let mn = Math.min.apply(null, vals), mx = Math.max.apply(null, vals);
  if (mx === mn) { mx += 1; mn -= 1; }
  const px = i => P + (W - P - 8) * (rows.length === 1 ? 1 : i / (rows.length - 1));
  const py = v => H - P - (H - 2 * P) * ((v - mn) / (mx - mn));
  g.strokeStyle = "#7a5a34"; g.lineWidth = 2.5; g.beginPath();
  rows.forEach((r, i) => { if (i === 0) g.moveTo(px(i), py(r.kg)); else g.lineTo(px(i), py(r.kg)); });
  g.stroke();
  g.fillStyle = "#7a5a34";
  rows.forEach((r, i) => { g.beginPath(); g.arc(px(i), py(r.kg), 3.5, 0, 7); g.fill(); });
  g.fillStyle = "#6e695c"; g.font = "11px sans-serif";
  g.fillText(rows[0].date, P, H - 8);
  g.fillText(rows[rows.length - 1].date + "  " + rows[rows.length - 1].kg + " kg", W - 150, H - 8);
}
function stacked(cv, labels, weeks) {
  const g = cv.getContext("2d");
  const W = cv.width, H = cv.height, P = 28;
  g.clearRect(0, 0, W, H);
  const groups = ["push", "pull", "legs", "other"];
  const mc = { push: "#7a5a34", pull: "#2f7d33", legs: "#375f8f", other: "#bbb" };
  let mx = 1;
  weeks.forEach(w => {
    const t = groups.reduce((a, k) => a + w[k], 0);
    if (t > mx) mx = t;
  });
  const bw = (W - P - 8) / Math.max(1, weeks.length);
  weeks.forEach((w, i) => {
    let y0 = H - P;
    groups.forEach(gr => {
      const h = (H - 2 * P) * (w[gr] / mx);
      g.fillStyle = mc[gr];
      g.fillRect(P + i * bw + 3, y0 - h, bw - 6, h);
      y0 -= h;
    });
    g.fillStyle = "#6e695c"; g.font = "10px sans-serif";
    g.fillText(labels[i], P + i * bw + 3, H - 8);
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
