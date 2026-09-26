// GENERATED fixtures drive these tests: every payload below was built by
// tests/scenarios.py through the real backend (scripts/gen.py).
import { describe, it, expect } from 'vitest';
import { snapshotSchema } from '../generated/snapshot';
import blank from '../generated/blank.json';
import minimal from './fixtures/minimal.json';
import rich from './fixtures/rich.json';
import deload from './fixtures/deload.json';
import goalOffTrack from './fixtures/goal_off_track.json';
import brk from './fixtures/break.json';

describe('snapshotSchema (generated)', () => {
  it('parses every generated fixture', () => {
    for (const f of [minimal, rich, deload, goalOffTrack, brk]) {
      const snap = snapshotSchema.parse(f);
      expect(snap.schema_version).toBe(3);
      expect(Array.isArray(snap.sessions)).toBe(true);
    }
  });

  it('parses the generated blank (worker no-sync payload)', () => {
    const snap = snapshotSchema.parse(blank);
    expect(snap.sessions).toEqual([]);
    expect(snap.lifts).toEqual([]);
    expect(snap.next_up.empty).toBeTruthy();
  });

  it('rejects unknown top-level sections (no silent tolerance)', () => {
    expect(() => snapshotSchema.parse({ ...minimal, future_section: {} })).toThrow();
  });

  it('rich fixture carries computed views, not raw tables', () => {
    const snap = snapshotSchema.parse(rich);
    expect((snap as Record<string, unknown>).workouts).toBeUndefined();
    expect((snap as Record<string, unknown>).sets).toBeUndefined();
    const bench = snap.lifts.find(l => l.exercise === 'bench');
    expect(bench?.sessions.length).toBeGreaterThan(0);
    expect(bench?.best).toBeTruthy();
    expect(snap.calendar.length).toBeGreaterThan(0);
    expect(snap.volume_history.week_starts.length).toBeGreaterThan(0);
  });
});
