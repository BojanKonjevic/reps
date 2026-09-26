// SSOT owner: formatting (dates, values, ticks). Consumers: pages and components.
// The only place toLocaleDateString-adjacent logic lives; dates are ISO strings
// parsed in exactly one helper (parseDate).

export interface Ticks {
  lo: number;
  hi: number;
  step: number;
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export function parseDate(dstr: string): Date {
  // Parse-only; never reads the viewer clock (see lib/clock.ts for now-reads).
  return new Date(dstr + 'T12:00:00');
}

export function fmtV(v: number): string {
  return v >= 100 ? String(Math.round(v)) : v.toFixed(1);
}

export function fmtD(dstr: string): string {
  if (!dstr) return '';
  return MONTHS[parseInt(dstr.slice(5, 7), 10) - 1] + ' ' + parseInt(dstr.slice(8, 10), 10);
}

export function fmtTick(v: number, step: number): string {
  const dec = step >= 1 ? 0 : Math.min(2, -Math.floor(Math.log10(step) + 1e-9));
  return v.toFixed(dec);
}

export function fmtHoverDate(dstr: string): string {
  return parseDate(dstr).toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });
}

export function fmtLong(dstr: string): string {
  return parseDate(dstr).toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });
}

export function fmtSet(w: number, r: number): string {
  return (Number.isInteger(w) ? String(w) : String(w)) + ' x ' + r;
}

export function fmtMin(v: number): string {
  const n = Number.isInteger(v) ? String(v) : v.toFixed(1);
  return n + ' min';
}

export function fmtE1RM(ev: number): string {
  return 'e1RM ' + ev.toFixed(1);
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

export function daysBetween(a: string, b: string): number {
  return Math.round((parseDate(b).getTime() - parseDate(a).getTime()) / 86400000);
}

const MONTH_LONG = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

export function isoParts(iso: string): [number, number, number] {
  return [
    parseInt(iso.slice(0, 4), 10),
    parseInt(iso.slice(5, 7), 10),
    parseInt(iso.slice(8, 10), 10),
  ];
}

export function monthLabel(year: number, month: number): string {
  return MONTH_LONG[month - 1] + ' ' + year;
}

export function shiftMonth(year: number, month: number, delta: number): [number, number] {
  const total = (year * 12 + (month - 1) + delta) % 12;
  const wrapped = total < 0 ? total + 12 : total;
  return [year + Math.floor((month - 1 + delta) / 12), wrapped + 1];
}

// Month grid, Monday first: weeks of ISO dates, null for leading/trailing
// blanks. Calendar presentation only; domain dates stay ISO strings.
export function monthGrid(year: number, month: number): Array<Array<string | null>> {
  const dim = new Date(year, month, 0).getDate();
  let lead = new Date(year, month - 1, 1).getDay() - 1;
  if (lead < 0) lead = 6;
  const pad = (n: number) => String(n).padStart(2, '0');
  const cells: Array<string | null> = [];
  for (let i = 0; i < lead; i += 1) cells.push(null);
  for (let d = 1; d <= dim; d += 1) cells.push(year + '-' + pad(month) + '-' + pad(d));
  while (cells.length % 7 !== 0) cells.push(null);
  const weeks: Array<Array<string | null>> = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  return weeks;
}
