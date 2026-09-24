// SSOT owner: muscle-volume chart geometry. Consumers: MuscleVolumeChart via plot() -> HitMap.

import { max } from 'd3-array';
import { fit, putText, drawHoverLine } from './charts';
import { linearScale } from './lib/scales';
import { niceTicks } from './lib/format';
import { theme } from './lib/theme';
import {
  layoutOf as baseLayout,
  emptyHit,
  firstNonZero,
  labelIndices,
  type ChartLayout,
  type HitMap,
} from './lib/chartLayout';

export interface MuscleBands {
  mev: number;
  mav: number[] | null;
  mrv: number | null;
}

export interface MuscleModel {
  labels: string[];
  counts: number[];
  bands: MuscleBands;
  color: string;
}

export function layoutOf(w: number, h: number): ChartLayout {
  return baseLayout(w, h, 'full');
}

// Vertical geometry: list-page minis (H < 170) use mini-like margins so the
// plot fills the canvas the way TrendMini does; the full-page chart keeps
// roomier margins. Pure, so unit tests can pin the plot height.
export function vertical(H: number): { padL: number; padB: number; top: number; area: number } {
  const compact = H < 170;
  const padL = compact ? 30 : 46;
  const padB = compact ? 24 : 46;
  const top = compact ? 8 : 16;
  return { padL, padB, top, area: H - padB - top };
}

export function plot(cv: HTMLCanvasElement, model: MuscleModel, hover = -1): HitMap {
  const { labels, counts, bands, color } = model;
  const { g, W, H } = fit(cv);
  const L = layoutOf(W, H);
  const V = vertical(H);
  const P = V.padL;
  const hit = emptyHit();
  g.clearRect(0, 0, W, H);
  // Compact mode for list-page minis: fewer ticks, smaller type, sparse
  // x labels, and no per-point value labels that would collide with the
  // MEV/MRV line labels at this height.
  const compact = H < 170;
  g.font = theme.font(compact ? 13 : 16, 600);
  if (!counts.length) {
    g.fillStyle = theme.color('ink-dim');
    putText(g, W, 'no sets logged for this muscle yet', P, H / 2, 'left');
    return hit;
  }
  let mx = max(counts.concat([bands.mev, bands.mrv || 0, bands.mav ? bands.mav[1] : 0, 1])) ?? 1;
  const t = niceTicks(0, mx, compact ? 2 : 3);
  mx = t.hi;
  const n = counts.length;
  const found = firstNonZero(counts);
  const start = found === -1 ? Math.max(0, n - 1) : found;
  const nv = n - start;
  const bw = (W - P - L.padR) / Math.max(1, nv);
  const py = linearScale([0, mx], [H - V.padB, V.top]);
  const nt = Math.round((t.hi - t.lo) / t.step);
  for (let i = 0; i <= nt; i += 1) {
    const v = parseFloat((t.lo + i * t.step).toPrecision(12));
    const y = py(v);
    g.strokeStyle = theme.color('line');
    g.lineWidth = 1;
    g.beginPath();
    g.moveTo(P, y);
    g.lineTo(W - L.padR, y);
    g.stroke();
    if (i % 2 === 0 || i === nt) {
      g.fillStyle = theme.color('ink-dim');
      putText(g, W, String(v), 4, y + 4, 'left');
    }
  }
  if (bands.mav) {
    g.fillStyle = theme.color('overlay-tick');
    const yHi = py(bands.mav[1]);
    const yLo = py(bands.mav[0]);
    g.fillRect(P, yHi, W - P - L.padR, yLo - yHi);
  }
  const line = (v: number, style: string, dash: number[]) => {
    g.save();
    g.strokeStyle = style;
    g.setLineDash(dash);
    g.lineWidth = 1.5;
    g.beginPath();
    g.moveTo(P, py(v));
    g.lineTo(W - L.padR, py(v));
    g.stroke();
    g.restore();
    g.fillStyle = style;
    putText(g, W, String(v), W - L.padR, py(v) - 6, 'right');
  };
  line(bands.mev, theme.color('warn'), [6, 4]);
  if (bands.mrv !== null && bands.mrv !== undefined) line(bands.mrv, theme.color('bad'), [6, 4]);
  const pxi = (i: number) => P + (i - start) * bw + bw / 2;
  g.strokeStyle = color;
  g.lineWidth = 2.5;
  g.lineJoin = 'round';
  g.beginPath();
  let begun = false;
  counts.forEach((c, i) => {
    if (i < start) return;
    if (!begun) {
      g.moveTo(pxi(i), py(c));
      begun = true;
    } else g.lineTo(pxi(i), py(c));
  });
  g.stroke();
  counts.forEach((c, i) => {
    if (i < start) return;
    g.fillStyle = color;
    g.beginPath();
    g.arc(pxi(i), py(c), hover === i ? 5 : 2.5, 0, 7);
    g.fill();
    hit.points.push({ x: pxi(i), y: py(c), index: i });
  });
  hit.bars = counts
    .map((c, i) => ({
      x: P + (i - start) * bw,
      y: 0,
      w: bw,
      h: H,
      index: i,
    }))
    .filter(b => b.index >= start);
  const li = counts.length - 1;
  if (li >= 0 && !compact) {
    g.fillStyle = color;
    putText(g, W, String(counts[li]), pxi(li) + 8, py(counts[li]) - 10, 'left');
  }
  g.fillStyle = theme.color('ink-dim');
  const showLabel = compact
    ? new Set([start, n - 1])
    : new Set(labelIndices(nv).map(k => k + start));
  counts.forEach((c, i) => {
    if (i < start) return;
    if (showLabel.has(i)) putText(g, W, labels[i], P + (i - start) * bw + bw / 2, H - 8, 'center');
  });
  if (hover >= start && hover < n) {
    drawHoverLine(g, H - V.padB + P, P, P + (hover - start) * bw + bw / 2);
  }
  return hit;
}
