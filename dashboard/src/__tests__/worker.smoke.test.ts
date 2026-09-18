// @vitest-environment node
import { describe, expect, it } from 'vitest';
import worker from '../index';

// NOTE: this file intentionally runs in plain node with no DOM globals.
// Importing the worker module must not throw: any unguarded
// window/document/localStorage access at module scope fails this whole
// file before assertions even run. That is the regression gate — the same
// file ships to browsers AND to the Workers runtime.

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
    const res = await callFetch(new Request('http://localhost/sync', { method: 'PUT', body: '{}' }), {
      SNAPSHOTS: memR2(),
    });
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
          note: 'grindy',
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
