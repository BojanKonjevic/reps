import { max, min } from 'd3-array';
import { fit, putText, TC, GC, drawYAxis } from './charts';
import { linearScale } from './lib/scales';
import { fmtV, fmtD } from './utils';
import { niceTicks } from './utils';

export function mini(
  cv: HTMLCanvasElement,
  days: string[],
  vals: (number | null)[],
  col: string,
  hover?: number
) {
  const { g, W, H } = fit(cv);
  const P = 30;
  g.clearRect(0, 0, W, H);
  g.font = "600 15px 'IBM Plex Sans', sans-serif";
  const pts = [];
  for (let i = 0; i < vals.length; i += 1) if (vals[i] !== null) pts.push(i);
  if (!pts.length) {
    g.fillStyle = TC;
    putText(g, W, 'no data', P, H / 2, 'left');
    return;
  }
  const raw = pts.map(pi => vals[pi]!);
  let mn = min(raw) ?? 0;
  let mx = max(raw) ?? 1;
  if (!(mx > mn)) mx = mn + 1;
  const pad = (mx - mn) * 0.3 || 1;
  mn = Math.max(0, mn - pad);
  mx += pad;
  const t = niceTicks(mn, mx, 2);
  mn = t.lo;
  mx = t.hi;
  const n = vals.length;
  const px = linearScale([0, Math.max(1, n - 1)], [P, W - 6]);
  const xOf = (i: number) => (n <= 1 ? W - 6 : px(i));
  const py = linearScale([mn, mx], [H - 15, 6]);
  drawYAxis(g, W, H, P, t);
  g.strokeStyle = col;
  g.lineWidth = 2.5;
  g.lineJoin = 'round';
  g.beginPath();
  pts.forEach((pi, k) => {
    if (k === 0) g.moveTo(xOf(pi), py(vals[pi]!));
    else g.lineTo(xOf(pi), py(vals[pi]!));
  });
  g.stroke();
  g.fillStyle = col;
  pts.forEach(pi => {
    g.beginPath();
    g.arc(xOf(pi), py(vals[pi]!), 2.5, 0, 7);
    g.fill();
  });
  const li = pts[pts.length - 1];
  g.fillStyle = col;
  if (li > n / 2) putText(g, W, fmtV(vals[li]!), xOf(li) - 8, py(vals[li]!) - 10, 'right');
  else putText(g, W, fmtV(vals[li]!), xOf(li) + 8, py(vals[li]!) - 10, 'left');
  if (hover !== undefined && hover >= 0 && hover < n && vals[hover] !== null) {
    const x = xOf(hover);
    g.strokeStyle = TC;
    g.globalAlpha = 0.45;
    g.lineWidth = 1;
    g.beginPath();
    g.moveTo(x, 6);
    g.lineTo(x, H - 15);
    g.stroke();
    g.globalAlpha = 1;
    g.fillStyle = col;
    g.beginPath();
    g.arc(x, py(vals[hover]!), 5, 0, 7);
    g.fill();
  }
  g.fillStyle = TC;
  if (days.length > 1) {
    putText(g, W, fmtD(days[0]), P, H - 5, 'left');
    putText(g, W, fmtD(days[days.length - 1]), W - 6, H - 5, 'right');
  }
}
