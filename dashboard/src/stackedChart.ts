import { max } from 'd3-array';
import { fit, putText, TC, GC, MC, GROUPS } from './charts';
import { linearScale } from './lib/scales';
import { fmtTick } from './utils';
import { niceTicks } from './utils';

export interface StackedHit {
  wi: number;
  g: string;
}

interface Layout {
  W: number;
  H: number;
  P: number;
  area: number;
  mx: number;
  bw: number;
}

function layout(W: number, H: number, weeks: Array<Record<string, number>>): Layout {
  const P = 46;
  const totals = weeks.map(w => GROUPS.reduce((a, k) => a + w[k], 0));
  const mx = niceTicks(0, Math.max(1, max(totals) ?? 1), 3).hi;
  return { W, H, P, area: H - P - 42, mx, bw: (W - P - 8) / Math.max(1, weeks.length) };
}

export function yOfWeek(L: Layout, v: number): number {
  return linearScale([0, L.mx], [L.H - L.P, L.H - L.P - L.area])(v);
}

function segRect(
  L: Layout,
  weeks: Array<Record<string, number>>,
  wi: number,
  g: string
): { x: number; y: number; w: number; h: number } {
  let acc = 0;
  for (const gr of GROUPS) {
    acc += weeks[wi][gr];
    if (gr === g) {
      const h = (L.area * weeks[wi][gr]) / L.mx;
      return { x: L.P + wi * L.bw + 3, y: yOfWeek(L, acc), w: L.bw - 6, h };
    }
  }
  return { x: 0, y: 0, w: 0, h: 0 };
}

export function stackedHit(
  cv: HTMLCanvasElement,
  labels: string[],
  weeks: Array<Record<string, number>>,
  x: number,
  y: number
): StackedHit | null {
  const r = cv.getBoundingClientRect();
  if (!r.width) return null;
  const L = layout(r.width, r.height, weeks);
  const wi = Math.floor((x - L.P) / L.bw);
  if (wi < 0 || wi >= weeks.length) return null;
  let acc = 0;
  for (const gr of GROUPS) {
    acc += weeks[wi][gr];
    const h = (L.area * weeks[wi][gr]) / L.mx;
    if (y <= yOfWeek(L, acc - weeks[wi][gr]) && y >= yOfWeek(L, acc) && h > 2) return { wi, g: gr };
  }
  return null;
}

export function stacked(
  cv: HTMLCanvasElement,
  labels: string[],
  weeks: Array<Record<string, number>>,
  hover?: StackedHit | null
) {
  const { g, W, H } = fit(cv);
  const P = 46;
  g.clearRect(0, 0, W, H);
  const L = layout(W, H, weeks);
  const bw = L.bw;
  const t = niceTicks(0, L.mx, 3);
  g.font = "600 16px 'IBM Plex Sans', sans-serif";
  const nt = Math.round((t.hi - t.lo) / t.step);
  for (let i = 0; i <= nt; i += 1) {
    const v = parseFloat((t.lo + i * t.step).toPrecision(12));
    const y = yOfWeek(L, v);
    g.strokeStyle = GC;
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
  weeks.forEach((w, i) => {
    GROUPS.forEach(gr => {
      const r = segRect(L, weeks, i, gr);
      g.fillStyle = MC[gr];
      g.fillRect(r.x, r.y, r.w, r.h);
      if (hover && hover.wi === i && hover.g === gr) {
        g.fillStyle = 'rgba(255,255,255,0.35)';
        g.fillRect(r.x, r.y, r.w, r.h);
      }
    });
    const total = GROUPS.reduce((a, k) => a + w[k], 0);
    const top = yOfWeek(L, total);
    g.fillStyle = TC;
    putText(g, W, String(total), P + i * bw + bw / 2, top - 10, 'center');
    const step = Math.ceil(weeks.length / 4);
    if (i === 0 || i === weeks.length - 1 || i % step === 0)
      putText(g, W, labels[i], P + i * bw + bw / 2, H - 8, 'center');
  });
}
