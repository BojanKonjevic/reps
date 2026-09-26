/// <reference types="@cloudflare/workers-types" />
import BLANK from './generated/blank.json';
import { SCHEMA_VERSION, SNAPSHOT_SCHEMA_VERSION } from './generated/version';

interface Env {
  SNAPSHOTS: R2Bucket;
  SYNC_SECRET: string;
}

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

function schemaOf(body: string): number | null {
  try {
    const data = JSON.parse(body) as { schema_version?: unknown };
    if (data && typeof data.schema_version === 'number') return data.schema_version;
  } catch {
    // not JSON: no version
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
        return Response.json({ error: 'payload too large' }, { status: 413 });
      }
      let envelope: unknown;
      try {
        envelope = JSON.parse(raw);
      } catch {
        return Response.json({ error: 'not json' }, { status: 400 });
      }
      const snapshotRaw =
        envelope && typeof envelope === 'object' && 'snapshot' in envelope
          ? JSON.stringify((envelope as { snapshot: unknown }).snapshot)
          : raw;
      const statesRaw =
        envelope && typeof envelope === 'object' && 'history_states' in envelope
          ? JSON.stringify((envelope as { history_states: unknown }).history_states)
          : null;
      if (schemaOf(snapshotRaw) !== SNAPSHOT_SCHEMA_VERSION) {
        return Response.json(
          {
            error:
              'schema v' +
              schemaOf(snapshotRaw) +
              ' != worker v' +
              SNAPSHOT_SCHEMA_VERSION +
              ' (resync needed)',
          },
          { status: 409 }
        );
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
      await env.SNAPSHOTS.put('snapshot.json', snapshotRaw, {
        httpMetadata: { contentType: 'application/json' },
      });
      if (statesRaw !== null) {
        await env.SNAPSHOTS.put('history-states.json', statesRaw, {
          httpMetadata: { contentType: 'application/json' },
        });
      }
      const tag = etagFor(snapshotRaw);
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
    if (url.pathname === '/history-states') {
      const obj = await env.SNAPSHOTS.get('history-states.json');
      if (!obj) return Response.json({ error: 'no history states synced' }, { status: 404 });
      return new Response(await obj.text(), {
        headers: { 'content-type': 'application/json' },
      });
    }
    return new Response('not found', { status: 404 });
  },
};

export { SCHEMA_VERSION };
