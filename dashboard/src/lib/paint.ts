// Debounced window-resize repaint for canvas components. Returns a
// cleanup for onMount. Canvases repaint from cached props, never refetch.
export function onResizePaint(paint: () => void): () => void {
  let rt: ReturnType<typeof setTimeout> | null = null;
  const onResize = () => {
    if (rt) clearTimeout(rt);
    rt = setTimeout(paint, 250);
  };
  window.addEventListener('resize', onResize);
  return () => window.removeEventListener('resize', onResize);
}
