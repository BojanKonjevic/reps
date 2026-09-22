import { fmtV, fmtD, isDate, e1rm } from './utils';
import { MC, GROUPS, liftColor } from './charts';
import { liftChart, getLiftPts, LiftPoint } from './liftChart';
import { mini } from './miniChart';
import { bwline } from './bwChart';
import { stacked, stackedHit } from './stackedChart';
import { computePRs, PRData } from './prs';
import { weekKey } from './date';
import { showTip, hideTip, bindHover } from './tip';
import { goalChart, goalHit } from './goalChart';
import { muscleChart, muscleHit } from './muscleChart';
import { pieChart, pieHit, piePalette, PieSlice } from './pieChart';
import {
  splitDayExercises,
  labelSession,
  nextSlot,
  isStalling,
  deloadWatch,
  parseNextTarget,
  musclePageData,
  missedExpected,
  adherenceWeeks,
  goalPercent,
  AdherenceDay,
} from './forward';

interface SnapWorkout {
  id: number;
  date: string;
  status: string;
  notes: string;
}

interface SnapSet {
  id: number;
  workout_id: number;
  exercise: string;
  weight: number;
  reps: number;
  note: string;
  created: string;
  muscles: string;
}

interface SnapBodyweight {
  date: string;
  kg: number;
  note: string;
}

let SNAP: any = null;
let TREND = {
  days: [] as string[],
  series: [] as Array<Array<number | null>>,
  top: [] as string[],
  meta: [] as Array<Array<{ w: number; r: number } | null>>,
};
let SLOT_OF_DATE: Record<string, string> = {};
let DAY_MOVES: Record<string, string[]> = {};
let D: { W: any[]; S: any[]; BW: any[] } | null = null;
let PR: PRData | null = null;
let DASHY = 0;
let VIEW = 'dash';
const HIDDEN = new Set<string>();
let HADHIDDEN = false;
try {
  const raw = localStorage.getItem('reps-hidden');
  if (raw !== null) {
    HADHIDDEN = true;
    HIDDEN.clear();
    for (const n of JSON.parse(raw)) HIDDEN.add(n);
  }
} catch {
  // storage unavailable, start fresh
}
let LIFTDATA: { pts: LiftPoint[]; ex: string; fut: number | null } | null = null;
const FILTER: { q: string; facets: Set<string> } = { q: '', facets: new Set() };
let MUSDATA: { labels: string[]; weeks: Array<Record<string, number>> } | null = null;
let MUSPAGE: { mus: string } | null = null;
let MUSPIE: { slices: PieSlice[]; sets: number[] } | null = null;
let LIFTGOAL: {
  ex: string;
  actuals: Array<{ date: string; ev: number }>;
  checkpoints: number[];
  tops: Record<string, { w: number; r: number }>;
} | null = null;
let BWDATA: { date: string; kg: number }[] = [];

function saveHidden() {
  try {
    localStorage.setItem('reps-hidden', JSON.stringify(Array.from(HIDDEN)));
  } catch (e) {}
}

async function main() {
  SNAP = await (await fetch('/snapshot')).json();
  try {
    // Explicitly load every family/weight before first paint AND first
    // canvas draw: fonts.ready alone resolves while nothing is pending,
    // which still races fallback rendering on slow networks.
    await Promise.all([
      document.fonts.load('500 16px "IBM Plex Serif"'),
      document.fonts.load('600 16px "IBM Plex Serif"'),
      document.fonts.load('700 16px "IBM Plex Serif"'),
      document.fonts.load('400 16px "IBM Plex Sans"'),
      document.fonts.load('500 16px "IBM Plex Sans"'),
      document.fonts.load('600 16px "IBM Plex Sans"'),
      document.fonts.load('400 16px "JetBrains Mono"'),
      document.fonts.load('500 16px "JetBrains Mono"'),
    ]);
  } catch {
    // fonts API unavailable, render anyway
  }
  render();
  let rt: ReturnType<typeof setTimeout> | null = null;
  window.addEventListener('resize', () => {
    if (rt) clearTimeout(rt);
    rt = setTimeout(() => {
      if (VIEW === 'lift' && LIFTDATA) {
        liftChart(
          document.getElementById('chLift') as HTMLCanvasElement,
          LIFTDATA.pts,
          LIFTDATA.ex,
          -1,
          LIFTDATA.fut
        );
        if (LIFTGOAL)
          goalChart(
            document.getElementById('chGoal') as HTMLCanvasElement,
            LIFTGOAL.actuals,
            LIFTGOAL.checkpoints,
            liftColor(LIFTGOAL.ex)
          );
      } else if (VIEW === 'mus' && MUSPAGE) {
        paintMuscle(MUSPAGE.mus);
      } else if (VIEW === 'dash') {
        render();
      }
    }, 250);
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
  const musCv = document.getElementById('chMus') as HTMLCanvasElement;
  const musShow = (cx: number, cy: number) => {
    if (!MUSDATA || !vis(musCv)) {
      hideTip();
      return;
    }
    const r = musCv.getBoundingClientRect();
    const hit = stackedHit(musCv, MUSDATA.labels, MUSDATA.weeks, cx - r.left, cy - r.top);
    if (!hit) {
      hideTip();
      stacked(musCv, MUSDATA.labels, MUSDATA.weeks);
      return;
    }
    stacked(musCv, MUSDATA.labels, MUSDATA.weeks, hit);
    const mev = mevOf(SNAP, MUSDATA.labels[hit.wi]);
    showTip(
      MUSDATA.labels[hit.wi],
      [
        [
          MC[hit.g],
          hit.g +
            ' ' +
            MUSDATA.weeks[hit.wi][hit.g] +
            ' sets' +
            (mev > 0 ? ' (MEV ' + mev + ')' : ''),
        ],
      ],
      cx,
      cy
    );
  };
  bindHover(musCv, musShow);
  musCv.addEventListener('click', ev => {
    if (!MUSDATA) return;
    const r = musCv.getBoundingClientRect();
    const hit = stackedHit(
      musCv,
      MUSDATA.labels,
      MUSDATA.weeks,
      ev.clientX - r.left,
      ev.clientY - r.top
    );
    if (hit) location.hash = '#/m/' + encodeURIComponent(hit.g);
  });
  musCv.addEventListener('mouseleave', () => {
    hideTip();
    if (MUSDATA && vis(musCv)) stacked(musCv, MUSDATA.labels, MUSDATA.weeks);
  });
  const bwCv = document.getElementById('chBw') as HTMLCanvasElement;
  const bwShow = (cx: number, cy: number) => {
    if (!BWDATA.length || !vis(bwCv)) {
      hideTip();
      return;
    }
    const r = bwCv.getBoundingClientRect();
    const idx = sliceIdx(cx - r.left, r.width, BWDATA.length);
    bwline(bwCv, BWDATA, idx);
    showTip(BWDATA[idx].date, [[null, BWDATA[idx].kg.toFixed(1) + ' kg']], cx, cy);
  };
  bindHover(bwCv, bwShow);
  bwCv.addEventListener('mouseleave', () => {
    hideTip();
    if (vis(bwCv)) bwline(bwCv, BWDATA, -1);
  });
  const liftCv = document.getElementById('chLift') as HTMLCanvasElement;
  const liftShow = (cx: number, cy: number) => {
    if (!LIFTDATA || !vis(liftCv)) {
      hideTip();
      return;
    }
    const r = liftCv.getBoundingClientRect();
    const x = cx - r.left;
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
      liftChart(liftCv, LIFTDATA.pts, LIFTDATA.ex, -1, LIFTDATA.fut);
      liftCv.style.cursor = 'default';
      return;
    }
    liftChart(liftCv, LIFTDATA.pts, LIFTDATA.ex, bi, LIFTDATA.fut);
    const p = LIFTDATA.pts[bi];
    showTip(
      p.date,
      [[null, p.w + ' x ' + p.r + ' (e1RM ' + p.ev.toFixed(1) + ')' + (p.pr ? ' PR' : '')]],
      cx,
      cy
    );
    liftCv.style.cursor = 'pointer';
  };
  bindHover(liftCv, liftShow);
  liftCv.addEventListener('mouseleave', () => {
    hideTip();
    if (LIFTDATA && vis(liftCv)) liftChart(liftCv, LIFTDATA.pts, LIFTDATA.ex, -1, LIFTDATA.fut);
    liftCv.style.cursor = 'default';
  });
  const goalCv = document.getElementById('chGoal') as HTMLCanvasElement;
  const goalCol = () => liftColor((LIFTGOAL && LIFTGOAL.ex) || '');
  const goalShow = (cx: number, cy: number) => {
    if (!LIFTGOAL || !vis(goalCv)) {
      hideTip();
      return;
    }
    const r = goalCv.getBoundingClientRect();
    const bi = goalHit(goalCv, LIFTGOAL.actuals, LIFTGOAL.checkpoints, cx - r.left);
    if (bi < 0) {
      hideTip();
      goalChart(goalCv, LIFTGOAL.actuals, LIFTGOAL.checkpoints, goalCol());
      return;
    }
    goalChart(goalCv, LIFTGOAL.actuals, LIFTGOAL.checkpoints, goalCol(), bi);
    if (bi < LIFTGOAL.actuals.length) {
      const a = LIFTGOAL.actuals[bi];
      const top = LIFTGOAL.tops[a.date];
      const logged = top
        ? 'logged ' + top.w + ' x ' + top.r + ' (e1RM ' + fmtV(a.ev) + ')'
        : 'e1RM ' + fmtV(a.ev);
      showTip(
        fmtD(a.date),
        [
          [goalCol(), logged],
          [null, 'plan ' + fmtV(LIFTGOAL.checkpoints[bi])],
        ],
        cx,
        cy
      );
    } else {
      showTip(
        'session ' + (bi + 1) + ' (plan)',
        [[goalCol(), 'target e1RM ' + fmtV(LIFTGOAL.checkpoints[bi])]],
        cx,
        cy
      );
    }
  };
  bindHover(goalCv, goalShow);
  goalCv.addEventListener('mouseleave', () => {
    hideTip();
    if (LIFTGOAL && vis(goalCv))
      goalChart(goalCv, LIFTGOAL.actuals, LIFTGOAL.checkpoints, goalCol());
  });
  const musVolCv = document.getElementById('chMusVol') as HTMLCanvasElement;
  const musVolData = () => {
    if (!MUSPAGE || !D) return null;
    const data = musclePageData(D.W, D.S, MUSPAGE.mus);
    const constants = (SNAP.constants || {}) as any;
    const entry = (constants.muscles || {})[MUSPAGE.mus] || {};
    return {
      data,
      bands: {
        mev: entry.mev !== undefined ? entry.mev : 0,
        mav: entry.mav || null,
        mrv: entry.mrv !== undefined ? entry.mrv : null,
      },
      color: entry.color || '#888',
    };
  };
  const musVolShow = (cx: number, cy: number) => {
    const m = musVolData();
    if (!m || !vis(musVolCv)) {
      hideTip();
      return;
    }
    const r = musVolCv.getBoundingClientRect();
    const bi = muscleHit(musVolCv, m.data.counts.length, cx - r.left);
    if (bi < 0) {
      hideTip();
      muscleChart(musVolCv, m.data.labels, m.data.counts, m.bands, m.color);
      return;
    }
    muscleChart(musVolCv, m.data.labels, m.data.counts, m.bands, m.color, bi);
    showTip(
      m.data.labels[bi],
      [[m.color, m.data.counts[bi] + ' sets (MEV ' + m.bands.mev + ')']],
      cx,
      cy
    );
  };
  bindHover(musVolCv, musVolShow);
  musVolCv.addEventListener('mouseleave', () => {
    hideTip();
    const m = musVolData();
    if (m && vis(musVolCv)) muscleChart(musVolCv, m.data.labels, m.data.counts, m.bands, m.color);
  });
  const musPieCv = document.getElementById('chMusPie') as HTMLCanvasElement;
  const musPieShow = (cx: number, cy: number) => {
    if (!MUSPIE || !vis(musPieCv)) {
      hideTip();
      return;
    }
    const r = musPieCv.getBoundingClientRect();
    const bi = pieHit(musPieCv, MUSPIE.slices, cx - r.left, cy - r.top);
    if (bi < 0) {
      hideTip();
      pieChart(musPieCv, MUSPIE.slices);
      return;
    }
    pieChart(musPieCv, MUSPIE.slices, bi);
    showTip(
      MUSPIE.slices[bi].label,
      [
        [
          piePalette(MUSPIE.slices[bi].label),
          MUSPIE.sets[bi] + ' sets · ' + Math.round(MUSPIE.slices[bi].frac * 100) + '%',
        ],
      ],
      cx,
      cy
    );
  };
  bindHover(musPieCv, musPieShow);
  musPieCv.addEventListener('click', ev => {
    if (!MUSPIE) return;
    const r = musPieCv.getBoundingClientRect();
    const bi = pieHit(musPieCv, MUSPIE.slices, ev.clientX - r.left, ev.clientY - r.top);
    const link = bi >= 0 ? MUSPIE.slices[bi].link : null;
    if (link) location.hash = link;
  });
  musPieCv.addEventListener('mouseleave', () => {
    hideTip();
    if (MUSPIE && vis(musPieCv)) pieChart(musPieCv, MUSPIE.slices);
  });
}

function sliceIdx(x: number, cw: number, n: number): number {
  if (n <= 1) return 0;
  const i = Math.round((x - 46) / ((cw - 46 - 8) / (n - 1)));
  return Math.min(n - 1, Math.max(0, i));
}

function vis(cv: HTMLCanvasElement): boolean {
  return cv.clientWidth > 0 && cv.clientHeight > 0;
}

function breakGap(snap: any): number {
  // Same rule as plan's today.break: gap of break_days + 1 or more.
  const t = snap && snap.constants && snap.constants.thresholds;
  return ((t && t.break_days) || 4) + 1;
}

function render() {
  const snap = SNAP;
  const W: SnapWorkout[] = snap.workouts || [];
  const S: SnapSet[] = snap.sets || [];
  const BW: SnapBodyweight[] = snap.bodyweight || [];
  const sessions = W.filter(w => w.status !== 'rest');
  const sdates = sessions.map(w => w.date).sort();
  document.getElementById('sub')!.textContent = sdates.length
    ? sessions.length + (sessions.length === 1 ? ' session' : ' sessions')
    : W.length
      ? 'no sessions yet, ' + W.length + ' rest days logged'
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
  const e1 = (s: any) => e1rm(s.weight, s.reps);
  const counts: Record<string, number> = {};
  for (const s of T) counts[s.exercise] = (counts[s.exercise] || 0) + 1;
  const goalEx = new Set((snap.goals || []).map((g: any) => (g.exercise || '').toLowerCase()));
  const prio = prioMuscles(snap);
  const rank = (ex: string) => {
    if (goalEx.has(ex.toLowerCase())) return 0;
    if (musclesOf(snap, ex).some(m => prio.has(m.toLowerCase()))) return 1;
    return 2;
  };
  const top = Object.entries(counts)
    .sort((a, b) => rank(a[0]) - rank(b[0]) || b[1] - a[1])
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
  const meta = top.map(t =>
    days.map(d => {
      const sets = byDate[d].filter((s: any) => s.exercise === t);
      if (!sets.length) return null;
      const best = sets.slice().sort((a: any, b: any) => e1(b) - e1(a))[0];
      return { w: best.weight, r: best.reps };
    })
  );
  TREND = { days, series, top, meta };
  PR = computePRs(W, S);
  DAY_MOVES = splitDayExercises(snap.split_active || []);
  const sessEx: Record<string, string[]> = {};
  for (const s of S) {
    const d = wday(s);
    (sessEx[d] = sessEx[d] || []).push(s.exercise);
  }
  SLOT_OF_DATE = {};
  for (const d of Object.keys(sessEx)) {
    const lab = labelSession(sessEx[d], DAY_MOVES);
    if (lab) SLOT_OF_DATE[d] = lab;
  }
  refreshTrend();
  renderNow(snap, W, S);
  renderNext(snap, W, S);
  renderSignals(snap);
  renderProgramSummary(snap);
  renderForward(snap, W, S);
  renderAdh(snap);
  D = { W, S, BW };
  const noted: Record<string, string> = {};
  for (const w of W) if (w.notes) noted[w.date] = w.notes;
  for (const s of S) {
    if (s.note && s.note.trim()) {
      const d = wday(s);
      noted[d] = (noted[d] ? noted[d] + ' / ' : '') + s.exercise + ': ' + s.note.trim();
    }
  }
  const nl = document.getElementById('noteList')!;
  nl.innerHTML = '';
  Object.keys(noted)
    .sort()
    .slice(-6)
    .forEach(d => {
      const li = document.createElement('li');
      const al = document.createElement('a');
      al.href = '#/s/' + d;
      al.textContent = fmtD(d) + ': ' + noted[d];
      li.appendChild(al);
      const low = noted[d].toLowerCase();
      if (
        low.indexOf('pain') >= 0 ||
        low.indexOf('sleep') >= 0 ||
        low.indexOf('sore') >= 0 ||
        low.indexOf('injury') >= 0
      )
        li.style.color = '#f0d060';
      nl.appendChild(li);
    });
  bwline(document.getElementById('chBw') as HTMLCanvasElement, BW);
  BWDATA = BW;
  const blank = () => Object.fromEntries(GROUPS.map(g => [g, 0]));
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
  MUSDATA = {
    labels: Object.keys(weeks).sort(),
    weeks: Object.keys(weeks)
      .sort()
      .map(k => weeks[k]),
  };
  const lm = document.getElementById('legMus')!;
  lm.innerHTML = '';
  const focus = prioMuscles(snap);
  const deprio = new Set(
    Object.keys(snap.priority || {})
      .filter(m => {
        const t = snap.priority[m];
        return (typeof t === 'string' ? t : t.tier) === 'deprioritize';
      })
      .map(m => m.toLowerCase())
  );
  GROUPS.forEach(g => {
    const sp = document.createElement('a');
    sp.className =
      'chip' +
      (focus.has(g.toLowerCase()) ? ' focus' : '') +
      (deprio.has(g.toLowerCase()) ? ' dim' : '');
    sp.href = '#/m/' + encodeURIComponent(g);
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
  const restDates: Record<string, boolean> = {};
  for (const w of W)
    if (w.status === 'rest' && !(dayDetail[w.date] && dayDetail[w.date].length))
      restDates[w.date] = true;
  const missed = missedExpected(SNAP.adherence);
  const drawCal = () => renderCal(viewY, viewM, dayDetail, restDates, missed);
  document.getElementById('calPrev')!.onclick = () => {
    viewM -= 1;
    if (viewM < 0) {
      viewM = 11;
      viewY -= 1;
    }
    drawCal();
  };
  document.getElementById('calNext')!.onclick = () => {
    viewM += 1;
    if (viewM > 11) {
      viewM = 0;
      viewY += 1;
    }
    drawCal();
  };
  drawCal();
  const wdate: Record<number, string> = {};
  for (const w of W) wdate[w.id] = w.date;
  const prs: Record<string, { s: any; ev: number }> = {};
  for (const s of S) {
    const k = s.exercise;
    const ev = e1rm(s.weight, s.reps);
    if (!prs[k] || ev > prs[k].ev) prs[k] = { s, ev };
  }
  const tbl = document.getElementById('prs') as HTMLTableElement;
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

function prTrophy(title: string): HTMLSpanElement {
  const tr = document.createElement('span');
  tr.className = 'prt';
  tr.title = title;
  tr.innerHTML =
    '<svg viewBox="0 0 16 16"><path d="M5 1.5h6v4.2a3 3 0 0 1-6 0V1.5z" fill="currentColor"/><path d="M5 2.5H3.2a2.8 2.8 0 0 0 2.9 3.6M11 2.5h1.8a2.8 2.8 0 0 1-2.9 3.6" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M8 8.7v2.1M6.2 12.8h3.6M5.4 14.5h5.2" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>';
  return tr;
}

function renderCal(
  year: number,
  month: number,
  dayDetail: Record<string, string[]>,
  restDates: Record<string, boolean>,
  missedDates: Record<string, string> = {}
) {
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
  const trainedDates = Object.keys(sByDate).sort();
  const breakDates: Record<string, boolean> = {};
  for (let i = 1; i < trainedDates.length; i += 1) {
    const gap = Math.round(
      (new Date(trainedDates[i] + 'T12:00:00').getTime() -
        new Date(trainedDates[i - 1] + 'T12:00:00').getTime()) /
        86400000
    );
    // Matches plan's break rule: gap of break_days + 1 or more.
    if (gap >= breakGap(SNAP)) breakDates[trainedDates[i]] = true;
  }
  for (let d = 1; d <= days; d += 1) {
    const key = year + '-' + String(month + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0');
    const trained = dayDetail[key] && dayDetail[key].length > 0;
    const rested = !trained && !!restDates[key];
    const missed = !trained && !rested && !!missedDates[key] && key <= todayS;
    const isPR = PR && PR.prDates.has(key);
    const el = document.createElement(trained || rested ? 'a' : 'div');
    const link = trained || rested ? (el as HTMLAnchorElement) : null;
    if (link) link.href = '#/s/' + key;
    if (missed) el.title = 'missed: expected ' + missedDates[key];
    el.className =
      'cd' +
      (trained ? ' t' : '') +
      (rested ? ' r' : '') +
      (missed ? ' m' : '') +
      (key === todayS ? ' today' : '') +
      (key > todayS ? ' fut' : '') +
      (breakDates[key] ? ' brk' : '');
    el.textContent = String(d);
    if (isPR) el.appendChild(prTrophy('personal record'));
    if (link) {
      link.addEventListener('click', hideTip);
      link.addEventListener('mousemove', ev => {
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
          }) +
          (SLOT_OF_DATE[key] ? ' ' + SLOT_OF_DATE[key] : '') +
          (isPR ? '  PR' : '');
        showTip(title, rows.length ? rows : [[null, 'tap to open']], ev.clientX, ev.clientY);
      });
      link.addEventListener('mouseleave', hideTip);
    }
    box.appendChild(el);
  }
}

function route() {
  const h = location.hash || '';
  const ds = h.slice(0, 4) === '#/s/' ? h.slice(4, 14) : '';
  const lift = h.slice(0, 4) === '#/l/' ? decodeURIComponent(h.slice(4)) : '';
  const mus = h.slice(0, 4) === '#/m/' ? decodeURIComponent(h.slice(4)) : '';
  const prog = h === '#/program';
  const lifts = h === '#/lifts';
  const muscles = h === '#/muscles';
  if (ds && isDate(ds) && D) {
    if (VIEW === 'dash') DASHY = window.scrollY;
    VIEW = 'sess';
    showSession(ds);
  } else if (lift && D) {
    if (VIEW === 'dash') DASHY = window.scrollY;
    VIEW = 'lift';
    showLift(lift);
  } else if (mus && D) {
    if (VIEW === 'dash') DASHY = window.scrollY;
    VIEW = 'mus';
    showMuscle(mus);
  } else if (prog && D) {
    if (VIEW === 'dash') DASHY = window.scrollY;
    VIEW = 'prog';
    showProgram();
  } else if (lifts && D) {
    if (VIEW === 'dash') DASHY = window.scrollY;
    VIEW = 'lifts';
    showLifts();
  } else if (muscles && D) {
    if (VIEW === 'dash') DASHY = window.scrollY;
    VIEW = 'muscles';
    showMuscles();
  } else {
    const restore = VIEW !== 'dash';
    VIEW = 'dash';
    document.getElementById('viewDash')!.hidden = false;
    document.getElementById('viewSession')!.hidden = true;
    document.getElementById('viewLift')!.hidden = true;
    document.getElementById('viewProgram')!.hidden = true;
    document.getElementById('viewMuscle')!.hidden = true;
    document.getElementById('viewLifts')!.hidden = true;
    document.getElementById('viewMuscles')!.hidden = true;
    document.title = 'reps dashboard';
    if (restore) {
      // Full repaint once layout settles: any canvas painted while the dash
      // was hidden keeps a zero-size bitmap that CSS stretches into smears.
      requestAnimationFrame(() => render());
      window.scrollTo(0, DASHY);
    }
  }
}

function showProgram() {
  document.getElementById('viewDash')!.hidden = true;
  document.getElementById('viewSession')!.hidden = true;
  document.getElementById('viewLift')!.hidden = true;
  document.getElementById('viewMuscle')!.hidden = true;
  document.getElementById('viewMuscle')!.hidden = true;
  document.getElementById('viewLifts')!.hidden = true;
  document.getElementById('viewMuscles')!.hidden = true;
  const v = document.getElementById('viewProgram')!;
  v.hidden = false;
  document.title = 'program';
  renderProgramPage(SNAP);
  window.scrollTo(0, 0);
}

function showMuscle(mus: string) {
  const match = GROUPS.filter(g => g.toLowerCase() === mus.toLowerCase())[0];
  if (!match || !D) {
    location.hash = '#/';
    return;
  }
  document.getElementById('viewDash')!.hidden = true;
  document.getElementById('viewSession')!.hidden = true;
  document.getElementById('viewLift')!.hidden = true;
  document.getElementById('viewProgram')!.hidden = true;
  const v = document.getElementById('viewMuscle')!;
  document.getElementById('viewLifts')!.hidden = true;
  document.getElementById('viewMuscles')!.hidden = true;
  v.hidden = false;
  document.title = match;
  MUSPAGE = { mus: match };
  paintMuscle(match);
  window.scrollTo(0, 0);
}

function paintMuscle(mus: string) {
  if (!D) return;
  const data = musclePageData(D.W, D.S, mus);
  const constants = (SNAP.constants || {}) as any;
  const entry = (constants.muscles || {})[mus] || {};
  const title = document.getElementById('musTitle')!;
  title.textContent = mus;
  const sub = document.getElementById('musSub')!;
  const mav = entry.mav ? entry.mav[0] + '-' + entry.mav[1] : 'no range';
  const mrv = entry.mrv !== undefined && entry.mrv !== null ? entry.mrv : 'no cap';
  const recent = data.counts.slice(-4);
  const avg = recent.length ? recent.reduce((a, b) => a + b, 0) / recent.length : 0;
  const last8 = data.counts.slice(-8);
  const trained = last8.filter(c => c > 0).length;
  const isFocus = prioMuscles(SNAP).has(mus.toLowerCase());
  sub.textContent =
    'MEV ' +
    (entry.mev !== undefined ? entry.mev : '?') +
    ' · MAV ' +
    mav +
    ' · MRV ' +
    mrv +
    ' · last 4 weeks avg ' +
    fmtV(Math.round(avg * 10) / 10) +
    '/wk · trained ' +
    trained +
    ' of last ' +
    last8.length +
    ' weeks' +
    (isFocus ? ' · focus' : '');
  muscleChart(
    document.getElementById('chMusVol') as HTMLCanvasElement,
    data.labels,
    data.counts,
    {
      mev: entry.mev !== undefined ? entry.mev : 0,
      mav: entry.mav || null,
      mrv: entry.mrv !== undefined ? entry.mrv : null,
    },
    entry.color || '#888'
  );
  const tbl = document.getElementById('musLegend')!;
  tbl.innerHTML = '';
  const ranked = data.lifts;
  const big = ranked.filter(l => l.share >= 0.04);
  const small = ranked.filter(l => l.share < 0.04);
  const smallSets = small.reduce((a, l) => a + l.sets, 0);
  const slices: PieSlice[] = big.map(l => ({
    label: l.ex,
    frac: l.share,
    link: '#/l/' + encodeURIComponent(l.ex),
  }));
  if (smallSets > 0) {
    const frac = smallSets / (data.total || 1);
    slices.push({ label: small.length + ' smaller lifts', frac, link: null });
  }
  MUSPIE = { slices, sets: slices.map((s, i) => (i < big.length ? big[i].sets : smallSets)) };
  pieChart(document.getElementById('chMusPie') as HTMLCanvasElement, slices);
  slices.forEach((s, i) => {
    const row = document.createElement('div');
    row.className = 'row';
    const sw = document.createElement('span');
    sw.className = 'sw';
    sw.style.background = piePalette(s.label);
    row.appendChild(sw);
    if (s.link) {
      const al = document.createElement('a');
      al.href = s.link;
      al.textContent = s.label;
      row.appendChild(al);
    } else {
      row.appendChild(document.createTextNode(s.label));
    }
    const meta = document.createElement('span');
    meta.className = 'meta';
    const share = Math.round(s.frac * 100);
    const sets = i < big.length ? big[i].sets : smallSets;
    meta.textContent = sets + ' sets · ' + share + '%';
    row.appendChild(meta);
    tbl.appendChild(row);
  });
  if (!slices.length) {
    const d = document.createElement('div');
    d.className = 'empty';
    d.textContent = 'nothing logged for this muscle yet';
    tbl.appendChild(d);
  }
}

function showSession(ds: string) {
  document.getElementById('viewDash')!.hidden = true;
  document.getElementById('viewLift')!.hidden = true;
  document.getElementById('viewProgram')!.hidden = true;
  document.getElementById('viewMuscle')!.hidden = true;
  document.getElementById('viewLifts')!.hidden = true;
  document.getElementById('viewMuscles')!.hidden = true;
  const v = document.getElementById('viewSession')!;
  v.hidden = false;
  const title = document.getElementById('sessTitle')!;
  const notes = document.getElementById('sessNotes')!;
  const body = document.getElementById('sessBody')!;
  const prev = document.getElementById('sessPrev') as HTMLAnchorElement;
  const next = document.getElementById('sessNext') as HTMLAnchorElement;
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
  title.textContent =
    new Date(ds + 'T12:00:00').toLocaleDateString(undefined, {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
    }) + (SLOT_OF_DATE[ds] ? ', ' + SLOT_OF_DATE[ds] : '');
  const wnotes = ws.map(w => w.notes).filter(n => n);
  const allRest = ws.length > 0 && ws.every(w => w.status === 'rest');
  if (allRest) {
    const badge = document.createElement('div');
    badge.className = 'card restday';
    badge.textContent = 'rest day';
    notes.appendChild(badge);
  }
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
      const prog = (SNAP.progression || {})[ex.toLowerCase()];
      const subs: string[] = [];
      if (prog) subs.push(prog.verdict + ', next ' + prog.next);
      const deload = SNAP.deload || [];
      if (
        deload.some(
          (d: any) =>
            (d.scope === 'lift' && (d.subject || '').toLowerCase() === ex.toLowerCase()) ||
            (d.scope === 'slot' && d.subject === SLOT_OF_DATE[ds])
        )
      ) {
        subs.push('deload');
      }
      if (subs.length) {
        const sub = document.createElement('span');
        sub.className = 'exsub';
        sub.textContent = subs.join(' · ');
        h.appendChild(sub);
      }
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
      const sn: Array<[string, number, string]> = [];
      byEx[ex].forEach((s, i) => {
        const tr = document.createElement('tr');
        const ev = e1rm(s.weight, s.reps);
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
        if (s.note) sn.push([ex, i + 1, s.note]);
        tbody.appendChild(tr);
      });
      wrap.appendChild(tbl);
      body.appendChild(wrap);
      if (sn.length) {
        const nd = document.createElement('div');
        nd.className = 'setnotes';
        sn.forEach(trip => {
          const ln = document.createElement('div');
          const b = document.createElement('b');
          b.textContent = trip[0] + ' ' + trip[1];
          ln.appendChild(b);
          ln.appendChild(document.createTextNode(trip[2]));
          nd.appendChild(ln);
        });
        notes.appendChild(nd);
      }
    });
  });
  document.title = fmtD(ds) + (allRest ? ' rest day' : ' training');
  window.scrollTo(0, 0);
}

function showLift(ex: string) {
  document.getElementById('viewDash')!.hidden = true;
  document.getElementById('viewSession')!.hidden = true;
  document.getElementById('viewProgram')!.hidden = true;
  document.getElementById('viewMuscle')!.hidden = true;
  document.getElementById('viewLifts')!.hidden = true;
  document.getElementById('viewMuscles')!.hidden = true;
  const v = document.getElementById('viewLift')!;
  v.hidden = false;
  const title = document.getElementById('liftTitle')!;
  const sub = document.getElementById('liftSub')!;
  const tl = document.getElementById('liftPRs')!;
  tl.innerHTML = '';
  title.textContent = ex;
  document.title = ex;
  const musBox = document.getElementById('liftMuscles')!;
  musBox.innerHTML = '';
  const trained = musclesOf(SNAP, ex);
  if (trained.length) {
    musBox.hidden = false;
    trained.forEach((m, i) => {
      if (i > 0) musBox.appendChild(document.createTextNode(', '));
      const al = document.createElement('a');
      al.href = '#/m/' + encodeURIComponent(m);
      const b = document.createElement('b');
      b.textContent = m;
      al.appendChild(b);
      musBox.appendChild(al);
    });
  } else {
    musBox.hidden = true;
  }
  const sets = D!.S.filter(s => s.exercise === ex);
  if (!sets.length) {
    sub.textContent = 'never logged';
    musBox.hidden = true;
    LIFTDATA = null;
    LIFTGOAL = null;
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
        ev: e1rm(top.weight, top.reps),
        pr: byDate[d].some(s => PR!.prIds.has(s.id)),
      };
    });
  const best = pts.slice().sort((a, b) => b.ev - a.ev)[0];
  const prog = (SNAP.progression || {})[ex.toLowerCase()];
  const progNext = prog ? parseNextTarget(prog.next) : null;
  sub.textContent =
    'best ' +
    best.w +
    ' x ' +
    best.r +
    ' (e1RM ' +
    best.ev.toFixed(1) +
    ') on ' +
    fmtD(best.date) +
    (prog ? ' | progression ' + prog.verdict + ', next ' + prog.next + ' ' + prog.direction : '');
  LIFTDATA = { pts, ex, fut: progNext ? progNext.ev : null };
  liftChart(
    document.getElementById('chLift') as HTMLCanvasElement,
    pts,
    ex,
    -1,
    progNext ? progNext.ev : null
  );
  const goal = goalByExercise(SNAP, ex);
  const goalCard = document.getElementById('liftGoalCard')!;
  if (goal && goal.checkpoints && goal.checkpoints.length) {
    goalCard.hidden = false;
    const acts = (goal.actuals || []).map((a: any) => ({ date: a.date, ev: a.e1rm }));
    const tops: Record<string, { w: number; r: number }> = {};
    acts.forEach((a: { date: string }) => {
      const top = topSetOn(D!.S, wdate, ex, a.date);
      if (top) tops[a.date] = top;
    });
    LIFTGOAL = { ex, actuals: acts, checkpoints: goal.checkpoints || [], tops };
    const lpct = goalPercent({
      target_e1rm: goal.target_e1rm,
      checkpoints: goal.checkpoints || [],
      actuals: acts,
    });
    goalChart(
      document.getElementById('chGoal') as HTMLCanvasElement,
      acts,
      goal.checkpoints || [],
      liftColor(ex)
    );
    const cap = document.getElementById('liftGoalCap')!;
    cap.textContent =
      'Target e1RM ' +
      fmtV(goal.target_e1rm) +
      ' by ' +
      fmtD(goal.deadline) +
      (lpct !== null ? ', ' + lpct + '% there' : '') +
      (goal.next_checkpoint !== null && goal.next_checkpoint !== undefined
        ? ', next checkpoint ' + fmtV(goal.next_checkpoint)
        : ', trajectory complete') +
      (goal.on_track === false ? ', OFF TRACK' : '') +
      (goal.slippage ? ', slippage: deadline needs room' : '') +
      '. Dashed line is the plan, hollow points are future.';
  } else {
    goalCard.hidden = true;
    LIFTGOAL = null;
  }
  const setup = notesOf(SNAP, ex);
  const setupCard = document.getElementById('liftSetupCard')!;
  if (setup.length) {
    setupCard.hidden = false;
    const box = document.getElementById('liftSetup')!;
    box.innerHTML = '';
    setup.forEach(n => {
      const d = document.createElement('div');
      d.textContent = n;
      box.appendChild(d);
    });
  } else {
    setupCard.hidden = true;
  }
  const order = D!.S.slice().sort((a, b) =>
    a.created < b.created ? -1 : a.created > b.created ? 1 : a.id - b.id
  );
  const seen = new Set<string>();
  const top2 = { ev: 0 };
  let lastPR: string | null = null;
  order.forEach(s => {
    if (s.exercise !== ex) return;
    const ev = e1rm(s.weight, s.reps);
    if (!seen.has(ex)) {
      seen.add(ex);
      top2.ev = ev;
      return;
    }
    if (ev > top2.ev) {
      const jump = ev - top2.ev;
      top2.ev = ev;
      lastPR = wdate[s.workout_id];
      const item = document.createElement('a');
      item.className = 'tl-item';
      item.href = '#/s/' + wdate[s.workout_id];
      const date = document.createElement('div');
      date.className = 'tl-date';
      date.textContent = fmtD(wdate[s.workout_id]);
      item.appendChild(date);
      const rail = document.createElement('div');
      rail.className = 'tl-rail';
      item.appendChild(rail);
      const what = document.createElement('div');
      what.className = 'tl-what';
      const b = document.createElement('b');
      b.textContent = s.weight + ' x ' + s.reps + ' (e1RM ' + ev.toFixed(1) + ')';
      what.appendChild(b);
      const delta = document.createElement('span');
      delta.className = 'tl-delta';
      delta.textContent = '+' + jump.toFixed(1);
      what.appendChild(delta);
      item.appendChild(what);
      tl.appendChild(item);
    }
  });
  const prNote = document.createElement('div');
  prNote.className = 'cap';
  if (!lastPR) {
    prNote.textContent = 'no PR yet, the first logged set is the baseline';
  } else {
    const days = Math.round(
      (new Date().getTime() - new Date(lastPR + 'T12:00:00').getTime()) / 86400000
    );
    prNote.textContent =
      days <= 0 ? 'PR today' : 'last PR ' + days + 'd ago (' + fmtD(lastPR) + ')';
  }
  tl.insertBefore(prNote, tl.firstChild);
  window.scrollTo(0, 0);
}

function refreshTrend() {
  drawTrendFilters();
  drawTrendChips();
  drawMinis();
}

function liftMatches(t: string, i: number, facet: string): boolean {
  if (facet === 'goal') return goalByExercise(SNAP, t) !== null;
  if (facet === 'stall') {
    const pts = (TREND.series[i].filter(v => v !== null) as number[]).map(ev => ({ ev }));
    return isStalling(pts) || deloadWatch(pts);
  }
  if (facet === 'focus') {
    const prio = prioMuscles(SNAP);
    return musclesOf(SNAP, t).some(m => prio.has(m.toLowerCase()));
  }
  return false;
}

function passFilter(t: string, i: number): boolean {
  if (FILTER.q && t.toLowerCase().indexOf(FILTER.q) < 0) return false;
  if (!FILTER.facets.size) return true;
  for (const f of FILTER.facets) if (liftMatches(t, i, f)) return true;
  return false;
}

function drawTrendFilters() {
  const box = document.getElementById('trendFacets')!;
  if (box.childElementCount) {
    box.querySelectorAll('button[data-facet]').forEach(b => {
      const f = (b as HTMLButtonElement).dataset.facet || '';
      const on = FILTER.facets.has(f);
      b.classList.toggle('off', !on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    return;
  }
  const search = document.getElementById('trendSearch') as HTMLInputElement;
  search.value = FILTER.q;
  search.addEventListener('input', () => {
    FILTER.q = search.value.trim().toLowerCase();
    refreshTrend();
  });
  const mkReset = () => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'chip mini';
    b.textContent = 'Reset';
    b.addEventListener('click', () => {
      FILTER.q = '';
      FILTER.facets.clear();
      search.value = '';
      HADHIDDEN = true;
      HIDDEN.clear();
      saveHidden();
      refreshTrend();
    });
    box.appendChild(b);
  };
  mkReset();
  [
    ['Goals', 'goal'],
    ['Stalling', 'stall'],
    ['Focus', 'focus'],
  ].forEach(([label, facet]) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'chip mini off';
    b.textContent = label;
    b.dataset.facet = facet;
    b.setAttribute('aria-pressed', 'false');
    b.addEventListener('click', () => {
      if (FILTER.facets.has(facet)) FILTER.facets.delete(facet);
      else FILTER.facets.add(facet);
      refreshTrend();
    });
    box.appendChild(b);
  });
}
function drawMinis() {
  const grid = document.getElementById('trendGrid')!;
  grid.innerHTML = '';
  const shown = TREND.top
    .map((t, i) => i)
    .filter(i => !HIDDEN.has(TREND.top[i]) && passFilter(TREND.top[i], i));
  if (!shown.length) {
    const e = document.createElement('div');
    e.className = 'empty';
    e.textContent = 'no lifts match, adjust filters or use Reset';
    grid.appendChild(e);
    return;
  }
  const wd: Record<number, string> = {};
  for (const w of SNAP.workouts) wd[w.id] = w.date;
  const prDate: Record<string, Record<string, boolean>> = {};
  for (const s of SNAP.sets) {
    if (PR && PR.prIds.has(s.id))
      (prDate[s.exercise] = prDate[s.exercise] || {})[wd[s.workout_id] || ''] = true;
  }
  const jobs: Array<[HTMLCanvasElement, (number | null)[], string]> = [];
  shown.forEach(i => {
    const t = TREND.top[i];
    const vals = TREND.series[i];
    const wrap = document.createElement('div');
    wrap.className = 'mini';
    const h = document.createElement('div');
    h.className = 'minititle';
    const al = document.createElement('a');
    al.href = '#/l/' + encodeURIComponent(t);
    al.textContent = t;
    h.appendChild(al);
    const pts = (vals.filter(v => v !== null) as number[]).map(ev => ({ ev }));
    const marks: Array<[string, string]> = [];
    if (isStalling(pts)) marks.push(['stalling', 'bad']);
    else if (deloadWatch(pts)) marks.push(['slipping', 'bad']);
    if (goalByExercise(SNAP, t)) marks.push(['goal', 'plan']);
    if (marks.length) {
      const wrap2 = document.createElement('span');
      wrap2.className = 'ministat';
      marks.forEach(m => {
        const s = document.createElement('span');
        s.className = 'minisub ' + m[1];
        s.textContent = m[0];
        wrap2.appendChild(s);
      });
      h.appendChild(wrap2);
    }
    wrap.appendChild(h);
    const cv = document.createElement('canvas');
    wrap.appendChild(cv);
    wrap.addEventListener('click', ev => {
      if ((ev.target as HTMLElement).tagName !== 'A')
        location.hash = '#/l/' + encodeURIComponent(t);
    });
    grid.appendChild(wrap);
    const col = liftColor(t),
      prs = prDate[t] || {};
    jobs.push([cv, vals, col]);
    const miniShow = (cx: number, cy: number) => {
      if (!vis(cv)) {
        hideTip();
        return;
      }
      const r = cv.getBoundingClientRect();
      const n = vals.length;
      const pxi = (k: number) => 30 + (r.width - 30 - 6) * (n <= 1 ? 1 : k / (n - 1));
      let bi = -1,
        bd = 1e9;
      for (let k = 0; k < n; k += 1) {
        if (vals[k] === null) continue;
        const d = Math.abs(pxi(k) - (cx - r.left));
        if (d < bd) {
          bd = d;
          bi = k;
        }
      }
      if (bi < 0 || bd > 30) {
        hideTip();
        mini(cv, TREND.days, vals, col);
        return;
      }
      mini(cv, TREND.days, vals, col, bi);
      const m = TREND.meta[i] && TREND.meta[i][bi];
      const detail = m ? ' (' + m.w + ' x ' + m.r + ')' : '';
      showTip(
        TREND.days[bi],
        [[col, fmtV(vals[bi]!) + detail + (prs[TREND.days[bi]] ? ' PR' : '')]],
        cx,
        cy
      );
    };
    bindHover(cv, miniShow);
    cv.addEventListener('mouseleave', () => {
      hideTip();
      if (vis(cv)) mini(cv, TREND.days, vals, col);
    });
  });
  // Never paint while hidden: display:none reports zero size and fit() would
  // bake a 50px bitmap that CSS then stretches into smears. Canvases stay
  // blank until returning to the dash repaints them, see route().
  if (grid.clientWidth > 0) jobs.forEach(j => mini(j[0], TREND.days, j[1], j[2]));
}
function drawTrendChips() {
  const lt = document.getElementById('legTrend')!;
  lt.innerHTML = '';
  const mkBtn = (label: string, hide: boolean) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'chip mini';
    b.textContent = label;
    b.addEventListener('click', () => {
      HADHIDDEN = true;
      if (hide) TREND.top.forEach(t => HIDDEN.add(t));
      else {
        HIDDEN.clear();
        FILTER.q = '';
        FILTER.facets.clear();
        const search = document.getElementById('trendSearch') as HTMLInputElement;
        if (search) search.value = '';
      }
      saveHidden();
      refreshTrend();
    });
    lt.appendChild(b);
  };
  mkBtn('All', false);
  mkBtn('None', true);
  TREND.top.forEach((t, i) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'chip' + (HIDDEN.has(t) ? ' off' : '');
    b.setAttribute('aria-pressed', HIDDEN.has(t) ? 'false' : 'true');
    const sw = document.createElement('span');
    sw.className = 'sw';
    sw.style.background = liftColor(t);
    b.appendChild(sw);
    b.appendChild(document.createTextNode(t));
    b.addEventListener('click', () => {
      HADHIDDEN = true;
      if (HIDDEN.has(t)) HIDDEN.delete(t);
      else HIDDEN.add(t);
      saveHidden();
      refreshTrend();
    });
    lt.appendChild(b);
  });
}

function renderNext(snap: any, W: any[], S: any[]) {
  // Prospective card: what the rotation says is up next, with last numbers
  // and progression targets per movement. Computed from the same inputs as
  // plan's slot guess (last done session + rotation step).
  const card = document.getElementById('nextCard')!;
  card.innerHTML = '';
  const wdate: Record<number, string> = {};
  for (const w of W) wdate[w.id] = w.date;
  const done = W.filter(w => w.status === 'done' && S.some(s => s.workout_id === w.id)).sort(
    (a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : a.id - b.id)
  );
  const moves = splitDayExercises(snap.split_active || []);
  const rot: string[] = snap.rotation || [];
  const last = done.length ? done[done.length - 1] : null;
  const lastEx = last ? S.filter(s => s.workout_id === last.id).map(s => s.exercise) : [];
  const lastDay = last ? labelSession(lastEx, moves) : null;
  const nxt = nextSlot(lastDay, rot);
  if (!last || !lastDay || !nxt.day || !(moves[nxt.day] || []).length) {
    const e = document.createElement('div');
    e.className = 'empty';
    e.textContent = !Object.keys(moves).length
      ? 'no program synced yet, split show in chat is the source'
      : 'log a session and the next slot appears here';
    card.appendChild(e);
    return;
  }
  const h = document.createElement('h3');
  h.textContent = 'Next up: ' + nxt.day;
  card.appendChild(h);
  const prog = snap.progression || {};
  (moves[nxt.day] || []).forEach(m => {
    const hist = S.filter(s => (s.exercise || '').toLowerCase() === m.toLowerCase());
    const lastDate = hist.length
      ? hist
          .map(s => wdate[s.workout_id] || (s.created || '').slice(0, 10))
          .sort()
          .pop()!
      : null;
    const top = lastDate ? topSetOn(S, wdate, m, lastDate) : null;
    const p = prog[m.toLowerCase()];
    const row = document.createElement('div');
    row.className = 'nextrow';
    const al = document.createElement('a');
    al.href = '#/l/' + encodeURIComponent(m);
    al.textContent = m;
    row.appendChild(al);
    const detail = document.createElement('span');
    detail.className = 'meta';
    detail.textContent =
      (top ? 'last ' + top.w + ' x ' + top.r + ' · ' + fmtD(lastDate!) : 'never logged') +
      (p ? ' → target ' + p.next + ' ' + p.direction : ' · no target yet');
    row.appendChild(detail);
    card.appendChild(row);
  });
  const cap = document.createElement('div');
  cap.className = 'cap';
  cap.textContent = nxt.basis + '. Confirm or override in chat before training.';
  card.appendChild(cap);
}

function renderSignals(snap: any) {
  // Warning signs in words. The backend computes every line; the page only
  // reads them aloud, worst first. Nothing here is generated or inferred.
  const wrap = document.getElementById('sigWrap')!;
  const card = document.getElementById('sigCard')!;
  card.innerHTML = '';
  if (!('signals' in snap)) {
    wrap.hidden = true;
    return;
  }
  wrap.hidden = false;
  const rows: Array<{ severity: string; text: string }> = snap.signals || [];
  if (!rows.length) {
    const e = document.createElement('div');
    e.className = 'empty';
    e.textContent = 'all clear, nothing flagged';
    card.appendChild(e);
    return;
  }
  rows.forEach(r => {
    const row = document.createElement('div');
    row.className = 'sigrow';
    const tag = document.createElement('span');
    tag.className = 'sigtag sig-' + r.severity;
    tag.textContent = r.severity.toUpperCase();
    row.appendChild(tag);
    const tx = document.createElement('span');
    tx.textContent = r.text;
    row.appendChild(tx);
    card.appendChild(row);
  });
}

function renderAdh(snap: any) {
  const wrap = document.getElementById('adhWrap')!;
  const card = document.getElementById('adhCard')!;
  card.innerHTML = '';
  const days: AdherenceDay[] = (snap.adherence && snap.adherence.days) || [];
  if (!days.length) {
    wrap.hidden = true;
    return;
  }
  wrap.hidden = false;
  const strip = document.createElement('div');
  strip.className = 'dtstrip';
  days.forEach(d => {
    const s = document.createElement('span');
    s.className = 'dt dt-' + d.status.replace('_', '');
    s.title = d.date + ': ' + d.status + ' (expected ' + d.expected + ')';
    strip.appendChild(s);
  });
  card.appendChild(strip);
  const weeks = adherenceWeeks(days).slice(-8);
  const list = document.createElement('div');
  list.className = 'adhweeks';
  weeks.forEach(w => {
    const row = document.createElement('div');
    row.textContent = w.week + ' · ' + w.trained + '/' + w.expected + ' sessions';
    list.appendChild(row);
  });
  card.appendChild(list);
  const cap = document.createElement('div');
  cap.className = 'cap';
  cap.textContent = 'Green is trained as planned, red is missed, hollow is scheduled rest.';
  card.appendChild(cap);
}

function renderNow(snap: any, W: any[], S: any[]) {
  const lines = document.getElementById('nowLines')!;
  lines.innerHTML = '';
  const esc = (s: string) =>
    (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const line = (html: string) => {
    const d = document.createElement('div');
    d.innerHTML = html;
    lines.appendChild(d);
  };
  const todayS = new Date().toISOString().slice(0, 10);
  const todayRows = W.filter(w => w.date === todayS);
  if (todayRows.some(w => w.status === 'open')) line('<b>Workout open today.</b>');
  else if (todayRows.some(w => w.status === 'rest')) line('Rest day today.');
  const doneDates = W.filter(w => w.status === 'done' && S.some(s => s.workout_id === w.id))
    .map(w => w.date)
    .sort();
  if (doneDates.length) {
    const gap = Math.round(
      (new Date(todayS + 'T12:00:00').getTime() -
        new Date(doneDates[doneDates.length - 1] + 'T12:00:00').getTime()) /
        86400000
    );
    if (gap >= breakGap(snap))
      line('<b>Break:</b> ' + gap + 'd since last session, no PR attempts.');
  }
  const deload = snap.deload || [];
  deload.forEach((d: any) => line('<b>Deloading</b> ' + esc(d.subject) + '.'));
  const prio = snap.priority || {};
  Object.keys(prio).forEach(m => {
    const t = prio[m];
    const tier = typeof t === 'string' ? t : t.tier;
    if (tier && tier !== 'maintain') line('<b>Focus:</b> ' + esc(m) + '.');
  });
  const flags = snap.flags || [];
  flags
    .slice(0, 3)
    .forEach((f: any) => line('<b>Watch:</b> ' + esc(f.subject) + ', ' + esc(f.reason || '')));
  if (flags.length > 3) line('+' + (flags.length - 3) + ' more flags in chat.');
}

function musclesOf(snap: any, exercise: string): string[] {
  const rows = snap.mapping || [];
  const hit = rows.filter((r: any) => (r.exercise || '').toLowerCase() === exercise.toLowerCase());
  if (!hit.length) return [];
  return (hit[0].muscles || '')
    .split(',')
    .map((x: string) => x.trim())
    .filter((x: string) => x);
}

function notesOf(snap: any, exercise: string): string[] {
  const rows = snap.movement_notes || [];
  return rows
    .filter((r: any) => (r.exercise || '').toLowerCase() === exercise.toLowerCase())
    .map((r: any) => r.note)
    .filter((n: string) => n);
}

function prioMuscles(snap: any): Set<string> {
  const prio = snap.priority || {};
  return new Set(
    Object.keys(prio)
      .filter(m => {
        const t = prio[m];
        const tier = typeof t === 'string' ? t : t.tier;
        return tier === 'priority';
      })
      .map(m => m.toLowerCase())
  );
}

function mevOf(snap: any, g: string): number {
  const c = (snap.constants || {}).muscles || {};
  return (c[g] && c[g].mev) || 0;
}

function goalByExercise(snap: any, exercise: string): any {
  const goals = snap.goals || [];
  const hit = goals.filter((g: any) => (g.exercise || '').toLowerCase() === exercise.toLowerCase());
  return hit.length ? hit[0] : null;
}

function orderedSplitDays(snap: any): {
  rows: Array<{ day: string; slot: number; movements: string; sets: number }>;
  ordered: string[];
  rot: string[];
} {
  const rows: Array<{ day: string; slot: number; movements: string; sets: number }> =
    snap.split_active || [];
  const rot: string[] = snap.rotation || [];
  const byDay: Record<string, typeof rows> = {};
  rows.forEach(r => {
    (byDay[r.day] = byDay[r.day] || []).push(r);
  });
  const ordered = Object.keys(byDay).sort((a, b) => {
    const ia = rot.indexOf(a);
    const ib = rot.indexOf(b);
    if (ia >= 0 && ib >= 0) return ia - ib;
    if (ia >= 0) return -1;
    if (ib >= 0) return 1;
    return a < b ? -1 : 1;
  });
  return { rows, ordered, rot };
}

function renderProgramSummary(snap: any) {
  const { rows, ordered, rot } = orderedSplitDays(snap);
  const rotLine = document.getElementById('rotLine')!;
  rotLine.textContent = '';
  if (!rows.length) {
    rotLine.textContent = 'No program synced yet, split show in chat is the source.';
    return;
  }
  const seq = rot.length ? rot : ordered;
  rotLine.appendChild(document.createTextNode('Rotating ' + seq.join(' / ') + '. '));
  const link = document.createElement('a');
  link.href = '#/program';
  link.id = 'progLink';
  link.textContent = 'Full split';
  rotLine.appendChild(link);
  rotLine.appendChild(document.createTextNode(' · '));
  const liftsLink = document.createElement('a');
  liftsLink.href = '#/lifts';
  liftsLink.textContent = 'Movements';
  rotLine.appendChild(liftsLink);
  rotLine.appendChild(document.createTextNode(' · '));
  const musclesLink = document.createElement('a');
  musclesLink.href = '#/muscles';
  musclesLink.textContent = 'Muscles';
  rotLine.appendChild(musclesLink);
  rotLine.appendChild(document.createTextNode('.'));
}

function renderProgramPage(snap: any) {
  const sub = document.getElementById('progSub')!;
  const grid = document.getElementById('progGrid')!;
  grid.innerHTML = '';
  const { rows, ordered, rot } = orderedSplitDays(snap);
  sub.textContent = rot.length ? 'Active split, rotation: ' + rot.join(' / ') : 'Active split.';
  if (!rows.length) {
    const e = document.createElement('div');
    e.className = 'empty';
    e.textContent = 'no program synced yet, split show in chat is the source';
    grid.appendChild(e);
    return;
  }
  const byDay: Record<string, typeof rows> = {};
  rows.forEach(r => {
    (byDay[r.day] = byDay[r.day] || []).push(r);
  });
  const panels = document.createElement('div');
  panels.className = 'daypanels';
  ordered.forEach(day => {
    const panel = document.createElement('div');
    panel.className = 'daypanel';
    const h = document.createElement('h2');
    h.textContent = day;
    panel.appendChild(h);
    const slots = byDay[day].slice().sort((a, b) => a.slot - b.slot);
    const seen: string[] = [];
    slots.forEach(r => {
      (r.movements || '')
        .split('/')
        .map((m: string) => m.trim())
        .forEach((m: string) => {
          musclesOf(snap, m).forEach(mu => {
            if (seen.indexOf(mu) < 0) seen.push(mu);
          });
        });
    });
    const mus = document.createElement('div');
    mus.className = 'daymuscles';
    mus.textContent = seen.join(' · ');
    panel.appendChild(mus);
    const tbl = document.createElement('table');
    const thead = document.createElement('thead');
    const head = document.createElement('tr');
    ['', 'movement', 'sets', 'muscles'].forEach(t => {
      const th = document.createElement('th');
      th.setAttribute('scope', 'col');
      th.textContent = t;
      head.appendChild(th);
    });
    thead.appendChild(head);
    tbl.appendChild(thead);
    const tbody = document.createElement('tbody');
    tbl.appendChild(tbody);
    slots.forEach(r => {
      const tr = document.createElement('tr');
      const num = document.createElement('td');
      num.textContent = String(r.slot);
      tr.appendChild(num);
      const mv = document.createElement('td');
      const moves = (r.movements || '').split('/').map((m: string) => m.trim());
      moves.forEach((m: string, mi: number) => {
        if (mi > 0) mv.appendChild(document.createTextNode(' / '));
        const al = document.createElement('a');
        al.href = '#/l/' + encodeURIComponent(m);
        al.textContent = m;
        mv.appendChild(al);
      });
      tr.appendChild(mv);
      const st = document.createElement('td');
      st.textContent = String(r.sets);
      tr.appendChild(st);
      const mu = document.createElement('td');
      const uniq = Array.from(new Set(moves.flatMap((m: string) => musclesOf(snap, m))));
      const focus = prioMuscles(snap);
      uniq.forEach((m, mi) => {
        if (mi > 0) mu.appendChild(document.createTextNode(', '));
        if (focus.has(m.toLowerCase())) {
          const b = document.createElement('b');
          b.textContent = m;
          mu.appendChild(b);
        } else {
          mu.appendChild(document.createTextNode(m));
        }
      });
      tr.appendChild(mu);
      tbody.appendChild(tr);
    });
    panel.appendChild(tbl);
    panels.appendChild(panel);
  });
  grid.appendChild(panels);
}

const LIFTF: { q: string; facets: Set<string> } = { q: '', facets: new Set() };
const MUSF: Set<string> = new Set();

function holdExercises(auto: any): Set<string> {
  const out = new Set<string>();
  for (const h of (auto && auto.holds) || []) {
    for (const m of (h.movements || '').split('/')) {
      const t = m.trim().toLowerCase();
      if (t) out.add(t);
    }
  }
  return out;
}

function recentChanges(auto: any, changes: any[]): Set<string> {
  const out = new Set<string>();
  for (const ch of changes || []) {
    if (ch.reverted_on) continue;
    for (const m of (ch.after_movements || '').split('/')) {
      const t = m.trim().toLowerCase();
      if (t) out.add(t);
    }
  }
  return out;
}

function changeOf(changes: any[], ex: string): any {
  // Newest unreverted change touching the exercise (snapshot is newest-first).
  const low = ex.toLowerCase();
  for (const ch of changes || []) {
    if (ch.reverted_on) continue;
    const moves = (ch.after_movements || '').split('/').map((m: string) => m.trim().toLowerCase());
    if (moves.indexOf(low) >= 0) return ch;
  }
  return null;
}

function groupedOf(auto: any, ex: string): string[] {
  const out: string[] = [];
  for (const [mus, lifts] of Object.entries((auto && auto.grouped) || {})) {
    if ((lifts as string[]).some(l => l.toLowerCase() === ex.toLowerCase())) out.push(mus);
  }
  return out;
}

function liftRank(
  t: string,
  i: number,
  fx: {
    held: Set<string>;
    changed: Set<string>;
    prog: any;
  }
): number {
  if (fx.held.has(t.toLowerCase()) || fx.changed.has(t.toLowerCase())) return 0;
  const pts = (TREND.series[i].filter(v => v !== null) as number[]).map(ev => ({ ev }));
  if (isStalling(pts) || deloadWatch(pts)) return 1;
  if (goalByExercise(SNAP, t)) return 2;
  return 3;
}

function liftPasses(
  t: string,
  i: number,
  fx: { held: Set<string>; changed: Set<string> }
): boolean {
  if (LIFTF.q && t.toLowerCase().indexOf(LIFTF.q) < 0) return false;
  if (!LIFTF.facets.size) return true;
  for (const f of LIFTF.facets) {
    if (f === 'autoreg' && (fx.held.has(t.toLowerCase()) || fx.changed.has(t.toLowerCase())))
      return true;
    if (f === 'grouped' && groupedOf(SNAP.autoreg, t).length) return true;
    if (f === 'goal' && goalByExercise(SNAP, t)) return true;
    if (f === 'stall') {
      const pts = (TREND.series[i].filter(v => v !== null) as number[]).map(ev => ({ ev }));
      if (isStalling(pts) || deloadWatch(pts)) return true;
    }
    if (f === 'focus' && musclesOf(SNAP, t).some(m => prioMuscles(SNAP).has(m.toLowerCase())))
      return true;
  }
  return false;
}

function showLifts() {
  document.getElementById('viewDash')!.hidden = true;
  document.getElementById('viewSession')!.hidden = true;
  document.getElementById('viewLift')!.hidden = true;
  document.getElementById('viewProgram')!.hidden = true;
  document.getElementById('viewMuscle')!.hidden = true;
  document.getElementById('viewMuscles')!.hidden = true;
  const v = document.getElementById('viewLifts')!;
  v.hidden = false;
  document.title = 'movements';
  const grid = document.getElementById('liftGrid')!;
  grid.innerHTML = '';
  const sub = document.getElementById('liftsSub')!;
  const wdate: Record<number, string> = {};
  for (const w of SNAP.workouts || []) wdate[w.id] = w.date;
  const prDate: Record<string, Record<string, boolean>> = {};
  for (const s of SNAP.sets || []) {
    if (PR && PR.prIds.has(s.id))
      (prDate[s.exercise] = prDate[s.exercise] || {})[wdate[s.workout_id] || ''] = true;
  }
  const todayS = new Date().toISOString().slice(0, 10);
  const thisMonth = todayS.slice(0, 7);
  const holds: Array<{ movements: string; action: string; hold_until: string; reason: string }> =
    (SNAP.autoreg && SNAP.autoreg.holds) || [];
  const held = holdExercises(SNAP.autoreg);
  const changed = recentChanges(SNAP.autoreg, SNAP.autoreg_changes || []);
  const prog = SNAP.progression || {};
  const notesByEx: Record<string, string[]> = {};
  for (const n of SNAP.movement_notes || []) {
    (notesByEx[n.exercise] = notesByEx[n.exercise] || []).push(n.note);
  }
  const order = TREND.top
    .map((t, i) => i)
    .sort(
      (a, b) =>
        liftRank(TREND.top[a], a, { held, changed, prog }) -
          liftRank(TREND.top[b], b, { held, changed, prog }) ||
        (TREND.top[a] < TREND.top[b] ? -1 : 1)
    )
    .filter(i => liftPasses(TREND.top[i], i, { held, changed }));
  sub.textContent = order.length + ' movements';
  const jobs: Array<[HTMLCanvasElement, (number | null)[], string]> = [];
  order.forEach(i => {
    const t = TREND.top[i];
    const vals = TREND.series[i];
    const col = liftColor(t);
    const card = document.createElement('div');
    card.className = 'card';
    card.style.margin = '0';
    const row = document.createElement('div');
    row.className = 'listrow';
    card.appendChild(row);
    const info = document.createElement('div');
    info.className = 'listinfo';
    row.appendChild(info);
    const chartbox = document.createElement('div');
    chartbox.className = 'listchart';
    row.appendChild(chartbox);
    const h = document.createElement('div');
    h.className = 'minititle';
    const al = document.createElement('a');
    al.href = '#/l/' + encodeURIComponent(t);
    al.textContent = t;
    h.appendChild(al);
    if (Object.keys(prDate[t] || {}).some(d => d.slice(0, 7) === thisMonth))
      h.appendChild(prTrophy("PR'd this month"));
    const marks: Array<[string, string]> = [];
    const myHolds = holds.filter(hh =>
      hh.movements.split('/').some(m => m.trim().toLowerCase() === t.toLowerCase())
    );
    myHolds.forEach(hh =>
      marks.push([
        hh.action + ', holds until ' + hh.hold_until + (hh.reason ? ' (' + hh.reason + ')' : ''),
        'bad',
      ])
    );
    const change = changeOf(SNAP.autoreg_changes || [], t);
    if (change)
      marks.push(['adjusted ' + change.date + ': ' + (change.evidence || change.action), 'plan']);
    const grouped = groupedOf(SNAP.autoreg, t);
    if (grouped.length) marks.push(['grouped fatigue: ' + grouped.join(', '), 'bad']);
    const pts = (vals.filter(x => x !== null) as number[]).map(ev => ({ ev }));
    if (isStalling(pts)) marks.push(['stalling', 'bad']);
    else if (deloadWatch(pts)) marks.push(['slipping', 'bad']);
    if (goalByExercise(SNAP, t)) marks.push(['goal', 'plan']);
    if (marks.length) {
      const wrap = document.createElement('span');
      wrap.className = 'ministat';
      marks.forEach(m => {
        const s = document.createElement('span');
        s.className = 'minisub ' + m[1];
        s.textContent = m[0];
        wrap.appendChild(s);
      });
      h.appendChild(wrap);
    }
    info.appendChild(h);
    const mus = musclesOf(SNAP, t);
    if (mus.length) {
      const mrow = document.createElement('div');
      mrow.className = 'legend';
      mus.forEach(m => {
        const a = document.createElement('a');
        a.className = 'chip';
        a.href = '#/m/' + encodeURIComponent(m);
        a.textContent = m;
        mrow.appendChild(a);
      });
      info.appendChild(mrow);
    }
    const cv = document.createElement('canvas');
    chartbox.appendChild(cv);
    const sets = (SNAP.sets || []).filter((s: any) => s.exercise === t);
    if (sets.length) {
      const last = sets.slice().sort((a: any, b: any) => {
        const d = (wdate[b.workout_id] || '').localeCompare(wdate[a.workout_id] || '');
        return d !== 0 ? d : b.id - a.id;
      })[0];
      const best = sets
        .slice()
        .sort((a: any, b: any) => e1rm(b.weight, b.reps) - e1rm(a.weight, a.reps))[0];
      const line = document.createElement('div');
      line.className = 'cap';
      line.textContent =
        'last ' +
        last.weight +
        ' x ' +
        last.reps +
        ' · best ' +
        best.weight +
        ' x ' +
        best.reps +
        ' (e1RM ' +
        fmtV(e1rm(best.weight, best.reps)) +
        ')';
      info.appendChild(line);
    }
    const p = prog[t.toLowerCase()];
    if (p) {
      const arrows: Record<string, [string, string]> = {
        up: ['↑', '#7fd67f'],
        flat: ['→', '#b0aca2'],
        down: ['↓', '#f09090'],
      };
      const pl = document.createElement('div');
      pl.className = 'cap';
      pl.appendChild(document.createTextNode(p.verdict + ' '));
      if (p.direction && arrows[p.direction]) {
        const arrow = document.createElement('span');
        arrow.textContent = arrows[p.direction][0];
        arrow.style.color = arrows[p.direction][1];
        arrow.style.fontWeight = '700';
        pl.appendChild(arrow);
        pl.appendChild(document.createTextNode(' ' + p.next + (p.note ? ' · ' + p.note : '')));
      } else {
        pl.appendChild(document.createTextNode('→ ' + p.next + (p.note ? ' · ' + p.note : '')));
      }
      info.appendChild(pl);
    }
    (notesByEx[t] || []).forEach(n => {
      const nl = document.createElement('div');
      nl.className = 'cap';
      nl.textContent = 'setup: ' + n;
      info.appendChild(nl);
    });
    card.addEventListener('click', ev => {
      if ((ev.target as HTMLElement).tagName !== 'A')
        location.hash = '#/l/' + encodeURIComponent(t);
    });
    grid.appendChild(card);
    jobs.push([cv, vals, col]);
  });
  drawLiftFilters();
  if (grid.clientWidth > 0) jobs.forEach(j => mini(j[0], TREND.days, j[1], j[2]));
  window.scrollTo(0, 0);
}

function drawLiftFilters() {
  const box = document.getElementById('liftFacets')!;
  if (box.childElementCount) {
    box.querySelectorAll('button[data-facet]').forEach(b => {
      const f = (b as HTMLButtonElement).dataset.facet || '';
      const on = LIFTF.facets.has(f);
      b.classList.toggle('off', !on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    return;
  }
  const search = document.getElementById('liftSearch') as HTMLInputElement;
  search.value = LIFTF.q;
  search.addEventListener('input', () => {
    LIFTF.q = search.value.trim().toLowerCase();
    showLifts();
  });
  [
    ['Autoreg', 'autoreg'],
    ['Grouped', 'grouped'],
    ['Goals', 'goal'],
    ['Stalling', 'stall'],
    ['Focus', 'focus'],
  ].forEach(([label, facet]) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'chip mini off';
    b.textContent = label;
    b.dataset.facet = facet;
    b.setAttribute('aria-pressed', 'false');
    b.addEventListener('click', () => {
      if (LIFTF.facets.has(facet)) LIFTF.facets.delete(facet);
      else LIFTF.facets.add(facet);
      showLifts();
    });
    box.appendChild(b);
  });
}

function musPasses(m: string, vol: any, grouped: Record<string, string[]>): boolean {
  if (!MUSF.size) return true;
  const v = vol[m];
  const status = v ? v.status : 'in_range';
  const prio = SNAP.priority || {};
  const t = prio[m];
  const tier = typeof t === 'string' ? t : t ? t.tier : null;
  for (const f of MUSF) {
    if (f === 'below' && status === 'below_mev') return true;
    if (f === 'above' && status === 'above_mrv') return true;
    if (f === 'priority' && tier === 'priority') return true;
    if (f === 'grouped' && grouped[m]) return true;
  }
  return false;
}

function showMuscles() {
  document.getElementById('viewDash')!.hidden = true;
  document.getElementById('viewSession')!.hidden = true;
  document.getElementById('viewLift')!.hidden = true;
  document.getElementById('viewProgram')!.hidden = true;
  document.getElementById('viewMuscle')!.hidden = true;
  document.getElementById('viewLifts')!.hidden = true;
  const v = document.getElementById('viewMuscles')!;
  v.hidden = false;
  document.title = 'muscles';
  const grid = document.getElementById('musGrid')!;
  grid.innerHTML = '';
  const sub = document.getElementById('musSub2')!;
  const vol = SNAP.volume || null;
  if (!vol) {
    sub.textContent = 'no volume data, sync first';
    return;
  }
  const grouped: Record<string, string[]> = (SNAP.autoreg && SNAP.autoreg.grouped) || {};
  const prio = SNAP.priority || {};
  const tierOf = (m: string) => {
    const t = prio[m];
    return typeof t === 'string' ? t : t ? t.tier : null;
  };
  const bad = (m: string) =>
    vol[m] && (vol[m].status === 'below_mev' || vol[m].status === 'above_mrv');
  const order = GROUPS.slice().sort((a, b) => {
    const ba = bad(a) ? 0 : 1;
    const bb = bad(b) ? 0 : 1;
    if (ba !== bb) return ba - bb;
    const pa = tierOf(a) && tierOf(a) !== 'maintain' ? 0 : 1;
    const pb = tierOf(b) && tierOf(b) !== 'maintain' ? 0 : 1;
    if (pa !== pb) return pa - pb;
    return a < b ? -1 : 1;
  });
  const shown = order.filter(m => musPasses(m, vol, grouped));
  sub.textContent = shown.length + ' muscles';
  const mon = new Date();
  mon.setHours(12, 0, 0, 0);
  mon.setDate(mon.getDate() - ((mon.getDay() + 6) % 7));
  const wlabels = [7, 6, 5, 4, 3, 2, 1, 0].map(k =>
    fmtD(new Date(mon.getTime() - k * 7 * 86400000).toISOString().slice(0, 10))
  );
  const jobs: Array<() => void> = [];
  shown.forEach(m => {
    const entry = vol[m] || { weekly: [], mev: 0, mav: null, mrv: null };
    const card = document.createElement('div');
    card.className = 'card';
    card.style.margin = '0';
    const row = document.createElement('div');
    row.className = 'listrow';
    card.appendChild(row);
    const info = document.createElement('div');
    info.className = 'listinfo';
    row.appendChild(info);
    const chartbox = document.createElement('div');
    chartbox.className = 'listchart';
    row.appendChild(chartbox);
    const h = document.createElement('div');
    h.className = 'minititle';
    const al = document.createElement('a');
    al.href = '#/m/' + encodeURIComponent(m);
    al.textContent = m;
    h.appendChild(al);
    const marks: Array<[string, string]> = [];
    if (vol[m]) {
      if (entry.status === 'below_mev') marks.push(['below MEV', 'bad']);
      else if (entry.status === 'above_mrv') marks.push(['above MRV', 'bad']);
      else marks.push(['in range', '']);
    }
    const tier = tierOf(m);
    if (tier && tier !== 'maintain') marks.push([tier, tier === 'priority' ? 'plan' : '']);
    if (grouped[m]) marks.push(['grouped fatigue: ' + grouped[m].join(', '), 'bad']);
    if (marks.length) {
      const wrap = document.createElement('span');
      wrap.className = 'ministat';
      marks.forEach(x => {
        const s = document.createElement('span');
        s.className = ('minisub ' + x[1]).trim();
        s.textContent = x[0];
        wrap.appendChild(s);
      });
      h.appendChild(wrap);
    }
    info.appendChild(h);
    const cv = document.createElement('canvas');
    cv.style.height = '120px';
    chartbox.appendChild(cv);
    const data = musclePageData(D!.W, D!.S, m);
    const lifts = data.lifts || [];
    lifts.slice(0, 3).forEach(l => {
      const row = document.createElement('div');
      row.className = 'cap';
      const a = document.createElement('a');
      a.href = '#/l/' + encodeURIComponent(l.ex);
      a.textContent = l.ex;
      row.appendChild(a);
      const meta = document.createElement('span');
      meta.textContent = ' ' + l.sets + ' sets · ' + Math.round(l.share * 100) + '%';
      row.appendChild(meta);
      info.appendChild(row);
    });
    if (lifts.length > 3) {
      const more = document.createElement('div');
      more.className = 'cap';
      const a = document.createElement('a');
      a.href = '#/m/' + encodeURIComponent(m);
      a.textContent = '+' + (lifts.length - 3) + ' more';
      more.appendChild(a);
      info.appendChild(more);
    }
    card.addEventListener('click', ev => {
      if ((ev.target as HTMLElement).tagName !== 'A')
        location.hash = '#/m/' + encodeURIComponent(m);
    });
    grid.appendChild(card);
    jobs.push(() =>
      muscleChart(
        cv,
        wlabels,
        entry.weekly || [],
        {
          mev: entry.mev !== undefined ? entry.mev : 0,
          mav: entry.mav || null,
          mrv: entry.mrv !== undefined ? entry.mrv : null,
        },
        MC[m] || '#888'
      )
    );
  });
  drawMusFilters();
  if (grid.clientWidth > 0) jobs.forEach(run => run());
  window.scrollTo(0, 0);
}

function drawMusFilters() {
  const box = document.getElementById('musFacets')!;
  if (box.childElementCount) {
    box.querySelectorAll('button[data-facet]').forEach(b => {
      const f = (b as HTMLButtonElement).dataset.facet || '';
      const on = MUSF.has(f);
      b.classList.toggle('off', !on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    return;
  }
  [
    ['Below MEV', 'below'],
    ['Above MRV', 'above'],
    ['Priority', 'priority'],
    ['Grouped', 'grouped'],
  ].forEach(([label, facet]) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'chip mini off';
    b.textContent = label;
    b.dataset.facet = facet;
    b.setAttribute('aria-pressed', 'false');
    b.addEventListener('click', () => {
      if (MUSF.has(facet)) MUSF.delete(facet);
      else MUSF.add(facet);
      showMuscles();
    });
    box.appendChild(b);
  });
}

function topSetOn(
  S: any[],
  wdate: Record<number, string>,
  ex: string,
  date: string
): { w: number; r: number } | null {
  const day = S.filter(
    s => s.exercise === ex && (wdate[s.workout_id] || (s.created || '').slice(0, 10)) === date
  );
  if (!day.length) return null;
  const best = day.slice().sort((a, b) => e1rm(b.weight, b.reps) - e1rm(a.weight, a.reps))[0];
  return { w: best.weight, r: best.reps };
}

function attachGoalHover(
  cv: HTMLCanvasElement,
  acts: Array<{ date: string; ev: number }>,
  cps: number[],
  col: string,
  tops: Record<string, { w: number; r: number }>
) {
  const goalShow = (cx: number, cy: number) => {
    if (!vis(cv)) {
      hideTip();
      return;
    }
    const r = cv.getBoundingClientRect();
    const bi = goalHit(cv, acts, cps, cx - r.left);
    if (bi < 0) {
      hideTip();
      goalChart(cv, acts, cps, col);
      return;
    }
    goalChart(cv, acts, cps, col, bi);
    if (bi < acts.length) {
      const a = acts[bi];
      const top = tops[a.date];
      const logged = top
        ? 'logged ' + top.w + ' x ' + top.r + ' (e1RM ' + fmtV(a.ev) + ')'
        : 'e1RM ' + fmtV(a.ev);
      showTip(
        fmtD(a.date),
        [
          [col, logged],
          [null, 'plan ' + fmtV(cps[bi])],
        ],
        cx,
        cy
      );
    } else {
      showTip('session ' + (bi + 1) + ' (plan)', [[col, 'target e1RM ' + fmtV(cps[bi])]], cx, cy);
    }
  };
  bindHover(cv, goalShow);
  cv.addEventListener('mouseleave', () => {
    hideTip();
    if (vis(cv)) goalChart(cv, acts, cps, col);
  });
}

function renderForward(snap: any, W: any[], S: any[]) {
  const grid = document.getElementById('goalGrid')!;
  grid.innerHTML = '';
  const goals: any[] = snap.goals || [];
  const empty = document.getElementById('goalEmpty')!;
  empty.hidden = goals.length > 0;
  // Paint after every card is appended: a canvas painted while its grid
  // column is still settling keeps a stretched bitmap (ovals, not circles).
  const jobs: Array<() => void> = [];
  const wdate: Record<number, string> = {};
  for (const w of W) wdate[w.id] = w.date;
  goals.forEach(g => {
    const card = document.createElement('div');
    card.className = 'goalcard card future';
    card.style.margin = '0';
    const h = document.createElement('h3');
    const al = document.createElement('a');
    al.href = '#/l/' + encodeURIComponent(g.exercise);
    al.textContent = g.exercise;
    h.appendChild(al);
    card.appendChild(h);
    const cv = document.createElement('canvas');
    card.appendChild(cv);
    const meta = document.createElement('div');
    meta.className = 'goalmeta';
    const acts = (g.actuals || []).map((a: any) => ({ date: a.date, ev: a.e1rm }));
    const pct = goalPercent({
      target_e1rm: g.target_e1rm,
      checkpoints: g.checkpoints || [],
      actuals: acts,
    });
    const bits = [
      'target e1RM ' + fmtV(g.target_e1rm) + ' by ' + fmtD(g.deadline),
      g.next_checkpoint !== null && g.next_checkpoint !== undefined
        ? 'next checkpoint ' + fmtV(g.next_checkpoint)
        : 'trajectory complete',
    ];
    if (pct !== null) bits.push(pct + '% there' + (g.on_track === false ? ', off track' : ''));
    if (g.on_track === false) bits.push('OFF TRACK');
    if (g.slippage) bits.push('slippage: deadline needs room');
    meta.textContent = bits.join(' | ');
    card.appendChild(meta);
    grid.appendChild(card);
    const cps = g.checkpoints || [];
    const col = liftColor(g.exercise);
    jobs.push(() => goalChart(cv, acts, cps, col));
    const tops: Record<string, { w: number; r: number }> = {};
    acts.forEach((a: { date: string }) => {
      const top = topSetOn(S, wdate, g.exercise, a.date);
      if (top) tops[a.date] = top;
    });
    attachGoalHover(cv, acts, cps, col, tops);
  });
  jobs.forEach(run => run());
  const tbl = document.getElementById('progTable') as HTMLTableElement;
  while (tbl.rows.length > 1) tbl.deleteRow(1);
  const prog = snap.progression || {};
  Object.keys(prog)
    .sort()
    .forEach(ex => {
      const p = prog[ex];
      const tr = document.createElement('tr');
      const a = document.createElement('td');
      const al = document.createElement('a');
      al.href = '#/l/' + encodeURIComponent(ex);
      al.textContent = ex;
      a.appendChild(al);
      const b2 = document.createElement('td');
      b2.textContent = p.verdict;
      b2.style.color =
        p.verdict === 'hit' ? '#7fd67f' : p.verdict === 'miss' ? '#f09090' : '#b0aca2';
      b2.style.fontWeight = '600';
      const c2 = document.createElement('td');
      c2.textContent = p.next;
      const d2 = document.createElement('td');
      const arrow = p.direction === 'up' ? '↗' : p.direction === 'down' ? '↘' : '→';
      d2.textContent = arrow;
      d2.title = p.direction;
      d2.style.color =
        p.direction === 'up' ? '#7fd67f' : p.direction === 'down' ? '#f09090' : '#8a8478';
      d2.style.fontWeight = '600';
      tr.appendChild(a);
      tr.appendChild(b2);
      tr.appendChild(c2);
      tr.appendChild(d2);
      tbl.appendChild(tr);
    });
  if (!Object.keys(prog).length) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.setAttribute('colspan', '4');
    td.textContent = 'no progression written yet, set at session end in chat';
    tr.appendChild(td);
    tbl.appendChild(tr);
  }
}

window.addEventListener('hashchange', route);
main();
