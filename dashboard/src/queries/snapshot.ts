import { snapshotSchema, type Snapshot } from '../generated/snapshot';
import { SCHEMA_VERSION, SNAPSHOT_SCHEMA_VERSION } from '../generated/version';

// Query function for the snapshot key: HTTP endpoint, runtime validation,
// then the TanStack cache. A malformed payload fails here, explicitly,
// instead of propagating arbitrary JSON into components.

export async function fetchSnapshot(): Promise<Snapshot> {
  const res = await fetch('/snapshot');
  if (!res.ok) throw new Error('snapshot fetch failed: ' + res.status);
  const snap = snapshotSchema.parse(await res.json());
  if (snap.schema_version !== SNAPSHOT_SCHEMA_VERSION) {
    throw new Error(
      'snapshot schema v' +
        snap.schema_version +
        ' != dashboard v' +
        SNAPSHOT_SCHEMA_VERSION +
        ' (resync needed)'
    );
  }
  return snap;
}

export { SCHEMA_VERSION };
