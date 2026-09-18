import { fit, putText, LC, TC, GC, drawYAxis } from './charts';
import { fmtD, fmtTick } from './utils';
import { niceTicks } from './utils';

export function bwline(
  cv: HTMLCanvasElement,
  rows: Array<{ date: string; kg: number }>,
  hover: number
) {
  const { g, W, H } = fit(cv);
  const P = 46;
  if (!rows.length) {
    g.clearRect(0, 0, W, H);
    g.fillStyle = TC;
    g.font = "600 14px 'IBM Plex Sans', sans-serif";
    g.fillText('no weigh ins yet, say your morning weight in chat', P, H / 2);
    return;
  }
  const vals = rows.map(r => r.kg);
  let mn = Math.min(...vals),
    mx = Math.max(...vals);
  const pad = (mx - mn) * 0.5 || 1;
  mn -= pad;
  mx += pad;
  const t = niceTicks(mn, mx, 3);
  mn = t.lo;
  mx = t.hi;
  g.clearRect(0, 0, W, H);
  g.font = "600 12px 'IBM Plex Sans', sans-serif";
  drawYAxis(g, W, H, P, t);
  const px = (i: number) => P + (W - P - 8) * (rows.length === 1 ? 1 : i / (rows.length - 1));
  const py = (v: number) => H - P - (H - P - 16) * ((v - mn) / (mx - mn));
  g.strokeStyle = LC[0];
  g.lineWidth = 3;
  g.lineJoin = 'round';
  g.beginPath();
  rows.forEach((r, i) => {
    if (i === 0) g.moveTo(px(i), py(r.kg));
    else g.lineTo(px(i), py(r.kg));
  });
  g.stroke();
  g.fillStyle = LC[0];
  g.textAlign = 'center';
  rows.forEach((r, i) => {
    g.beginPath();
    g.arc(px(i), py(r.kg), 5, 0, 7);
    g.fill();
    g.fillStyle = TC;
    if (i === 0) putText(g, W, r.kg.toFixed(1), px(i) + 8, py(r.kg) - 12, 'left');
    else if (i === rows.length - 1)
      putText(g, W, r.kg.toFixed(1), px(i) - 8, py(r.kg) - 12, 'right');
    else putText(g, W, r.kg.toFixed(1), px(i), py(r.kg) - 12, 'center');
    g.fillStyle = LC[0];
  });
  g.fillStyle = TC;
  putText(g, W, fmtD(rows[0].date), P, H - 8, 'left');
  putText(g, W, fmtD(rows[rows.length - 1].date), W - 8, H - 8, 'right');
  if (hover !== undefined && hover >= 0 && hover < rows.length) {
    const x = px(hover);
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
