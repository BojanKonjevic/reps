import { extent, max } from 'd3-array';
import { scaleLinear, scaleTime } from 'd3-scale';

// Canonical chart mathematics. D3 owns scales, domains, and extents;
// Reps owns rendering, ticks (niceTicks in utils, with its 2.5 steps),
// and every product-specific visual. Pixel math matches the previous
// hand-rolled lerps exactly: d3 linear interpolation is the same
// arithmetic, now under a recognizable name.

export type Domain = [number, number];

export function valueExtent(values: Array<number | null | undefined>): Domain | null {
  const xs = values.filter((v): v is number => typeof v === 'number' && Number.isFinite(v));
  if (!xs.length) return null;
  const [lo, hi] = extent(xs) as [number, number];
  return lo === hi ? [lo - 1, hi + 1] : [lo, hi];
}

export function maxExtent(values: Array<number | null | undefined>, fallback = 0): number {
  const m = max(values.filter((v): v is number => typeof v === 'number' && Number.isFinite(v)));
  return m === undefined ? fallback : m;
}

// Symmetric fractional padding with a floor, matching the established
// lift-chart domain expansion (25% of span, at least 5% of max).
export function padDomain([lo, hi]: Domain, frac = 0.25, minPad = 0): Domain {
  const pad = (hi - lo) * frac || Math.max(minPad, hi * 0.05);
  return [Math.max(0, lo - pad), hi + pad];
}

export function linearScale(domain: Domain, range: [number, number]) {
  return scaleLinear().domain(domain).range(range);
}

export function timeScale(dates: string[], range: [number, number]) {
  const ts = dates.map(d => new Date(d + 'T12:00:00').getTime());
  const [lo, hi] = extent(ts) as [number, number];
  const span = Math.max(1, hi - lo);
  return scaleTime()
    .domain([lo, lo + span])
    .range(range);
}
