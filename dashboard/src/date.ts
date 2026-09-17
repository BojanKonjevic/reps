export function weekKey(dstr: string): string {
  const d = new Date(dstr + "T12:00:00");
  const one = new Date(d.getFullYear(), 0, 1);
  const wk = Math.ceil((((d - one) / 86400000) + one.getDay() + 1) / 7);
  return d.getFullYear() + " W" + wk;
}

export function shift(dstr: string, n: number): string {
  const d = new Date(dstr + "T12:00:00");
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}