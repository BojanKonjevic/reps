import { describe, it, expect } from 'vitest';
import { palettePages, filterPages, sessionSpans } from '../lib/select';
import { dayAvgs } from '../lib/dashboard';
import type { SessionView } from '../generated/snapshot';

function sess(
  date: string,
  status: string,
  duration_min: number | null,
  slot_label: string | null
) {
  return { date, status, duration_min, slot_label } as SessionView;
}

describe('sessionSpans', () => {
  it('keeps done sessions with a span, oldest first', () => {
    const out = sessionSpans([
      sess('2026-09-24', 'done', 84.5, 'U2'),
      sess('2026-09-23', 'done', 77.8, 'L1'),
    ]);
    expect(out).toEqual([
      { date: '2026-09-23', minutes: 77.8, day: 'L1' },
      { date: '2026-09-24', minutes: 84.5, day: 'U2' },
    ]);
  });
  it('drops open, rest, and spanless sessions', () => {
    const out = sessionSpans([
      sess('2026-09-24', 'open', 12.0, 'U2'),
      sess('2026-09-23', 'rest', null, null),
      sess('2026-09-22', 'done', null, 'U1'),
    ]);
    expect(out).toEqual([]);
  });
  it('groups unmatched days under one label', () => {
    const out = sessionSpans([sess('2026-09-24', 'done', 30.0, null)]);
    expect(out).toEqual([{ date: '2026-09-24', minutes: 30.0, day: 'unscheduled' }]);
  });
});

describe('dayAvgs', () => {
  it('averages per day, alphabetical', () => {
    expect(
      dayAvgs([
        { date: '2026-09-24', minutes: 84.5, day: 'U2' },
        { date: '2026-09-22', minutes: 95.1, day: 'U1' },
        { date: '2026-09-23', minutes: 77.8, day: 'L1' },
        { date: '2026-09-21', minutes: 60.0, day: 'U1' },
      ])
    ).toEqual([
      { day: 'L1', avg: 77.8, n: 1 },
      { day: 'U1', avg: 77.6, n: 2 },
      { day: 'U2', avg: 84.5, n: 1 },
    ]);
  });
});

describe('palettePages', () => {
  it('lists the four top-level pages with working hashes', () => {
    const pages = palettePages();
    expect(pages.map(p => p.label)).toEqual(['Dashboard', 'Movements', 'Muscles', 'Program']);
    expect(pages.map(p => p.href)).toEqual(['#/', '#/lifts', '#/muscles', '#/program']);
  });

  it('filters by label substring, empty matches all', () => {
    const pages = palettePages();
    expect(filterPages(pages, '')).toHaveLength(4);
    expect(filterPages(pages, 'mov').map(p => p.key)).toEqual(['lifts']);
    expect(filterPages(pages, 'MUSCLES').map(p => p.key)).toEqual(['muscles']);
    expect(filterPages(pages, 'zzz')).toEqual([]);
  });
});
