// SSOT owner: clock reads for highlight-only use. Consumers: calendar/today highlight.
// Classification never reads the viewer clock: relative values come from snapshot.as_of.

export function viewToday(): string {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return d.getFullYear() + '-' + m + '-' + day;
}
