import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchSnapshot } from '../queries/snapshot';

const MINIMAL = {
  exported: '2026-09-17T12:00:00',
  workouts: [{ id: 1, date: '2026-09-10', status: 'done', notes: '' }],
  sets: [],
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('fetchSnapshot', () => {
  it('returns the validated snapshot', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, json: async () => MINIMAL }) as Response)
    );
    const snap = await fetchSnapshot();
    expect(snap.exported).toBe('2026-09-17T12:00:00');
    expect(snap.workouts).toHaveLength(1);
    expect(snap.sets).toEqual([]);
  });

  it('fails explicitly on HTTP errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: false, status: 404 }) as Response)
    );
    await expect(fetchSnapshot()).rejects.toThrow('snapshot fetch failed: 404');
  });

  it('fails explicitly on malformed payloads instead of returning JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, json: async () => ({ workouts: [] }) }) as Response)
    );
    await expect(fetchSnapshot()).rejects.toThrow();
  });
});
