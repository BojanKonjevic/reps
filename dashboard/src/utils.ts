export function e1rm(w: number, r: number): number {
  if (r === 1) return w;
  return w * (1 + r / 30);
}

export function fmtV(v: number): string {
  return v >= 100 ? String(Math.round(v)) : v.toFixed(1);
}

export function fmtD(dstr: string): string {
  const M = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return M[parseInt(dstr.slice(5, 7), 10) - 1] + ' ' + parseInt(dstr.slice(8, 10), 10);
}

export function fmtTick(v: number, step: number): string {
  const dec = step >= 1 ? 0 : Math.min(2, -Math.floor(Math.log10(step) + 1e-9));
  return v.toFixed(dec);
}

export function timeRolling(
  rows: Array<{ date: string; kg: number }>,
  spanDays: number
): Array<number | null> {
  // Trailing mean over the previous spanDays per point. Points with no
  // history inside the window read null so the overlay starts honestly.
  const t = (d: string) => new Date(d + 'T12:00:00').getTime();
  return rows.map((r, i) => {
    const from = t(r.date) - spanDays * 86400000;
    const win = rows.slice(0, i + 1).filter(q => t(q.date) >= from);
    if (!win.length) return null;
    return win.reduce((a, q) => a + q.kg, 0) / win.length;
  });
}

export function isDate(s: string): boolean {
  if (!s || s.length !== 10 || s.charAt(4) !== '-' || s.charAt(7) !== '-') return false;
  for (let i = 0; i < 10; i += 1) {
    if (i === 4 || i === 7) continue;
    const c = s.charAt(i);
    if (c < '0' || c > '9') return false;
  }
  return true;
}

export interface Ticks {
  lo: number;
  hi: number;
  step: number;
}

export function niceTicks(mn: number, mx: number, count: number): Ticks {
  let span = mx - mn;
  if (!(span > 0)) span = Math.abs(mx) || 1;
  const raw = span / count;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const cands = [1, 2, 2.5, 5, 10];
  let step = 10 * mag;
  for (let i = 0; i < cands.length; i += 1) {
    if (raw / (cands[i] * mag) <= count) {
      step = cands[i] * mag;
      break;
    }
  }
  step = parseFloat(step.toPrecision(12));
  const lo = parseFloat((Math.floor(mn / step) * step).toPrecision(12));
  const hi = parseFloat((Math.ceil(mx / step) * step).toPrecision(12));
  return { lo, hi: hi <= lo ? lo + step : hi, step };
}
