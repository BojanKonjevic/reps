export interface PRData {
  prIds: Set<number>;
  prDates: Set<string>;
}

export function computePRs(W: any[], S: any[]): PRData {
  const wdate: Record<number, string> = {};
  for (const w of W) wdate[w.id] = w.date;
  const order = S.slice().sort((a, b) =>
    a.created < b.created ? -1 : a.created > b.created ? 1 : a.id - b.id
  );
  const best: Record<string, number> = {};
  const seen = new Set<string>();
  const prIds = new Set<number>();
  const prDates = new Set<string>();
  order.forEach(s => {
    const ev = s.weight * (1 + s.reps / 30);
    if (!seen.has(s.exercise)) {
      seen.add(s.exercise);
      best[s.exercise] = ev;
      return;
    }
    if (ev > best[s.exercise]) {
      best[s.exercise] = ev;
      prIds.add(s.id);
      prDates.add(wdate[s.workout_id]);
    }
  });
  return { prIds, prDates };
}
