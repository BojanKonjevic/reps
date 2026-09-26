import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchHistoryStates } from '../queries/historyStates';
import richStates from './fixtures/rich.states.json';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('fetchHistoryStates', () => {
  it('returns validated states', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, status: 200, json: async () => richStates }) as Response)
    );
    const out = await fetchHistoryStates();
    expect(out?.states.length).toBeGreaterThan(0);
  });

  it('maps a missing payload to unavailable, not an error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: false, status: 404 }) as Response)
    );
    await expect(fetchHistoryStates()).resolves.toBeNull();
  });

  it('fails explicitly on HTTP errors and invalid payloads', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: false, status: 500 }) as Response)
    );
    await expect(fetchHistoryStates()).rejects.toThrow('history-states fetch failed: 500');
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () => ({ ok: true, status: 200, json: async () => ({ states: [{}] }) }) as Response
      )
    );
    await expect(fetchHistoryStates()).rejects.toThrow();
  });
});
