import { describe, it, expect } from 'vitest';
import {
  centeredDomain,
  linearScale,
  maxExtent,
  padDomain,
  timeScale,
  valueExtent,
} from '../lib/scales';

describe('valueExtent', () => {
  it('ignores nulls and returns the data min/max', () => {
    expect(valueExtent([null, 90, 92.5, null, 80])).toEqual([80, 92.5]);
  });
  it('returns null when nothing is finite', () => {
    expect(valueExtent([null, undefined, Number.NaN])).toBeNull();
  });
  it('expands a flat domain so scales stay valid', () => {
    expect(valueExtent([100, 100])).toEqual([99, 101]);
  });
});

describe('maxExtent', () => {
  it('returns the max, falling back when empty', () => {
    expect(maxExtent([1, 7, 3])).toBe(7);
    expect(maxExtent([])).toBe(0);
  });
});

describe('padDomain', () => {
  it('pads symmetrically with a zero floor', () => {
    expect(padDomain([80, 100])).toEqual([75, 105]);
    expect(padDomain([2, 4])).toEqual([1.5, 4.5]);
  });
  it('matches the lift-chart floor convention', () => {
    expect(padDomain([0, 0.4], 0.25, 1)).toEqual([0, 0.5]);
  });
});

describe('linearScale', () => {
  it('maps the lift-chart y pixels exactly', () => {
    const H = 330;
    const P = 46;
    const py = linearScale([90, 110], [H - P, 18]);
    expect(py(90)).toBeCloseTo(H - P, 10);
    expect(py(110)).toBeCloseTo(18, 10);
    expect(py(100)).toBeCloseTo((H - P + 18) / 2, 10);
  });
});

describe('timeScale', () => {
  it('spans the date range across the width', () => {
    const px = timeScale(['2026-09-10', '2026-09-14'], [46, 800]);
    expect(px(new Date('2026-09-10T12:00:00'))).toBeCloseTo(46, 6);
    expect(px(new Date('2026-09-14T12:00:00'))).toBeCloseTo(800, 6);
  });
});

describe('centeredDomain', () => {
  it('centers one value with a 5% pad', () => {
    expect(centeredDomain(100)).toEqual([95, 105]);
  });
  it('floors tiny values at a pad of 1 with a zero floor', () => {
    expect(centeredDomain(20)).toEqual([19, 21]);
    expect(centeredDomain(0)).toEqual([0, 1]);
  });
});
