import { fit, putText, TC, GC, MC, GROUPS } from './charts';
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
  let mx = 1;
  weeks.forEach(w => {
    const t = GROUPS.reduce((a, k) => a + w[k], 0);
    if (t > mx) mx = t;
  });
  mx = niceTicks(0, mx, 3).hi;
  return { W, H, P, area: H - P - 42, mx, bw: (W - P - 8) / Math.max(1, weeks.length) };
}

function segRect(
  L: Layout,
  weeks: Array<Record<string, number>>,
  wi: number,
  g: string
): { x: number; y: number; w: number; h: number } {
  let y0 = L.H - L.P;
  for (const gr of GROUPS) {
    const h = L.area * (weeks[wi][gr] / L.mx);
    if (gr === g) return { x: L.P + wi * L.bw + 3, y: y0 - h, w: L.bw - 6, h };
    y0 -= h;
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
  let y0 = L.H - L.P;
  for (const gr of GROUPS) {
    const h = L.area * (weeks[wi][gr] / L.mx);
    if (y <= y0 && y >= y0 - h && h > 2) return { wi, g: gr };
    y0 -= h;
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
  const area = L.area;
  const mx = L.mx;
  const t = niceTicks(0, mx, 3);
  g.font = "600 12px 'IBM Plex Sans', sans-serif";
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
    const top = H - P - area * (total / mx);
    g.fillStyle = TC;
    putText(g, W, String(total), P + i * bw + bw / 2, top - 10, 'center');
    const step = Math.ceil(weeks.length / 4);
    if (i === 0 || i === weeks.length - 1 || i % step === 0)
      putText(g, W, labels[i], P + i * bw + bw / 2, H - 8, 'center');
  });
}
