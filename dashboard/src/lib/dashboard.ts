// SSOT owner: view selection over snapshot v2. Consumers: pages.
// Pure selection and formatting of emitted facts. No thresholds, no buckets,
// no domain math: classification happened in Python. Relative values read
// snapshot.as_of, never the viewer clock (clock.ts is highlight-only).

import type { Snapshot } from '../generated/snapshot';
import { fmtD } from './format';

export interface NowSeg {
  t: string;
  b: boolean;
}

export function subLine(snap: Snapshot): string {
  const sessions = snap.sessions.filter(s => s.status !== 'rest');
  if (sessions.length) return sessions.length + (sessions.length === 1 ? ' session' : ' sessions');
  if (snap.sessions.length) return 'no sessions yet, ' + snap.sessions.length + ' rest days logged';
  return 'no sync yet, log your first session';
}

export function statusLines(snap: Snapshot): NowSeg[][] {
  const out: NowSeg[][] = [];
  const line = (...segs: Array<[string, boolean]>) => out.push(segs.map(([t, b]) => ({ t, b })));
  if (snap.status.open_today) line(['Workout open today.', true]);
  else if (snap.status.rest_today) line(['Rest day today.', false]);
  if (snap.status.on_break && snap.status.break_days !== null)
    line(
      ['Break:', true],
      [' ' + snap.status.break_days + 'd since last session, no PR attempts.', false]
    );
  for (const d of snap.deload) line(['Deloading', true], [' ' + d.subject + '.', false]);
  for (const m of snap.muscles) {
    if (m.tier !== 'maintain')
      line(['Focus:', true], [' ' + m.muscle + ' (' + m.tier + ').', false]);
  }
  snap.flags.slice(0, 3).forEach(f => {
    line(['Watch:', true], [' ' + f.subject + ', ' + f.reason, false]);
  });
  if (snap.flags.length > 3) line(['+' + (snap.flags.length - 3) + ' more flags in chat.', false]);
  return out;
}

export function rankLifts(snap: Snapshot): string[] {
  return snap.lifts
    .slice()
    .sort((a, b) => a.rank_default - b.rank_default)
    .map(l => l.exercise);
}

export function slotOfDate(snap: Snapshot): Record<string, string> {
  const out: Record<string, string> = {};
  for (const s of snap.sessions) {
    if (s.slot_label) out[s.date] = s.slot_label;
  }
  return out;
}

export function prDatesOf(snap: Snapshot): Record<string, Record<string, boolean>> {
  const m: Record<string, Record<string, boolean>> = {};
  for (const l of snap.lifts) {
    for (const s of l.sessions) {
      if (s.is_pr) (m[l.exercise] = m[l.exercise] || {})[s.date] = true;
    }
  }
  return m;
}

export interface PrRow {
  lift: string;
  detail: string;
  date: string;
}

export function bestSetRows(snap: Snapshot): PrRow[] {
  return snap.lifts
    .slice()
    .sort((a, b) => (a.exercise < b.exercise ? -1 : 1))
    .filter(l => l.best)
    .map(l => ({
      lift: l.exercise,
      detail: l.best!.weight + ' x ' + l.best!.reps + ' (' + l.best!.e1rm.toFixed(1) + ' e1RM)',
      date: fmtD(l.best!.date),
    }));
}

export interface AdherenceWeekView {
  week_start: string;
  trained: number;
  expected: number;
}

export function adherenceWeeksView(snap: Snapshot): AdherenceWeekView[] {
  return (snap.adherence?.weeks || []).slice(-8);
}

export function liftNames(snap: Snapshot): string[] {
  return snap.lifts.map(l => l.exercise).sort();
}
