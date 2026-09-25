import { parseHash, type View } from './router';

export const route = $state({
  view: parseHash(typeof location !== 'undefined' ? location.hash : '') as View,
});

// Scroll position per visited hash. Hash navigation never restores scroll on
// its own, so the router saves the outgoing position and restores the saved
// one (or the top for first visits) after the new view renders. Pages must
// not scroll themselves; that would race the restore.
const positions = new Map<string, number>();
let current = typeof location !== 'undefined' ? location.hash : '';

export function syncRoute() {
  if (typeof window !== 'undefined') positions.set(current, window.scrollY);
  current = typeof location !== 'undefined' ? location.hash : '';
  route.view = parseHash(typeof location !== 'undefined' ? location.hash : '');
  const y = positions.get(current);
  if (typeof window !== 'undefined') {
    requestAnimationFrame(() => window.scrollTo(0, y ?? 0));
  }
}

export function go(hash: string) {
  if (location.hash === hash) syncRoute();
  else location.hash = hash;
}
