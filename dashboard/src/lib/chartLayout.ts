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

export interface HitMap {
  points: HitPoint[];
  bars: HitBar[];
  slices: HitSlice[];
}

export function emptyHit(): HitMap {
  return { points: [], bars: [], slices: [] };
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
