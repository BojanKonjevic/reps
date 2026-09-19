// @vitest-environment node
import { describe, expect, it } from 'vitest';
import worker from '../worker';

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

interface SnapshotBody {
  workouts: unknown[];
  sets: unknown[];
  bodyweight: unknown[];
  exported?: string;
}

const authed = (r2: R2Stub): TestEnv => ({ SNAPSHOTS: r2, SYNC_SECRET: 'test-secret' });

describe('worker entry (no DOM globals)', () => {
  it('serves BLANK snapshot when bucket empty', async () => {
    const res = await callFetch(new Request('http://localhost/snapshot'), {
      SNAPSHOTS: memR2(),
    });
    expect(res.status).toBe(200);
    const body = (await res.json()) as SnapshotBody;
    expect(body.workouts).toEqual([]);
    expect(body.sets).toEqual([]);
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

  it('round-trips a sync payload with data intact', async () => {
    const r2 = memR2();
    const payload = {
      exported: 'x',
      workouts: [{ id: 1, date: '2026-09-10', status: 'done', notes: 'push' }],
      sets: [
        {
          id: 1,
          workout_id: 1,
          exercise: 'flat barbell bench press',
          weight: 90,
          reps: 5,
          note: '',
          created: '2026-09-10T18:00:00',
          muscles: 'chest',
        },
        {
          id: 2,
          workout_id: 1,
          exercise: 'overhead press',
          weight: 42.5,
          reps: 7,
          note: 'hard set',
          created: '2026-09-10T18:15:00',
          muscles: 'shoulders,triceps',
        },
      ],
      bodyweight: [{ id: 1, date: '2026-09-10', kg: 84.2, note: 'fasted' }],
    };
    const put = await callFetch(
      new Request('http://localhost/sync', {
        method: 'PUT',
        body: JSON.stringify(payload),
        headers: { Authorization: 'Bearer test-secret', 'Content-Type': 'application/json' },
      }),
      authed(r2)
    );
    expect(put.status).toBe(200);
    const get = await callFetch(new Request('http://localhost/snapshot'), authed(r2));
    const body = (await get.json()) as SnapshotBody;
    expect(body.workouts).toEqual(payload.workouts);
    expect(body.sets).toEqual(payload.sets);
    expect(body.bodyweight).toEqual(payload.bodyweight);
  });

  it('404s unknown paths', async () => {
    const res = await callFetch(new Request('http://localhost/nope'), {
      SNAPSHOTS: memR2(),
    });
    expect(res.status).toBe(404);
  });
});

describe('sync concurrency (ETag)', () => {
  const payload = (exported: string) => ({
    exported,
    workouts: [],
    sets: [],
    bodyweight: [],
  });

  function put(env: TestEnv, body: unknown, extraHeaders: Record<string, string> = {}) {
    return callFetch(
      new Request('http://localhost/sync', {
        method: 'PUT',
        body: JSON.stringify(body),
        headers: {
          Authorization: 'Bearer test-secret',
          'Content-Type': 'application/json',
          ...extraHeaders,
        },
      }),
      env
    );
  }

  function getSnapshot(env: TestEnv) {
    return callFetch(new Request('http://localhost/snapshot'), env);
  }

  it('exposes the snapshot ETag on GET', async () => {
    const env = authed(memR2());
    const first = await put(env, payload('2026-09-17T12:00:00'));
    expect(first.status).toBe(200);
    const get = await getSnapshot(env);
    expect(get.headers.get('etag')).toBe('"2026-09-17T12:00:00"');
  });

  it('rejects a stale push with 412 instead of overwriting', async () => {
    const env = authed(memR2());
    await put(env, payload('2026-09-17T12:00:00'));
    const staleTag = (await getSnapshot(env)).headers.get('etag')!;
    // Another session pushes first with a fresh base.
    const fresh = await put(env, payload('2026-09-17T12:05:00'), { 'if-match': staleTag });
    expect(fresh.status).toBe(200);
    // The stale base is now rejected.
    const retry = await put(env, payload('2026-09-17T12:06:00'), { 'if-match': staleTag });
    expect(retry.status).toBe(412);
    const body = (await retry.json()) as { etag: string };
    expect(body.etag).toBe('"2026-09-17T12:05:00"');
    // Stored snapshot is untouched by the rejected push.
    const get = await getSnapshot(env);
    expect(get.headers.get('etag')).toBe('"2026-09-17T12:05:00"');
  });

  it('rejects a headerless push once a snapshot exists, force overwrites', async () => {
    const env = authed(memR2());
    // First push ever needs no base.
    expect((await put(env, payload('2026-09-17T12:00:00'))).status).toBe(200);
    // Pull-first is enforced: no If-Match, no force.
    expect((await put(env, payload('2026-09-17T12:01:00'))).status).toBe(412);
    // Explicit force overwrites.
    const forced = await put(env, payload('2026-09-17T12:01:00'), { 'x-sync-force': '1' });
    expect(forced.status).toBe(200);
    expect((await getSnapshot(env)).headers.get('etag')).toBe('"2026-09-17T12:01:00"');
  });
});
