// @vitest-environment node
import { describe, expect, it } from 'vitest';
import worker from '../worker';
import blank from '../generated/blank.json';
import rich from './fixtures/rich.json';

// NOTE: this file intentionally runs in plain node with no DOM globals.
// The worker module must stay DOM free so it can run on the Workers runtime.
// Importing it must not throw: any window/document/localStorage access at
// module scope fails this whole file before assertions even run.

interface R2Stub {
  get(key: string): Promise<Response | null>;
  put(key: string, value: string): Promise<void>;
}

interface TestEnv {
  SNAPSHOTS: R2Stub;
  SYNC_SECRET?: string;
}

type WorkerFetchEnv = Parameters<typeof worker.fetch>[1];

function memR2(): R2Stub {
  const store = new Map<string, string>();
  return {
    async get(key: string) {
      const v = store.get(key);
      if (v === undefined) return null;
      return new Response(v, { headers: { 'content-type': 'application/json' } });
    },
    async put(key: string, value: string) {
      store.set(key, value);
    },
  };
}

function callFetch(req: Request, env: TestEnv) {
  return worker.fetch(req, env as unknown as WorkerFetchEnv);
}

const authed = (r2: R2Stub): TestEnv => ({ SNAPSHOTS: r2, SYNC_SECRET: 'test-secret' });

describe('worker entry (no DOM globals)', () => {
  it('serves the generated BLANK snapshot when bucket empty', async () => {
    const res = await callFetch(new Request('http://localhost/snapshot'), {
      SNAPSHOTS: memR2(),
    });
    expect(res.status).toBe(200);
    const body = (await res.json()) as Record<string, unknown>;
    expect(body.schema_version).toBe(2);
    expect(body.sessions).toEqual([]);
    expect(body).toEqual(blank);
  });

  it('rejects unauthenticated sync', async () => {
    const res = await callFetch(
      new Request('http://localhost/sync', { method: 'PUT', body: '{}' }),
      {
        SNAPSHOTS: memR2(),
      }
    );
    expect(res.status).toBe(401);
  });

  it('rejects wrong-schema sync payloads (resync needed)', async () => {
    const r2 = memR2();
    const put = await callFetch(
      new Request('http://localhost/sync', {
        method: 'PUT',
        body: JSON.stringify({ ...rich, schema_version: 99 }),
        headers: { Authorization: 'Bearer test-secret', 'Content-Type': 'application/json' },
      }),
      authed(r2)
    );
    expect(put.status).toBe(409);
  });

  it('round-trips a generated fixture with data intact', async () => {
    const r2 = memR2();
    const payload = JSON.stringify(rich);
    const put = await callFetch(
      new Request('http://localhost/sync', {
        method: 'PUT',
        body: payload,
        headers: { Authorization: 'Bearer test-secret', 'Content-Type': 'application/json' },
      }),
      authed(r2)
    );
    expect(put.status).toBe(200);
    const get = await callFetch(new Request('http://localhost/snapshot'), authed(r2));
    const body = (await get.json()) as Record<string, unknown>;
    expect(body).toEqual(rich);
  });

  it('404s unknown paths', async () => {
    const res = await callFetch(new Request('http://localhost/nope'), {
      SNAPSHOTS: memR2(),
    });
    expect(res.status).toBe(404);
  });
});
