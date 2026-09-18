import { fit, putText, TC, GC, trophy, drawYAxis } from './charts';
import { fmtV, fmtD, fmtTick } from './utils';
import { niceTicks } from './utils';

export function mini(
  cv: HTMLCanvasElement,
  days: string[],
  vals: (number | null)[],
  col: string,
  prs: Record<string, boolean>,
  hover: number
) {
  const { g, W, H } = fit(cv);
  const P = 30;
  g.clearRect(0, 0, W, H);
  g.font = "600 11px 'IBM Plex Sans', sans-serif";
  const pts = [];
  for (let i = 0; i < vals.length; i += 1) if (vals[i] !== null) pts.push(i);
  if (!pts.length) {
    g.fillStyle = TC;
    putText(g, W, 'no data', P, H / 2, 'left');
    return;
  }
  let mn = Infinity,
    mx = 0;
  pts.forEach(pi => {
    const v = vals[pi]!;
    if (v < mn) mn = v;
    if (v > mx) mx = v;
  });
  if (!(mx > mn)) mx = mn + 1;
  const pad = (mx - mn) * 0.3 || 1;
  mn = Math.max(0, mn - pad);
  mx += pad;
  const t = niceTicks(mn, mx, 2);
  mn = t.lo;
  mx = t.hi;
  const n = vals.length;
  const px = (i: number) => P + (W - P - 6) * (n <= 1 ? 1 : i / (n - 1));
  const py = (v: number) => H - 15 - (H - 15 - 6) * ((v - mn) / (mx - mn));
  drawYAxis(g, W, H, P, t);
  g.strokeStyle = col;
  g.lineWidth = 2.5;
  g.lineJoin = 'round';
  g.beginPath();
  pts.forEach((pi, k) => {
    if (k === 0) g.moveTo(px(pi), py(vals[pi]!));
    else g.lineTo(px(pi), py(vals[pi]!));
  });
  g.stroke();
  g.fillStyle = col;
  pts.forEach(pi => {
    g.beginPath();
    g.arc(px(pi), py(vals[pi]!), 2.5, 0, 7);
    g.fill();
  });
  pts.forEach(pi => {
    if (prs[days[pi]]) trophy(g, px(pi), py(vals[pi]!) - 9, 5, '#e6c400');
  });
  const li = pts[pts.length - 1];
  g.fillStyle = col;
  if (li > n / 2) putText(g, W, fmtV(vals[li]!), px(li) - 8, py(vals[li]!) - 10, 'right');
  else putText(g, W, fmtV(vals[li]!), px(li) + 8, py(vals[li]!) - 10, 'left');
  if (hover !== undefined && hover >= 0 && hover < n && vals[hover] !== null) {
    const x = px(hover);
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
    putText(g, W, fmtD(days[0]), P, H - 1, 'left');
    putText(g, W, fmtD(days[days.length - 1]), W - 6, H - 1, 'right');
  }
}
