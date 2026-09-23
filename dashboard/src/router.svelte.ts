// Hash router. Routes mirror the legacy controller exactly so links,
// bookmarks, and e2e hooks keep working: #/ dashboard, #/s/<date>,
// #/l/<lift>, #/m/<muscle>, #/program, #/lifts, #/muscles.

export type View =
  | { name: 'dash' }
  | { name: 'sess'; date: string }
  | { name: 'lift'; exercise: string }
  | { name: 'muscle'; muscle: string }
  | { name: 'prog' }
  | { name: 'lifts' }
  | { name: 'muscles' };

function isDate(s: string): boolean {
  if (!s || s.length !== 10 || s.charAt(4) !== '-' || s.charAt(7) !== '-') return false;
  for (let i = 0; i < 10; i += 1) {
    if (i === 4 || i === 7) continue;
    const c = s.charAt(i);
    if (c < '0' || c > '9') return false;
  }
  return true;
}

export function parseHash(hash: string): View {
  const h = hash || '';
  if (h.startsWith('#/s/')) {
    const ds = h.slice(4, 14);
    if (isDate(ds)) return { name: 'sess', date: ds };
  } else if (h.startsWith('#/l/')) {
    return { name: 'lift', exercise: decodeURIComponent(h.slice(4)) };
  } else if (h.startsWith('#/m/')) {
    return { name: 'muscle', muscle: decodeURIComponent(h.slice(4)) };
  } else if (h === '#/program') {
    return { name: 'prog' };
  } else if (h === '#/lifts') {
    return { name: 'lifts' };
  } else if (h === '#/muscles') {
    return { name: 'muscles' };
  }
  return { name: 'dash' };
}

export const route = $state({
  view: parseHash(typeof location !== 'undefined' ? location.hash : '') as View,
});

export function syncRoute() {
  route.view = parseHash(location.hash);
}

export function go(hash: string) {
  if (location.hash === hash) syncRoute();
  else location.hash = hash;
}
