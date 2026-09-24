// SSOT owner: routes. Consumers: every link and the router.
// Builders and the parser both derive from the route table; encode/decode
// lives here, exactly once.

export type Route =
  | { name: 'dash' }
  | { name: 'lift'; exercise: string }
  | { name: 'session'; date: string }
  | { name: 'muscle'; muscle: string }
  | { name: 'program' }
  | { name: 'lifts' }
  | { name: 'muscles' };

export const href = {
  dash(): string {
    return '#/';
  },
  lift(exercise: string): string {
    return '#/l/' + encodeURIComponent(exercise);
  },
  session(date: string): string {
    return '#/s/' + encodeURIComponent(date);
  },
  muscle(muscle: string): string {
    return '#/m/' + encodeURIComponent(muscle);
  },
  program(): string {
    return '#/program';
  },
  lifts(): string {
    return '#/lifts';
  },
  muscles(): string {
    return '#/muscles';
  },
};

export function parse(hash: string): Route {
  const path = hash.startsWith('#') ? hash.slice(1) : hash;
  const segs = path.split('/').map(s => {
    try {
      return decodeURIComponent(s);
    } catch {
      return s;
    }
  });
  if (segs[1] === 'l' && segs[2]) return { name: 'lift', exercise: segs[2] };
  if (segs[1] === 's' && segs[2] && isDate(segs[2])) return { name: 'session', date: segs[2] };
  if (segs[1] === 'm' && segs[2]) return { name: 'muscle', muscle: segs[2] };
  if (segs[1] === 'program') return { name: 'program' };
  if (segs[1] === 'lifts') return { name: 'lifts' };
  if (segs[1] === 'muscles') return { name: 'muscles' };
  return { name: 'dash' };
}

export function isDate(s: string): boolean {
  if (!s || s.length !== 10 || s.charAt(4) !== '-' || s.charAt(7) !== '-') return false;
  for (let i = 0; i < 10; i += 1) {
    if (i === 4 || i === 7) continue;
    const c = s.charAt(i);
    if (c < '0' || c > '9') return false;
  }
  return true;
}
