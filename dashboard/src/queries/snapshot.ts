import { snapshotSchema, type Snapshot } from '../schemas/snapshot';

// Query function for the snapshot key: HTTP endpoint, runtime validation,
// then the TanStack cache. A malformed payload fails here, explicitly,
// instead of propagating arbitrary JSON into components.

export async function fetchSnapshot(): Promise<Snapshot> {
  const res = await fetch('/snapshot');
  if (!res.ok) throw new Error('snapshot fetch failed: ' + res.status);
  return snapshotSchema.parse(await res.json());
}
