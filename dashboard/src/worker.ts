/// <reference types="@cloudflare/workers-types" />

interface Env {
  SNAPSHOTS: R2Bucket;
  SYNC_SECRET: string;
}

const BLANK = {
  note: 'no sync yet, run sync from the CLI after a session',
  workouts: [],
  sets: [],
  bodyweight: [],
};

// Optimistic concurrency: the snapshot ETag is the quoted `exported`
// timestamp of the stored payload. A PUT made from a stale pull carries a
// non-matching If-Match and is rejected with 412 instead of silently
// overwriting the newer snapshot. `sync force` sends X-Sync-Force to
// overwrite deliberately after reconciling.
function etagFor(body: string): string | null {
  try {
    const data = JSON.parse(body) as { exported?: unknown };
    if (data && typeof data.exported === 'string' && data.exported) {
      return '"' + data.exported + '"';
    }
  } catch {
    // not JSON or no exported field: no ETag
  }
  return null;
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    if (req.method === 'PUT' && url.pathname === '/sync') {
      const auth = req.headers.get('authorization') || '';
      if (!env.SYNC_SECRET || auth !== 'Bearer ' + env.SYNC_SECRET) {
        return Response.json({ error: 'unauthorized' }, { status: 401 });
      }
      const raw = await req.text();
      if (raw.length > 2000000) {
        return Response.json({ error: 'snapshot too large' }, { status: 413 });
      }
      try {
        JSON.parse(raw);
      } catch {
        return Response.json({ error: 'not json' }, { status: 400 });
      }
      const current = await env.SNAPSHOTS.get('snapshot.json');
      if (current) {
        const forced = req.headers.get('x-sync-force') === '1';
        if (!forced) {
          const currentTag = etagFor(await current.text());
          const match = req.headers.get('if-match');
          if (currentTag !== null && match !== currentTag) {
            return Response.json(
              { error: 'stale snapshot, pull first then push', etag: currentTag },
              { status: 412, headers: { etag: currentTag } }
            );
          }
        }
      }
      await env.SNAPSHOTS.put('snapshot.json', raw, {
        httpMetadata: { contentType: 'application/json' },
      });
      const tag = etagFor(raw);
      return Response.json(
        tag ? { ok: true, bytes: raw.length, etag: tag } : { ok: true, bytes: raw.length }
      );
    }
    if (url.pathname === '/snapshot') {
      const obj = await env.SNAPSHOTS.get('snapshot.json');
      if (!obj) return Response.json(BLANK);
      const raw = await obj.text();
      const tag = etagFor(raw);
      return new Response(raw, {
        headers: tag
          ? { 'content-type': 'application/json', etag: tag }
          : { 'content-type': 'application/json' },
      });
    }
    return new Response('not found', { status: 404 });
  },
};
