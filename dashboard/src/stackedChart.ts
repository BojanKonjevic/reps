import { fit, putText, TC, GC, MC, GROUPS } from "./charts";
import { fmtTick } from "./utils";
import { niceTicks } from "./utils";

export function stacked(cv: HTMLCanvasElement, labels: string[], weeks: Array<Record<string, number>>) {
  const { g, W, H } = fit(cv); const P = 46; g.clearRect(0, 0, W, H);
  let mx = 1; weeks.forEach(w => { const t = GROUPS.reduce((a, k) => a + w[k], 0); if (t > mx) mx = t; });
  const bw = (W - P - 8) / Math.max(1, weeks.length); const area = H - P - 42;
  const t = niceTicks(0, mx, 3); mx = t.hi; g.font = "600 12px sans-serif";
  const nt = Math.round((t.hi - t.lo) / t.step); for (let i = 0; i <= nt; i += 1) { const v = parseFloat((t.lo + i * t.step).toPrecision(12)); const y = H - P - area * (i / nt); g.strokeStyle = GC; g.lineWidth = 1; g.beginPath(); g.moveTo(P, y); g.lineTo(W - 8, y); g.stroke(); if (i % 2 === 0 || i === nt) { g.fillStyle = TC; putText(g, W, fmtTick(v, t.step), 4, y + 4, "left"); } }
  weeks.forEach((w, i) => { let y0 = H - P; GROUPS.forEach(gr => { const h = area * (w[gr] / mx); g.fillStyle = MC[gr]; g.fillRect(P + i * bw + 3, y0 - h, bw - 6, h); y0 -= h; }); const total = GROUPS.reduce((a, k) => a + w[k], 0); const top = H - P - area * (total / mx); g.fillStyle = TC; putText(g, W, String(total), P + i * bw + bw / 2, top - 10, "center"); putText(g, W, labels[i], P + i * bw + bw / 2, H - 8, "center"); });
}