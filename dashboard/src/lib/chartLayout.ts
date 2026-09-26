// SSOT owner: chart layout presets and hit-map contract. Consumers: every chart
// module (layoutOf) and every component (hover via the returned HitMap, never
// by recomputing padding).

export interface ChartLayout {
  w: number;
  h: number;
  padL: number;
  padR: number;
  padT: number;
  padB: number;
  plotW: number;
  plotH: number;
}

export interface HitPoint {
  x: number;
  y: number;
  index: number;
}

export interface HitBar {
  x: number;
  y: number;
  w: number;
  h: number;
  index: number;
  tag?: string;
}

export interface HitSlice {
  index: number;
}

export interface HitMark {
  x: number;
  date: string;
}

export interface HitMap {
  points: HitPoint[];
  bars: HitBar[];
  slices: HitSlice[];
  marks: HitMark[];
}

export function emptyHit(): HitMap {
  return { points: [], bars: [], slices: [], marks: [] };
}

export type LayoutPreset = 'full' | 'mini' | 'goal';

const PRESETS: Record<LayoutPreset, { padL: number; padR: number; padT: number; padB: number }> = {
  full: { padL: 46, padR: 8, padT: 14, padB: 30 },
  mini: { padL: 30, padR: 6, padT: 10, padB: 22 },
  goal: { padL: 40, padR: 10, padT: 12, padB: 26 },
};

export function layoutOf(w: number, h: number, preset: LayoutPreset = 'full'): ChartLayout {
  const p = PRESETS[preset];
  return {
    w,
    h,
    padL: p.padL,
    padR: p.padR,
    padT: p.padT,
    padB: p.padB,
    plotW: Math.max(1, w - p.padL - p.padR),
    plotH: Math.max(1, h - p.padT - p.padB),
  };
}

export function nearestPoint(hit: HitMap, x: number, maxDx: number): HitPoint | null {
  let best: HitPoint | null = null;
  for (const p of hit.points) {
    if (Math.abs(p.x - x) <= maxDx && (!best || Math.abs(p.x - x) < Math.abs(best.x - x))) {
      best = p;
    }
  }
  return best;
}

// First index holding a nonzero value, or -1 when all are zero. Charts trim
// leading all-zero weeks so a fresh log starts at the first session;
// interior zeros stay, a skipped week is information.
export function firstNonZero(values: number[]): number {
  for (let i = 0; i < values.length; i += 1) if (values[i] > 0) return i;
  return -1;
}

// Evenly spaced x-axis ticks, at most maxLabels, never forcing a colliding
// last tick (the previous tick already anchors the right edge).
export function labelIndices(n: number, maxLabels = 4): number[] {
  if (n <= 0) return [];
  if (n <= maxLabels) return Array.from({ length: n }, (_, i) => i);
  const step = Math.ceil(n / maxLabels);
  const out: number[] = [];
  for (let i = 0; i < n; i += step) out.push(i);
  const last = n - 1;
  if (out[out.length - 1] !== last && last - out[out.length - 1] >= step) out.push(last);
  return out;
}
