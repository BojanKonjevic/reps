import { fit, putText, TC, GC, drawHoverLine } from './charts';
import { niceTicks } from './utils';

export interface MuscleBands {
  mev: number;
  mav: [number, number] | null;
  mrv: number | null;
}

export function muscleHit(cv: HTMLCanvasElement, n: number, x: number): number {
  const r = cv.getBoundingClientRect();
  if (!r.width || !n) return -1;
  const P = 46;
  const bw = (r.width - P - 8) / n;
  const wi = Math.floor((x - P) / bw);
  if (wi < 0 || wi >= n) return -1;
  return wi;
}

export function muscleChart(
  cv: HTMLCanvasElement,
  labels: string[],
  counts: number[],
  bands: MuscleBands,
  color: string,
  hover?: number
) {
  const { g, W, H } = fit(cv);
  const P = 46;
  g.clearRect(0, 0, W, H);
  g.font = "600 16px 'IBM Plex Sans', sans-serif";
  if (!counts.length) {
    g.fillStyle = TC;
    putText(g, W, 'no sets logged for this muscle yet', P, H / 2, 'left');
    return;
  }
  let mx = Math.max(...counts, bands.mev, bands.mrv || 0, bands.mav ? bands.mav[1] : 0, 1);
  const t = niceTicks(0, mx, 3);
  mx = t.hi;
  const n = counts.length;
  const bw = (W - P - 8) / n;
  const area = H - P - 42;
  const py = (v: number) => H - P - area * (v / mx);
  const nt = Math.round((t.hi - t.lo) / t.step);
  for (let i = 0; i <= nt; i += 1) {
    const v = parseFloat((t.lo + i * t.step).toPrecision(12));
    const y = H - P - area * (i / nt);
    g.strokeStyle = GC;
    g.lineWidth = 1;
    g.beginPath();
    g.moveTo(P, y);
    g.lineTo(W - 8, y);
    g.stroke();
    if (i % 2 === 0 || i === nt) {
      g.fillStyle = TC;
      putText(g, W, String(v), 4, y + 4, 'left');
    }
  }
  if (bands.mav) {
    g.fillStyle = 'rgba(255,255,255,0.10)';
    const yHi = py(bands.mav[1]);
    const yLo = py(bands.mav[0]);
    g.fillRect(P, yHi, W - P - 8, yLo - yHi);
  }
  const line = (v: number, style: string, dash: number[]) => {
    g.save();
    g.strokeStyle = style;
    g.setLineDash(dash);
    g.lineWidth = 1.5;
    g.beginPath();
    g.moveTo(P, py(v));
    g.lineTo(W - 8, py(v));
    g.stroke();
    g.restore();
    g.fillStyle = style;
    putText(g, W, String(v), W - 8, py(v) - 6, 'right');
  };
  line(bands.mev, '#e6c400', [6, 4]);
  if (bands.mrv !== null && bands.mrv !== undefined) line(bands.mrv, '#f09090', [6, 4]);
  const pxi = (i: number) => P + i * bw + bw / 2;
  g.strokeStyle = color;
  g.lineWidth = 2.5;
  g.lineJoin = 'round';
  g.beginPath();
  counts.forEach((c, i) => {
    if (i === 0) g.moveTo(pxi(i), py(c));
    else g.lineTo(pxi(i), py(c));
  });
  g.stroke();
  counts.forEach((c, i) => {
    g.fillStyle = color;
    g.beginPath();
    g.arc(pxi(i), py(c), hover === i ? 5 : 2.5, 0, 7);
    g.fill();
  });
  const li = counts.length - 1;
  if (li >= 0) {
    g.fillStyle = color;
    putText(g, W, String(counts[li]), pxi(li) + 8, py(counts[li]) - 10, 'left');
  }
  g.fillStyle = TC;
  const step = Math.ceil(n / 6);
  counts.forEach((c, i) => {
    if (i === 0 || i === n - 1 || i % step === 0)
      putText(g, W, labels[i], P + i * bw + bw / 2, H - 8, 'center');
  });
  if (hover !== undefined && hover >= 0 && hover < n) {
    drawHoverLine(g, H, P, P + hover * bw + bw / 2);
  }
}
