// SSOT owner: bodyweight geometry. Consumers: BodyweightChart via plot() -> HitMap.
// Averages and gap flags arrive in the model from the snapshot (Python owns
// the 7-day window and the gap threshold); this module only draws them.

import { max, min } from 'd3-array';
import { fit, putText, LC, drawYAxis } from './charts';
import { linearScale } from './lib/scales';
import { fmtD, niceTicks } from './lib/format';
import { theme } from './lib/theme';
import {
  layoutOf as baseLayout,
  emptyHit,
  labelIndices,
  type ChartLayout,
  type HitMap,
} from './lib/chartLayout';

export interface BwRow {
  date: string;
  kg: number;
  avg7: number | null;
  gap: boolean;
}

export function layoutOf(w: number, h: number): ChartLayout {
  return baseLayout(w, h, 'full');
}

export function plot(cv: HTMLCanvasElement, rows: BwRow[], hover = -1): HitMap {
  const { g, W, H } = fit(cv);
  const L = layoutOf(W, H);
  const P = L.padL;
  const hit = emptyHit();
  if (!rows.length) {
    g.clearRect(0, 0, W, H);
    g.fillStyle = theme.color('ink-dim');
    g.font = theme.font(19, 600);
    g.fillText('no weigh ins yet, say your gym weight in chat', P, H / 2);
    return hit;
  }
  const vals = rows.map(r => r.kg);
  let mn = min(vals) ?? 0,
    mx = max(vals) ?? 1;
  const pad = (mx - mn) * 0.5 || 1;
  mn -= pad;
  mx += pad;
  const t = niceTicks(mn, mx, 3);
  mn = t.lo;
  mx = t.hi;
  g.clearRect(0, 0, W, H);
  g.font = theme.font(16, 600);
  drawYAxis(g, W, H, P, t);
  const px = linearScale([0, Math.max(1, rows.length - 1)], [P, W - L.padR]);
  const xOf = (i: number) => (rows.length === 1 ? W - L.padR : px(i));
  const py = linearScale([mn, mx], [H - P, 16]);
  g.strokeStyle = LC[0];
  g.lineWidth = 3;
  g.lineJoin = 'round';
  const isGap = (i: number) => i > 0 && rows[i].gap;
  g.beginPath();
  rows.forEach((r, i) => {
    if (i === 0 || isGap(i)) g.moveTo(xOf(i), py(r.kg));
    else g.lineTo(xOf(i), py(r.kg));
  });
  g.stroke();
  g.save();
  g.setLineDash([6, 5]);
  g.globalAlpha = 0.7;
  g.beginPath();
  rows.forEach((r, i) => {
    if (i === 0) return;
    if (isGap(i)) {
      g.moveTo(xOf(i - 1), py(rows[i - 1].kg));
      g.lineTo(xOf(i), py(r.kg));
    }
  });
  g.stroke();
  g.restore();
  g.strokeStyle = theme.color('ink-faint');
  g.lineWidth = 1.5;
  g.beginPath();
  rows.forEach((r, i) => {
    const v = r.avg7;
    if (v === null) return;
    if (i === 0 || rows[i - 1].avg7 === null) g.moveTo(xOf(i), py(v));
    else g.lineTo(xOf(i), py(v));
  });
  g.stroke();
  g.fillStyle = LC[0];
  g.textAlign = 'center';
  rows.forEach((r, i) => {
    g.beginPath();
    g.arc(xOf(i), py(r.kg), 5, 0, 7);
    g.fill();
    hit.points.push({ x: xOf(i), y: py(r.kg), index: i });
    g.fillStyle = theme.color('ink-dim');
    if (i === 0) putText(g, W, r.kg.toFixed(1), xOf(i) + 8, py(r.kg) - 12, 'left');
    else if (i === rows.length - 1)
      putText(g, W, r.kg.toFixed(1), xOf(i) - 8, py(r.kg) - 12, 'right');
    else putText(g, W, r.kg.toFixed(1), xOf(i), py(r.kg) - 12, 'center');
    g.fillStyle = LC[0];
  });
  g.fillStyle = theme.color('ink-dim');
  for (const i of labelIndices(rows.length, 5))
    putText(g, W, fmtD(rows[i].date), xOf(i), H - 8, 'center');
  if (hover >= 0 && hover < rows.length) {
    const x = xOf(hover);
    g.strokeStyle = theme.color('ink-dim');
    g.globalAlpha = 0.45;
    g.lineWidth = 1;
    g.beginPath();
    g.moveTo(x, 14);
    g.lineTo(x, H - P);
    g.stroke();
    g.globalAlpha = 1;
    g.fillStyle = LC[0];
    g.beginPath();
    g.arc(x, py(rows[hover].kg), 7, 0, 7);
    g.fill();
  }
  return hit;
}
