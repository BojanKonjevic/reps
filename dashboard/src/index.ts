import { fmtV, fmtD, fmtTick, isDate, niceTicks, Ticks } from './utils';
import {
  fit,
  putText,
  LC,
  TC,
  GC,
  STARC,
  MC,
  GROUPS,
  trophy,
  drawYAxis,
  drawXAxisLabels,
  drawValueLabels,
  drawHoverLine,
  drawPoint,
  drawHoverPoint,
  drawLine,
  ChartContext,
} from './charts';
import { liftChart, getLiftPts, LiftPoint } from './liftChart';
import { mini } from './miniChart';
import { bwline } from './bwChart';
import { stacked } from './stackedChart';
import { computePRs } from './prs';
import { tipRow, showTip, hideTip } from './tip';

interface Env {
  SNAPSHOTS: R2Bucket;
  SYNC_SECRET: string;
}

const BLANK = {
  note: 'no sync yet, run sync from the CLI after a session',
  workouts: [],
  sets: [],
  bodyweight: [],
};

let SNAP: any = null;
let TREND = {
  days: [] as string[],
  series: [] as number[][],
  top: [] as string[],
};
let D: { W: any[]; S: any[]; BW: any[] } | null = null;
let PR: PRData | null = null;
let DASHY = 0;
let VIEW = 'dash';
let HIDDEN = new Set<string>();
let HADHIDDEN = false;
let LIFTDATA: { pts: LiftPoint[]; ex: string } | null = null;
let BWDATA: any[] = [];

function saveHidden() {
  try {
    localStorage.setItem('reps-hidden', JSON.stringify(Array.from(HIDDEN)));
  } catch (e) {}
}

async function main() {
  SNAP = await (await fetch('snapshot')).json();
  render();
  let rt: number | null = null;
  window.addEventListener('resize', () => {
    if (rt) clearTimeout(rt);
    rt = setTimeout(render, 250);
  });
  const ch = document.getElementById('chLift') as HTMLCanvasElement;
  const near = (ev: MouseEvent) => {
    const r = ch.getBoundingClientRect();
    const x = ev.clientX - r.left,
      y = ev.clientY - r.top;
    let bp: any = null,
      bd = 1e9;
    getLiftPts().forEach(p => {
      const d = Math.abs(p.x - x) + Math.abs(p.y - y);
      if (d < bd) {
        bd = d;
        bp = p;
      }
    });
    return bd < 34 ? bp : null;
  };
  ch.addEventListener('click', ev => {
    const p = near(ev);
    if (p) location.hash = '#/s/' + p.date;
  });
  ch.addEventListener('mousemove', ev => {
    ch.style.cursor = near(ev) ? 'pointer' : 'default';
  });
  const bwCv = document.getElementById('chBw') as HTMLCanvasElement;
  bwCv.addEventListener('mousemove', ev => {
    if (!BWDATA.length) return;
    const r = bwCv.getBoundingClientRect();
    const idx = sliceIdx(ev.clientX - r.left, r.width, BWDATA.length);
    bwline(bwCv, BWDATA, idx);
    showTip(BWDATA[idx].date, [[null, BWDATA[idx].kg.toFixed(1) + ' kg']], ev.clientX, ev.clientY);
  });
  bwCv.addEventListener('mouseleave', () => {
    hideTip();
    bwline(bwCv, BWDATA, -1);
  });
  const liftCv = document.getElementById('chLift') as HTMLCanvasElement;
  liftCv.addEventListener('mousemove', ev => {
    if (!LIFTDATA) return;
    const r = liftCv.getBoundingClientRect();
    const x = ev.clientX - r.left;
    let bi = -1,
      bd = 1e9;
    getLiftPts().forEach((p, i) => {
      const d = Math.abs(p.x - x);
      if (d < bd) {
        bd = d;
        bi = i;
      }
    });
    if (bi < 0 || bd > 40) {
      hideTip();
      liftChart(liftCv, LIFTDATA.pts, LIFTDATA.ex, -1);
      liftCv.style.cursor = 'default';
      return;
    }
    liftChart(liftCv, LIFTDATA.pts, LIFTDATA.ex, bi);
    const p = LIFTDATA.pts[bi];
    showTip(
      p.date,
      [[null, p.w + ' x ' + p.r + ' (e1RM ' + p.ev.toFixed(1) + ')' + (p.pr ? ' PR' : '')]],
      ev.clientX,
      ev.clientY
    );
    liftCv.style.cursor = 'pointer';
  });
  liftCv.addEventListener('mouseleave', () => {
    hideTip();
    if (LIFTDATA) liftChart(liftCv, LIFTDATA.pts, LIFTDATA.ex, -1);
    liftCv.style.cursor = 'default';
  });
}

function sliceIdx(x: number, cw: number, n: number): number {
  if (n <= 1) return 0;
  const i = Math.round((x - 46) / ((cw - 46 - 8) / (n - 1)));
  return Math.min(n - 1, Math.max(0, i));
}

function render() {
  const snap = SNAP;
  const W = snap.workouts || [];
  const S = snap.sets || [];
  const BW = snap.bodyweight || [];
  document.getElementById('sub')!.textContent = W.length
    ? W.length +
      ' sessions, latest ' +
      fmtD(
        W.map(w => w.date)
          .sort()
          .pop()!
      )
    : 'no sync yet, log your first session';
  const wdates = W.map(w => w.date).sort();
  const lastW = wdates.length ? wdates[wdates.length - 1] : null;
  const wdate0: Record<number, string> = {};
  for (const w of W) wdate0[w.id] = w.date;
  const wday = (s: any) => wdate0[s.workout_id] || s.created.slice(0, 10);
  const T = S.filter((s: any) => s.weight > 0);
  const byDate: Record<string, any[]> = {};
  for (const s of T) {
    const d = wday(s);
    (byDate[d] = byDate[d] || []).push(s);
  }
  const e1 = (s: any) => s.weight * (1 + s.reps / 30);
  const counts: Record<string, number> = {};
  for (const s of T) counts[s.exercise] = (counts[s.exercise] || 0) + 1;
  const top = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(e => e[0]);
  Array.from(HIDDEN).forEach(n => {
    if (top.indexOf(n) < 0) HIDDEN.delete(n);
  });
  if (!HADHIDDEN) top.slice(8).forEach(n => HIDDEN.add(n));
  saveHidden();
  const days = Object.keys(byDate).sort();
  const series = top.map(t =>
    days.map(d => {
      const sets = byDate[d].filter((s: any) => s.exercise === t);
      if (!sets.length) return null;
      return Math.max(...sets.map(e1));
    })
  );
  TREND = { days, series, top };
  PR = computePRs(W, S);
  D = { W, S, BW };
  const noted: Record<string, string> = {};
  for (const w of W) if (w.notes) noted[w.date] = w.notes;
  for (const s of S) {
    if (s.note && s.note.toLowerCase().includes('grindy')) {
      const d = wday(s);
      noted[d] = (noted[d] ? noted[d] + ' / ' : '') + s.exercise + ': ' + s.note;
    }
  }
  const nl = document.getElementById('noteList')!;
  nl.innerHTML = '';
  Object.keys(noted)
    .sort()
    .slice(-6)
    .forEach(d => {
      const li = document.createElement('li');
      li.textContent = fmtD(d) + ': ' + noted[d];
      nl.appendChild(li);
    });
  bwline(document.getElementById('chBw') as HTMLCanvasElement, BW);
  BWDATA = BW;
  const blank = () => ({
    chest: 0,
    back: 0,
    shoulders: 0,
    biceps: 0,
    triceps: 0,
    quads: 0,
    hamstrings: 0,
    glutes: 0,
    abs: 0,
  });
  const weeks: Record<string, Record<string, number>> = {};
  for (const s of S) {
    const k = weekKey(wday(s));
    weeks[k] = weeks[k] || blank();
    const stored = (s.muscles || '')
      .split(',')
      .map((x: string) => x.trim().toLowerCase())
      .filter((x: string) => x);
    stored.forEach((g: string) => {
      if (g in weeks[k]) weeks[k][g] += 1;
    });
  }
  stacked(
    document.getElementById('chMus') as HTMLCanvasElement,
    Object.keys(weeks).sort(),
    Object.keys(weeks)
      .sort()
      .map(k => weeks[k])
  );
  const lm = document.getElementById('legMus')!;
  lm.innerHTML = '';
  GROUPS.forEach(g => {
    const sp = document.createElement('span');
    sp.className = 'chip';
    const sw = document.createElement('span');
    sw.className = 'sw';
    sw.style.background = MC[g];
    sp.appendChild(sw);
    sp.appendChild(document.createTextNode(g));
    lm.appendChild(sp);
  });
  const dayDetail: Record<string, string[]> = {};
  for (const w of W) dayDetail[w.date] = dayDetail[w.date] || [];
  for (const s of S) {
    const d = wday(s);
    (dayDetail[d] = dayDetail[d] || []).push(s.exercise + ' ' + s.weight + 'x' + s.reps);
  }
  const startView = lastW || new Date().toISOString().slice(0, 10);
  let viewY = parseInt(startView.slice(0, 4), 10);
  let viewM = parseInt(startView.slice(5, 7), 10) - 1;
  const drawCal = () => renderCal(viewY, viewM, dayDetail);
  document.getElementById('calPrev')!.addEventListener('click', () => {
    viewM -= 1;
    if (viewM < 0) {
      viewM = 11;
      viewY -= 1;
    }
    drawCal();
  });
  document.getElementById('calNext')!.addEventListener('click', () => {
    viewM += 1;
    if (viewM > 11) {
      viewM = 0;
      viewY += 1;
    }
    drawCal();
  });
  drawCal();
  const wdate: Record<number, string> = {};
  for (const w of W) wdate[w.id] = w.date;
  const prs: Record<string, { s: any; ev: number }> = {};
  for (const s of S) {
    const k = s.exercise;
    const ev = s.weight * (1 + s.reps / 30);
    if (!prs[k] || ev > prs[k].ev) prs[k] = { s, ev };
  }
  const tbl = document.getElementById('prs')!;
  while (tbl.rows.length > 1) tbl.deleteRow(1);
  Object.keys(prs)
    .sort()
    .forEach(k => {
      const p = prs[k];
      const tr = document.createElement('tr');
      const a = document.createElement('td');
      const al = document.createElement('a');
      al.href = '#/l/' + encodeURIComponent(k);
      al.textContent = k;
      a.appendChild(al);
      const b2 = document.createElement('td');
      b2.textContent = p.s.weight + ' x ' + p.s.reps + ' (e1RM ' + p.ev.toFixed(1) + ')';
      const c2 = document.createElement('td');
      c2.textContent = fmtD(wdate[p.s.workout_id] || '');
      tr.appendChild(a);
      tr.appendChild(b2);
      tr.appendChild(c2);
      tbl.appendChild(tr);
    });
  route();
}

function renderCal(year: number, month: number, dayDetail: Record<string, string[]>) {
  const names = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ];
  document.getElementById('calTitle')!.textContent = names[month] + ' ' + year;
  const box = document.getElementById('cal')!;
  box.innerHTML = '';
  hideTip();
  ['M', 'T', 'W', 'T', 'F', 'S', 'S'].forEach(d => {
    const h = document.createElement('div');
    h.className = 'dw';
    h.textContent = d;
    box.appendChild(h);
  });
  const first = new Date(year, month, 1);
  let lead = first.getDay() - 1;
  if (lead < 0) lead = 6;
  for (let i = 0; i < lead; i += 1) box.appendChild(document.createElement('div'));
  const days = new Date(year, month + 1, 0).getDate();
  const todayS = new Date().toISOString().slice(0, 10);
  const wByDate: Record<string, any[]> = {};
  if (D && D.W)
    for (const w of D.W) {
      (wByDate[w.date] = wByDate[w.date] || []).push(w);
    }
  const sByDate: Record<string, any[]> = {};
  const wid2date: Record<number, string> = {};
  if (D && D.W) for (const w of D.W) wid2date[w.id] = w.date;
  if (D && D.S)
    for (const s of D.S) {
      const d = wid2date[s.workout_id] || (s.created || '').slice(0, 10);
      (sByDate[d] = sByDate[d] || []).push(s);
    }
  for (let d = 1; d <= days; d += 1) {
    const key = year + '-' + String(month + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0');
    const trained = dayDetail[key] && dayDetail[key].length > 0;
    const isPR = PR && PR.prDates.has(key);
    const el = document.createElement(trained ? 'a' : 'div');
    if (trained) el.href = '#/s/' + key;
    el.className =
      'cd' +
      (trained ? ' t' : '') +
      (key === todayS ? ' today' : '') +
      (key > todayS ? ' fut' : '');
    el.textContent = String(d);
    if (isPR) {
      const tr = document.createElement('span');
      tr.className = 'prt';
      tr.title = 'personal record';
      tr.innerHTML =
        '<svg viewBox="0 0 16 16"><path d="M5 1.5h6v4.2a3 3 0 0 1-6 0V1.5z" fill="currentColor"/><path d="M5 2.5H3.2a2.8 2.8 0 0 0 2.9 3.6M11 2.5h1.8a2.8 2.8 0 0 1-2.9 3.6" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M8 8.7v2.1M6.2 12.8h3.6M5.4 14.5h5.2" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>';
      el.appendChild(tr);
    }
    if (trained) {
      el.addEventListener('click', hideTip);
      el.addEventListener('mousemove', ev => {
        const sets = sByDate[key] || [];
        const order: string[] = [];
        const byEx: Record<string, any[]> = {};
        sets.forEach(s => {
          (byEx[s.exercise] = byEx[s.exercise] || []).push(s);
          if (order.indexOf(s.exercise) < 0) order.push(s.exercise);
        });
        const rows: Array<[string | null, string]> = [];
        order.slice(0, 6).forEach(ex => {
          const g = byEx[ex];
          const top = g.slice().sort((a, b) => b.weight - a.weight || b.reps - a.reps)[0];
          const hasPR = g.some(s => PR && PR.prIds.has(s.id));
          rows.push([
            hasPR ? '#e6c400' : null,
            ex + ' ' + g.length + ' x ' + top.weight + 'x' + top.reps + (hasPR ? ' PR' : ''),
          ]);
        });
        if (order.length > 6) rows.push([null, '+' + (order.length - 6) + ' more lifts']);
        const wnotes = (wByDate[key] || []).map(w => w.notes).filter(n => n);
        if (wnotes.length && rows.length < 7) {
          const n = wnotes.join(' / ');
          rows.push([null, n.length > 90 ? n.slice(0, 90) + '...' : n]);
        }
        const title =
          new Date(key + 'T12:00:00').toLocaleDateString(undefined, {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
          }) + (isPR ? '  PR' : '');
        showTip(title, rows.length ? rows : [[null, 'tap to open']], ev.clientX, ev.clientY);
      });
      el.addEventListener('mouseleave', hideTip);
    }
    box.appendChild(el);
  }
}

function route() {
  const h = location.hash || '';
  const ds = h.slice(0, 4) === '#/s/' ? h.slice(4, 14) : '';
  const lift = h.slice(0, 4) === '#/l/' ? decodeURIComponent(h.slice(4)) : '';
  if (ds && isDate(ds) && D) {
    if (VIEW === 'dash') DASHY = window.scrollY;
    VIEW = 'sess';
    showSession(ds);
  } else if (lift && D) {
    if (VIEW === 'dash') DASHY = window.scrollY;
    VIEW = 'lift';
    showLift(lift);
  } else {
    const restore = VIEW !== 'dash';
    VIEW = 'dash';
    document.getElementById('viewDash')!.hidden = false;
    document.getElementById('viewSession')!.hidden = true;
    document.getElementById('viewLift')!.hidden = true;
    document.title = 'reps dashboard';
    if (restore) window.scrollTo(0, DASHY);
  }
}

function showSession(ds: string) {
  document.getElementById('viewDash')!.hidden = true;
  document.getElementById('viewLift')!.hidden = true;
  const v = document.getElementById('viewSession')!;
  v.hidden = false;
  const title = document.getElementById('sessTitle')!;
  const notes = document.getElementById('sessNotes')!;
  const body = document.getElementById('sessBody')!;
  const prev = document.getElementById('sessPrev')!;
  const next = document.getElementById('sessNext')!;
  notes.innerHTML = '';
  body.innerHTML = '';
  const ws = D!.W.filter(w => w.date === ds);
  const dates = Array.from(new Set(D!.W.map(w => w.date))).sort();
  const ix = dates.indexOf(ds);
  if (ix > 0) {
    prev.style.visibility = '';
    prev.href = '#/s/' + dates[ix - 1];
    prev.setAttribute('aria-label', 'previous session ' + fmtD(dates[ix - 1]));
  } else prev.style.visibility = 'hidden';
  if (ix >= 0 && ix < dates.length - 1) {
    next.style.visibility = '';
    next.href = '#/s/' + dates[ix + 1];
    next.setAttribute('aria-label', 'next session ' + fmtD(dates[ix + 1]));
  } else next.style.visibility = 'hidden';
  if (!ws.length) {
    title.textContent = fmtD(ds);
    document.title = fmtD(ds) + ' no session';
    window.scrollTo(0, 0);
    return;
  }
  title.textContent = new Date(ds + 'T12:00:00').toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });
  const wnotes = ws.map(w => w.notes).filter(n => n);
  if (wnotes.length) {
    const d = document.createElement('div');
    d.className = 'card';
    d.textContent = wnotes.join(' / ');
    notes.appendChild(d);
  }
  ws.forEach(w => {
    const sets = D!.S.filter(s => s.workout_id === w.id);
    const order: string[] = [];
    const byEx: Record<string, any[]> = {};
    sets.forEach(s => {
      (byEx[s.exercise] = byEx[s.exercise] || []).push(s);
      if (order.indexOf(s.exercise) < 0) order.push(s.exercise);
    });
    order.forEach(ex => {
      const wrap = document.createElement('div');
      wrap.className = 'card ex';
      const h = document.createElement('h3');
      const hl = document.createElement('a');
      hl.href = '#/l/' + encodeURIComponent(ex);
      hl.textContent = ex;
      h.appendChild(hl);
      wrap.appendChild(h);
      const tbl = document.createElement('table');
      tbl.className = 'sess';
      const thead = document.createElement('thead');
      const head = document.createElement('tr');
      ['set', 'weight', 'e1RM'].forEach(t => {
        const th = document.createElement('th');
        th.setAttribute('scope', 'col');
        th.textContent = t;
        head.appendChild(th);
      });
      thead.appendChild(head);
      tbl.appendChild(thead);
      const tbody = document.createElement('tbody');
      tbl.appendChild(tbody);
      const sn: Array<[number, string]> = [];
      byEx[ex].forEach((s, i) => {
        const tr = document.createElement('tr');
        const ev = s.weight * (1 + s.reps / 30);
        const cells = [String(i + 1), s.weight + ' x ' + s.reps, ev.toFixed(1)];
        cells.forEach(c => {
          const td = document.createElement('td');
          td.textContent = c;
          tr.appendChild(td);
        });
        if (PR!.prIds.has(s.id)) {
          const b = document.createElement('span');
          b.className = 'prbadge';
          b.title = 'personal record';
          b.innerHTML =
            '<svg viewBox="0 0 16 16"><path d="M5 1.5h6v4.2a3 3 0 0 1-6 0V1.5z" fill="currentColor"/><path d="M5 2.5H3.2a2.8 2.8 0 0 0 2.9 3.6M11 2.5h1.8a2.8 2.8 0 0 1-2.9 3.6" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M8 8.7v2.1M6.2 12.8h3.6M5.4 14.5h5.2" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>';
          tr.children[1].appendChild(b);
        }
        if (s.note) sn.push([i + 1, s.note]);
        tbody.appendChild(tr);
      });
      wrap.appendChild(tbl);
      if (sn.length) {
        const nd = document.createElement('div');
        nd.className = 'setnotes';
        sn.forEach(pair => {
          const ln = document.createElement('div');
          const b = document.createElement('b');
          b.textContent = String(pair[0]);
          ln.appendChild(b);
          ln.appendChild(document.createTextNode(pair[1]));
          nd.appendChild(ln);
        });
        wrap.appendChild(nd);
      }
      body.appendChild(wrap);
    });
  });
  document.title = fmtD(ds) + ' training';
  window.scrollTo(0, 0);
}

function showLift(ex: string) {
  document.getElementById('viewDash')!.hidden = true;
  document.getElementById('viewSession')!.hidden = true;
  const v = document.getElementById('viewLift')!;
  v.hidden = false;
  const title = document.getElementById('liftTitle')!;
  const sub = document.getElementById('liftSub')!;
  const tbl = document.getElementById('liftPRs')!;
  while (tbl.rows.length > 1) tbl.deleteRow(1);
  title.textContent = ex;
  document.title = ex;
  const sets = D!.S.filter(s => s.exercise === ex);
  if (!sets.length) {
    sub.textContent = 'never logged';
    LIFTDATA = null;
    liftChart(document.getElementById('chLift') as HTMLCanvasElement, [], ex, -1);
    window.scrollTo(0, 0);
    return;
  }
  const wdate: Record<number, string> = {};
  for (const w of D!.W) wdate[w.id] = w.date;
  const byDate: Record<string, any[]> = {};
  sets.forEach(s => {
    const d = wdate[s.workout_id];
    (byDate[d] = byDate[d] || []).push(s);
  });
  const pts = Object.keys(byDate)
    .sort()
    .map(d => {
      const top = byDate[d].slice().sort((a, b) => b.weight - a.weight || b.reps - a.reps)[0];
      return {
        date: d,
        w: top.weight,
        r: top.reps,
        ev: top.weight * (1 + top.reps / 30),
        pr: byDate[d].some(s => PR!.prIds.has(s.id)),
      };
    });
  const best = pts.slice().sort((a, b) => b.ev - a.ev)[0];
  sub.textContent =
    'best ' + best.w + ' x ' + best.r + ' (e1RM ' + best.ev.toFixed(1) + ') on ' + fmtD(best.date);
  LIFTDATA = { pts, ex };
  liftChart(document.getElementById('chLift') as HTMLCanvasElement, pts, ex);
  const order = D!.S.slice().sort((a, b) =>
    a.created < b.created ? -1 : a.created > b.created ? 1 : a.id - b.id
  );
  const seen = new Set<string>();
  let top2 = { ev: 0 };
  order.forEach(s => {
    if (s.exercise !== ex) return;
    const ev = s.weight * (1 + s.reps / 30);
    if (!seen.has(ex)) {
      seen.add(ex);
      top2.ev = ev;
      return;
    }
    if (ev > top2.ev) {
      top2.ev = ev;
      const tr = document.createElement('tr');
      const a = document.createElement('td');
      const al = document.createElement('a');
      al.href = '#/s/' + wdate[s.workout_id];
      al.textContent = fmtD(wdate[s.workout_id]);
      a.appendChild(al);
      const b2 = document.createElement('td');
      b2.textContent = s.weight + ' x ' + s.reps;
      const c2 = document.createElement('td');
      c2.textContent = ev.toFixed(1);
      tr.appendChild(a);
      tr.appendChild(b2);
      tr.appendChild(c2);
      tbl.appendChild(tr);
    }
  });
  window.scrollTo(0, 0);
}

window.addEventListener('hashchange', route);
main();

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    if (req.method === 'PUT' && url.pathname === '/sync') {
      const auth = req.headers.get('authorization') || '';
      if (!env.SYNC_SECRET || auth !== 'Bearer ' + env.SYNC_SECRET) {
        return Response.json({ error: 'unauthorized' }, { status: 401 });
      }
      const raw = await req.text();
      if (raw.length > 2000000) {
        return Response.json({ error: 'snapshot too large' }, { status: 413 });
      }
      try {
        JSON.parse(raw);
      } catch {
        return Response.json({ error: 'not json' }, { status: 400 });
      }
      await env.SNAPSHOTS.put('snapshot.json', raw, {
        httpMetadata: { contentType: 'application/json' },
      });
      return Response.json({ ok: true, bytes: raw.length });
    }
    if (url.pathname === '/snapshot') {
      const obj = await env.SNAPSHOTS.get('snapshot.json');
      if (!obj) return Response.json(BLANK);
      return new Response(obj.body, {
        headers: { 'content-type': 'application/json' },
      });
    }
    // Root path handled by static assets (index.html)
    return new Response('not found', { status: 404 });
  },
};
