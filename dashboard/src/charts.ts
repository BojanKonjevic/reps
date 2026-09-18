export const LC: string[] = (() => {
  const arr: string[] = [];
  for (let i = 0; i < 24; i += 1) {
    const h = Math.round((i * 137.5) % 360);
    arr.push('hsl(' + h + ',72%,62%)');
  }
  return arr;
})();

export const TC = '#cfc9bc';
export const GC = '#3a3733';
export const STARC = '#e6c400';
export const MC: Record<string, string> = {
  chest: '#ffa726',
  back: '#66bb6a',
  shoulders: '#e6c400',
  biceps: '#42a5f5',
  triceps: '#ef5350',
  quads: '#ab47bc',
  hamstrings: '#26c6da',
  glutes: '#ec407a',
  abs: '#b0bec5',
};
export const GROUPS = [
  'chest',
  'back',
  'shoulders',
  'biceps',
  'triceps',
  'quads',
  'hamstrings',
  'glutes',
  'abs',
];

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
  const s = r / 8;
  g.save();
  g.translate(x, y);
  g.scale(s, s);
  g.fillStyle = color;
  g.strokeStyle = color;
  g.lineWidth = 1.4;
  g.lineCap = 'round';
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

export function drawYAxis(
  g: CanvasRenderingContext2D,
  W: number,
  H: number,
  P: number,
  t: { lo: number; hi: number; step: number },
  color = GC
) {
  const nt = Math.round((t.hi - t.lo) / t.step);
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

export function drawXAxisLabels(
  g: CanvasRenderingContext2D,
  W: number,
  H: number,
  P: number,
  firstDate: string,
  lastDate: string
) {
  g.fillStyle = TC;
  putText(g, W, fmtD(firstDate), P, H - 8, 'left');
  putText(g, W, fmtD(lastDate), W - 8, H - 8, 'right');
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
  g.fillStyle = TC;
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

export function drawHoverLine(g: CanvasRenderingContext2D, H: number, P: number, x: number) {
  g.strokeStyle = TC;
  g.globalAlpha = 0.45;
  g.lineWidth = 1;
  g.beginPath();
  g.moveTo(x, 14);
  g.lineTo(x, H - P);
  g.stroke();
  g.globalAlpha = 1;
}

export function drawPoint(
  g: CanvasRenderingContext2D,
  x: number,
  y: number,
  r: number,
  color: string,
  isPR: boolean
) {
  if (isPR) trophy(g, x, y - 14, r, STARC);
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
  if (isPR) trophy(g, x, y - 14, r + 3, STARC);
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

import { fmtV, fmtD, fmtTick } from './utils';
