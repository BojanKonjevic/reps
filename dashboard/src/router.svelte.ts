import { parseHash, type View } from './router';

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
