// Shared repaint scheduling for canvas components. One debounced window
// resize listener for the whole page: previously every chart registered its
// own listener through canvasShell (N TrendMini instances, N listeners).
// Paints repaint from cached props, never refetch; each paint keeps its own
// isVisible guard, so hidden canvases never paint (zero-size bitmaps would
// stretch into smears on show).

const paints = new Set<() => void>();
let rt: ReturnType<typeof setTimeout> | null = null;
let attached = false;

function ensureListener(): void {
  if (attached || typeof window === 'undefined') return;
  attached = true;
  window.addEventListener('resize', () => {
    if (rt) clearTimeout(rt);
    rt = setTimeout(() => {
      for (const paint of [...paints]) paint();
    }, 150);
  });
}

export function onResizePaint(paint: () => void): () => void {
  // Debounced window-resize repaint for canvas components. Returns a
  // cleanup for onMount. Canvases repaint from cached props, never refetch.
  ensureListener();
  paints.add(paint);
  return () => {
    paints.delete(paint);
  };
}
