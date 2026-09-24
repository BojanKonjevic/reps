// SSOT owner: snapshot-derived vocabulary (muscle colors, groups, thresholds).
// Consumers: charts and pages. Created once per snapshot load; muscle colors
// come from snapshot.constants, lift colors from liftColor hashing (the single
// presentation-only identity->color map).

import type { Snapshot } from '../generated/snapshot';
import { liftColor as hashColor } from '../charts';

export interface Vocab {
  colors: Record<string, string>;
  groups: string[];
  thresholds: Record<string, number>;
  bands(muscle: string): { mev: number; mav: number[] | null; mrv: number | null };
  liftColor(name: string): string;
}

export function vocabOf(snap: Snapshot): Vocab {
  const muscles = snap.constants?.muscles ?? {};
  const colors: Record<string, string> = {};
  for (const [m, e] of Object.entries(muscles)) {
    const c = (e as { color?: string }).color;
    if (typeof c === 'string') colors[m] = c;
  }
  const groups = Object.keys(muscles);
  const thresholds: Record<string, number> = {};
  for (const [k, v] of Object.entries(snap.constants?.thresholds ?? {})) {
    if (typeof v === 'number') thresholds[k] = v;
  }
  return {
    colors,
    groups,
    thresholds,
    bands(muscle: string) {
      const e = muscles[muscle] as
        { mev?: number; mav?: [number, number] | null; mrv?: number | null } | undefined;
      return { mev: e?.mev ?? 0, mav: e?.mav ?? null, mrv: e?.mrv ?? null };
    },
    liftColor(name: string) {
      return hashColor(name);
    },
  };
}
