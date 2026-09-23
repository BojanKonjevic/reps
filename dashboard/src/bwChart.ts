import { max, min } from 'd3-array';
import { fit, putText, LC, TC, drawYAxis } from './charts';
import { linearScale } from './lib/scales';
import { fmtD } from './utils';
import { niceTicks } from './utils';
import { timeRolling } from './utils';

export function bwline(
  cv: HTMLCanvasElement,
  rows: Array<{ date: string; kg: number }>,
  hover?: number
) {
  const { g, W, H } = fit(cv);
  const P = 46;
  if (!rows.length) {
    g.clearRect(0, 0, W, H);
    g.fillStyle = TC;
    g.font = "600 19px 'IBM Plex Sans', sans-serif";
    g.fillText('no weigh ins yet, say your gym weight in chat', P, H / 2);
    return;
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
  g.font = "600 16px 'IBM Plex Sans', sans-serif";
  drawYAxis(g, W, H, P, t);
  const px = linearScale([0, Math.max(1, rows.length - 1)], [P, W - 8]);
  const xOf = (i: number) => (rows.length === 1 ? W - 8 : px(i));
  const py = linearScale([mn, mx], [H - P, 16]);
  g.strokeStyle = LC[0];
  g.lineWidth = 3;
  g.lineJoin = 'round';
  const gapDays = (a: string, b: string) =>
    Math.round(
      (new Date(b + 'T12:00:00').getTime() - new Date(a + 'T12:00:00').getTime()) / 86400000
    );
  const isGap = (i: number) => i > 0 && gapDays(rows[i - 1].date, rows[i].date) > 14;
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
  const roll = timeRolling(rows, 7);
  g.strokeStyle = '#8a8478';
  g.lineWidth = 1.5;
  g.beginPath();
  roll.forEach((v, i) => {
    if (v === null) return;
    if (i === 0 || roll[i - 1] === null) g.moveTo(xOf(i), py(v));
    else g.lineTo(xOf(i), py(v));
  });
  g.stroke();
  g.fillStyle = LC[0];
  g.textAlign = 'center';
  rows.forEach((r, i) => {
    g.beginPath();
    g.arc(xOf(i), py(r.kg), 5, 0, 7);
    g.fill();
    g.fillStyle = TC;
    if (i === 0) putText(g, W, r.kg.toFixed(1), xOf(i) + 8, py(r.kg) - 12, 'left');
    else if (i === rows.length - 1)
      putText(g, W, r.kg.toFixed(1), xOf(i) - 8, py(r.kg) - 12, 'right');
    else putText(g, W, r.kg.toFixed(1), xOf(i), py(r.kg) - 12, 'center');
    g.fillStyle = LC[0];
  });
  g.fillStyle = TC;
  putText(g, W, fmtD(rows[0].date), P, H - 8, 'left');
  putText(g, W, fmtD(rows[rows.length - 1].date), W - 8, H - 8, 'right');
  if (hover !== undefined && hover >= 0 && hover < rows.length) {
    const x = xOf(hover);
    g.strokeStyle = TC;
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
}
