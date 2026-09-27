import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { onResizePaint } from '../lib/paint';

describe('onResizePaint', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('shares one debounced listener across charts and cleans up', () => {
    let a = 0;
    let b = 0;
    const offA = onResizePaint(() => {
      a += 1;
    });
    const offB = onResizePaint(() => {
      b += 1;
    });
    window.dispatchEvent(new Event('resize'));
    window.dispatchEvent(new Event('resize'));
    expect(a).toBe(0);
    vi.advanceTimersByTime(200);
    expect(a).toBe(1);
    expect(b).toBe(1);
    offA();
    window.dispatchEvent(new Event('resize'));
    vi.advanceTimersByTime(200);
    expect(a).toBe(1);
    expect(b).toBe(2);
    offB();
  });
});
