import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchSnapshot } from '../queries/snapshot';
import rich from './fixtures/rich.json';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('fetchSnapshot', () => {
  it('returns the validated snapshot', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, json: async () => rich }) as Response)
    );
    const snap = await fetchSnapshot();
    expect(snap.schema_version).toBe(3);
    expect(snap.sessions.length).toBeGreaterThan(0);
  });

  it('fails explicitly on HTTP errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: false, status: 404 }) as Response)
    );
    await expect(fetchSnapshot()).rejects.toThrow('snapshot fetch failed: 404');
  });

  it('fails explicitly on schema mismatch (resync needed)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () => ({ ok: true, json: async () => ({ ...rich, schema_version: 99 }) }) as Response
      )
    );
    await expect(fetchSnapshot()).rejects.toThrow('resync needed');
  });
});
