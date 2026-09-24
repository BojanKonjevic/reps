// SSOT owner: pie geometry. Consumers: MusclePie via plot() -> HitMap.

import { fit, liftColor } from './charts';
import { layoutOf as baseLayout, emptyHit, type ChartLayout, type HitMap } from './lib/chartLayout';

export interface PieSlice {
  label: string;
  frac: number;
  link: string | null;
}

export function layoutOf(w: number, h: number): ChartLayout {
  return baseLayout(w, h, 'full');
}

export function pieLayout(w: number, h: number): { cx: number; cy: number; R: number } {
  const cx = w / 2;
  const cy = h / 2;
  const R = Math.min(w, h) / 2 - 8;
  return { cx, cy, R };
}

export function plot(cv: HTMLCanvasElement, slices: PieSlice[], hover = -1): HitMap {
  const { g, W, H } = fit(cv);
  const hit = emptyHit();
  g.clearRect(0, 0, W, H);
  if (!slices.length) return hit;
  const { cx, cy, R } = pieLayout(W, H);
  let a = -Math.PI / 2;
  slices.forEach((s, i) => {
    const a2 = a + s.frac * Math.PI * 2;
    g.fillStyle = liftColor(s.label);
    g.beginPath();
    g.moveTo(cx, cy);
    g.arc(cx, cy, hover === i ? R + 4 : R, a, a2);
    g.closePath();
    g.fill();
    hit.slices.push({ index: i });
    a = a2;
  });
  return hit;
}

export function pieHitFromPoint(
  w: number,
  h: number,
  slices: PieSlice[],
  x: number,
  y: number
): number {
  if (!w || !slices.length) return -1;
  const { cx, cy, R } = pieLayout(w, h);
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

export function piePalette(label: string): string {
  return liftColor(label);
}
