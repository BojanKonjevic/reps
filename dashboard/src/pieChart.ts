import { fit, liftColor } from './charts';

export interface PieSlice {
  label: string;
  frac: number;
  link: string | null;
}

export function pieHit(cv: HTMLCanvasElement, slices: PieSlice[], x: number, y: number): number {
  const r = cv.getBoundingClientRect();
  if (!r.width || !slices.length) return -1;
  const cx = r.width / 2;
  const cy = r.height / 2;
  const R = Math.min(r.width, r.height) / 2 - 8;
  const dx = x - cx;
  const dy = y - cy;
  if (dx * dx + dy * dy > R * R) return -1;
  let a = Math.atan2(dy, dx) + Math.PI / 2;
  if (a < 0) a += Math.PI * 2;
  let acc = 0;
  for (let i = 0; i < slices.length; i += 1) {
    acc += slices[i].frac * Math.PI * 2;
    if (a <= acc) return i;
  }
  return slices.length - 1;
}

export function pieChart(cv: HTMLCanvasElement, slices: PieSlice[], hover?: number) {
  const { g, W, H } = fit(cv);
  g.clearRect(0, 0, W, H);
  if (!slices.length) return;
  const cx = W / 2;
  const cy = H / 2;
  const R = Math.min(W, H) / 2 - 8;
  let a = -Math.PI / 2;
  slices.forEach((s, i) => {
    const a2 = a + s.frac * Math.PI * 2;
    g.fillStyle = liftColor(s.label);
    g.beginPath();
    g.moveTo(cx, cy);
    g.arc(cx, cy, hover === i ? R + 4 : R, a, a2);
    g.closePath();
    g.fill();
    a = a2;
  });
}

export function piePalette(label: string): string {
  return liftColor(label);
}
