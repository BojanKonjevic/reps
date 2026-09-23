import { onMount } from 'svelte';
import { onResizePaint } from './paint';

// Shared canvas shell: every chart component paints a bespoke renderer
// into its canvas, repaints on prop change and debounced window resize,
// and never paints while hidden (zero-size bitmaps stretch into smears).
// Hover and tooltip bodies stay per-chart; only the lifecycle is shared.
export function isVisible(cv: HTMLCanvasElement | undefined): boolean {
  return !!cv && cv.clientWidth > 0 && cv.clientHeight > 0;
}

export function canvasShell(paint: () => void, onDone?: () => void): void {
  onMount(() => {
    paint();
    const cleanupResize = onResizePaint(paint);
    return () => {
      cleanupResize();
      onDone?.();
    };
  });
}
