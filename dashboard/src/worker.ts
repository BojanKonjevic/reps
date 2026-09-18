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
      await env.SNAPSHOTS.put('snapshot.json', raw, {
        httpMetadata: { contentType: 'application/json' },
      });
      return Response.json({ ok: true, bytes: raw.length });
    }
    if (url.pathname === '/snapshot') {
      const obj = await env.SNAPSHOTS.get('snapshot.json');
      if (!obj) return Response.json(BLANK);
      return new Response(obj.body, {
        headers: { 'content-type': 'application/json' },
      });
    }
    return new Response('not found', { status: 404 });
  },
};
