// SSOT owner: canvas primitives and identity-to-color hashing. Consumers: every chart.
// Muscle colors come from snapshot constants via lib/vocab (never here);
// lift identity maps to color in liftColor only, split-day identity in
// dayColor only (both presentation-only, no domain meaning).

import { fmtV, fmtTick } from './lib/format';
import { icons } from './design/icons';
import { theme } from './lib/theme';

export const LC: string[] = (() => {
  const arr: string[] = [];
  for (let i = 0; i < 24; i += 1) {
    const h = Math.round((i * 137.5) % 360);
    arr.push('hsl(' + h + ',72%,62%)');
  }
  return arr;
})();

export function liftColor(name: string): string {
  // Stable color per lift: the same exercise renders identically in the
  // trend grid, goal cards, and lift page instead of by list position.
  let h = 2166136261;
  const key = (name || '').toLowerCase();
  for (let i = 0; i < key.length; i += 1) {
    h ^= key.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return LC[(h >>> 0) % LC.length];
}

// Split-day colors read as families: U-days run warm, L-days cool, numbered
// variants step through distinct hues inside the family so U1 vs U3 (or U1
// vs L1) is obvious without sharing one color. Same 72%/62% as LC so both
// sit naturally on the dark theme. Day names are user data, so this derives
// from the name instead of a token; anything unrecognized falls back to
// liftColor.
const DAY_HUES: Record<string, number[]> = {
  u: [12, 32, 48, 348],
  l: [212, 168],
};

export function dayColor(name: string): string {
  const key = (name || '').trim().toLowerCase();
  if (key === 'rest') return 'hsl(0,0%,50%)';
  let cut = key.length;
  while (cut > 0) {
    const ch = key.charAt(cut - 1);
    if (ch < '0' || ch > '9') break;
    cut -= 1;
  }
  const letters = key.slice(0, cut).trim();
  let alpha = letters.length > 0;
  for (const ch of letters) {
    if (ch < 'a' || ch > 'z') alpha = false;
  }
  if (alpha && DAY_HUES[letters]) {
    const hues = DAY_HUES[letters];
    const n = cut < key.length ? parseInt(key.slice(cut), 10) : 1;
    return 'hsl(' + hues[(Math.max(1, n) - 1) % hues.length] + ',72%,62%)';
  }
  return liftColor(name);
}

export interface ChartContext {
  g: CanvasRenderingContext2D;
  W: number;
  H: number;
}

export function fit(cv: HTMLCanvasElement): ChartContext {
  const dpr = window.devicePixelRatio || 1;
  const w = Math.max(50, cv.clientWidth),
    h = Math.max(50, cv.clientHeight);
  cv.width = Math.round(w * dpr);
  cv.height = Math.round(h * dpr);
  const g = cv.getContext('2d')!;
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { g, W: w, H: h };
}

export function putText(
  g: CanvasRenderingContext2D,
  W: number,
  str: string,
  x: number,
  y: number,
  align: 'left' | 'center' | 'right' = 'left'
) {
  g.textAlign = align;
  const w = g.measureText(str).width;
  if (align === 'center') x = Math.min(Math.max(x, w / 2 + 2), W - w / 2 - 2);
  else if (align === 'right') x = Math.min(x, W - 2);
  else x = Math.min(x, W - w - 2);
  g.fillText(str, Math.max(x, 2), y);
}

export function trophy(
  g: CanvasRenderingContext2D,
  x: number,
  y: number,
  r: number,
  color: string
) {
  // Same path data as <Icon name="trophy">, drawn via Path2D on canvas.
  const s = r / 8;
  g.save();
  g.translate(x - 8 * s, y - 8 * s);
  g.scale(s, s);
  const path = new Path2D(icons.trophy);
  g.strokeStyle = color;
  g.fillStyle = color;
  g.lineWidth = 1.4;
  g.lineCap = 'round';
  g.lineJoin = 'round';
  g.stroke(path);
  g.restore();
}

export function drawYAxis(
  g: CanvasRenderingContext2D,
  W: number,
  H: number,
  P: number,
  t: { lo: number; hi: number; step: number },
  color = theme.color('line')
) {
  const nt = Math.round((t.hi - t.lo) / t.step);
  const TC = theme.color('ink-dim');
  for (let i = 0; i <= nt; i += 1) {
    const v = parseFloat((t.lo + i * t.step).toPrecision(12));
    const y = H - P - ((H - P - 18) * i) / nt;
    g.strokeStyle = color;
    g.lineWidth = 1;
    g.beginPath();
    g.moveTo(P, y);
    g.lineTo(W - 8, y);
    g.stroke();
    if (i % 2 === 0 || i === nt) {
      g.fillStyle = TC;
      putText(g, W, fmtTick(v, t.step), 4, y + 4, 'left');
    }
  }
}

export function drawValueLabels(
  g: CanvasRenderingContext2D,
  W: number,
  P: number,
  py: (v: number) => number,
  firstVal: number,
  lastVal: number,
  lastIsPR: boolean
) {
  g.fillStyle = theme.color('ink-dim');
  putText(g, W, fmtV(firstVal) + ' start', P + 4, py(firstVal) - 12, 'left');
  putText(
    g,
    W,
    fmtV(lastVal) + ' now',
    W - 8,
    lastIsPR ? py(lastVal) + 24 : py(lastVal) - 12,
    'right'
  );
}

export function drawSingleLine(
  g: CanvasRenderingContext2D,
  W: number,
  P: number,
  padR: number,
  y: number,
  label: string,
  span?: number
) {
  // The y-axis for one data point: a single gridline labeled with the value.
  // The floating value label is dropped with it, so the two can never collide.
  // Faint unlabeled parallels give the chart texture without printing
  // values for a range that does not exist yet.
  if (span) {
    g.save();
    g.strokeStyle = theme.color('line');
    g.globalAlpha = 0.45;
    g.lineWidth = 1;
    g.beginPath();
    for (const off of [-span / 4, span / 4]) {
      g.moveTo(P, y + off);
      g.lineTo(W - padR, y + off);
    }
    g.stroke();
    g.restore();
  }
  g.strokeStyle = theme.color('line');
  g.lineWidth = 1;
  g.beginPath();
  g.moveTo(P, y);
  g.lineTo(W - padR, y);
  g.stroke();
  g.fillStyle = theme.color('ink-dim');
  putText(g, W, label, 4, y + 4, 'left');
}

export function drawHoverLine(g: CanvasRenderingContext2D, H: number, P: number, x: number) {
  g.strokeStyle = theme.color('ink-dim');
  g.globalAlpha = 0.45;
  g.lineWidth = 1;
  g.beginPath();
  g.moveTo(x, 14);
  g.lineTo(x, H - P);
  g.stroke();
  g.globalAlpha = 1;
}

// Subordinate history markers: short ticks along the bottom of the plot
// area, one per date carrying a state change. The chart stays primary;
// selection and detail live in the HTML EventStrip beside it. Ticks are
// interactive where the component wires hit.marks (hover preview, tap to
// select); the selected tick draws emphasized but still quiet.
export interface ChartMark {
  date: string;
  titles: string[];
  week?: number;
}

export function drawEventTicks(
  g: CanvasRenderingContext2D,
  xs: number[],
  yBase: number,
  sel: boolean[] = []
) {
  if (!xs.length) return;
  g.save();
  xs.forEach((x, i) => {
    const on = sel[i] === true;
    g.strokeStyle = theme.color(on ? 'warn' : 'ink-faint');
    g.lineWidth = on ? 3 : 2;
    const len = on ? 10 : 7;
    g.beginPath();
    g.moveTo(x, yBase - len);
    g.lineTo(x, yBase);
    g.stroke();
  });
  g.restore();
}

export function nearestMark(
  marks: Array<{ x: number; date: string }>,
  x: number,
  maxDx: number
): { x: number; date: string } | null {
  let best: { x: number; date: string } | null = null;
  for (const m of marks) {
    if (Math.abs(m.x - x) <= maxDx && (!best || Math.abs(m.x - x) < Math.abs(best.x - x))) {
      best = m;
    }
  }
  return best;
}

// Shared mark interaction: resolve the hovered/clicked tick to its date
// plus display titles. Per-chart hover and tooltip bodies stay per chart;
// only the hit lookup is shared.
export function markHit(
  marks: Array<{ x: number; date: string }>,
  titlesByDate: Map<string, ChartMark>,
  x: number,
  maxDx: number
): { date: string; titles: string[] } | null {
  const mk = nearestMark(marks, x, maxDx);
  if (!mk) return null;
  return { date: mk.date, titles: titlesByDate.get(mk.date)?.titles ?? [] };
}

export function drawPoint(
  g: CanvasRenderingContext2D,
  x: number,
  y: number,
  r: number,
  color: string,
  isPR: boolean
) {
  if (isPR) trophy(g, x, y - 14, r, theme.color('warn'));
  else {
    g.fillStyle = color;
    g.beginPath();
    g.arc(x, y, r, 0, 7);
    g.fill();
  }
}

export function drawHoverPoint(
  g: CanvasRenderingContext2D,
  x: number,
  y: number,
  r: number,
  color: string,
  isPR: boolean
) {
  if (isPR) trophy(g, x, y - 14, r + 3, theme.color('warn'));
  else {
    g.fillStyle = color;
    g.beginPath();
    g.arc(x, y, r, 0, 7);
    g.fill();
  }
}

export function drawLine(
  g: CanvasRenderingContext2D,
  pts: Array<{ x: number; y: number }>,
  color: string
) {
  g.strokeStyle = color;
  g.lineWidth = 3;
  g.lineJoin = 'round';
  g.beginPath();
  pts.forEach((p, i) => {
    if (i === 0) g.moveTo(p.x, p.y);
    else g.lineTo(p.x, p.y);
  });
  g.stroke();
}
