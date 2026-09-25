import { describe, it, expect } from 'vitest';
import {
  paletteMovements,
  paletteMuscles,
  palettePages,
  paletteSessions,
  filterPalRows,
  sessionSpans,
} from '../lib/select';
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
});

describe('filterPalRows', () => {
  it('matches labels case-insensitively, empty caps the list', () => {
    const pages = palettePages();
    expect(filterPalRows(pages, '').map(p => p.key)).toEqual([
      'page:dash',
      'page:lifts',
      'page:muscles',
      'page:program',
    ]);
    expect(filterPalRows(pages, 'mov').map(p => p.key)).toEqual(['page:lifts']);
    expect(filterPalRows(pages, 'MUSCLES').map(p => p.key)).toEqual(['page:muscles']);
    expect(filterPalRows(pages, 'zzz')).toEqual([]);
  });

  it('caps rows per section', () => {
    const rows = Array.from({ length: 9 }, (_, i) => ({
      key: 'k' + i,
      label: 'lift ' + i,
      sub: '',
      href: '#/',
      match: 'lift ' + i,
    }));
    expect(filterPalRows(rows, 'lift')).toHaveLength(6);
  });
});

describe('paletteMovements', () => {
  it('shows best e1RM and date, alphabetical', () => {
    const rows = paletteMovements([
      { exercise: 'row', best: { weight: 90, reps: 8, e1rm: 111.2, date: '2026-09-20' } },
      { exercise: 'bench', best: null },
    ] as never);
    expect(rows.map(r => [r.label, r.sub, r.href])).toEqual([
      ['bench', 'no sets yet', '#/l/bench'],
      ['row', 'e1RM 111 · Sep 20', '#/l/row'],
    ]);
  });
});

describe('paletteMuscles', () => {
  it('shows status and this week sets', () => {
    const rows = paletteMuscles([
      { muscle: 'chest', status: 'below_mev', weekly: [0, 8] },
    ] as never);
    expect(rows).toEqual([
      {
        key: 'muscle:chest',
        label: 'chest',
        sub: 'below mev · 8 sets',
        href: '#/m/chest',
        match: 'chest chest',
      },
    ]);
  });
});

describe('paletteSessions', () => {
  it('shows newest first with day, sets and span; rest days included', () => {
    const rows = paletteSessions([
      {
        date: '2026-09-22',
        status: 'done',
        slot_label: 'U1',
        duration_min: 95.1,
        exercises: [{ sets: [1, 2] }, { sets: [1] }],
      },
      { date: '2026-09-21', status: 'rest', slot_label: null, duration_min: null, exercises: [] },
      { date: '2026-09-24', status: 'open', slot_label: null, duration_min: 3.0, exercises: [] },
    ] as never);
    expect(rows).toEqual([
      {
        key: 'session:2026-09-22',
        label: 'Sep 22',
        sub: 'U1 · 3 sets · 95.1 min',
        href: '#/s/2026-09-22',
        match: 'sep 22 2026-09-22 u1',
      },
      {
        key: 'session:2026-09-21',
        label: 'Sep 21',
        sub: 'rest day',
        href: '#/s/2026-09-21',
        match: 'sep 21 2026-09-21 unscheduled',
      },
    ]);
  });

  it('matches typed dates and day names', () => {
    const rows = paletteSessions([
      {
        date: '2026-09-22',
        status: 'done',
        slot_label: 'U1',
        duration_min: 95.1,
        exercises: [{ sets: [1] }],
      },
    ] as never);
    expect(filterPalRows(rows, 'sep 22')).toHaveLength(1);
    expect(filterPalRows(rows, 'u1')).toHaveLength(1);
    expect(filterPalRows(rows, '2026-09-23')).toEqual([]);
  });
});
