// SSOT owner: canvas access to design tokens. Consumers: every chart module.
// Reads CSS custom properties once (after fonts load) and exposes them.

let cache: Record<string, string> | null = null;

function read(): Record<string, string> {
  if (cache) return cache;
  const out: Record<string, string> = {};
  try {
    const cs = getComputedStyle(document.documentElement);
    for (const k of [
      'bg',
      'bg-soft',
      'bg-raised',
      'bg-hover',
      'bg-active',
      'ink',
      'ink-dim',
      'ink-mute',
      'ink-faint',
      'line',
      'line-soft',
      'good',
      'good-deep',
      'bad',
      'bad-deep',
      'warn',
      'accent',
      'accent-strong',
      'accent-dim',
      'link',
      'overlay-dim',
      'overlay-tick',
      'overlay-tick-strong',
    ]) {
      out[k] = cs.getPropertyValue('--' + k).trim();
    }
  } catch {
    // non-DOM test env: fall back to the token values in design/tokens.css
  }
  if (!out['ink']) {
    // Design values live only in design/tokens.css; with no computed style
    // (non-DOM test env) there is nothing to read, so callers get white.
    // No second copy of the palette lives here by design.
    return {};
  }
  cache = out;
  return out;
}

export const theme = {
  color(name: string): string {
    // No hex fallback here by design: token values live only in
    // design/tokens.css. Outside a DOM with the tokens loaded (unit tests,
    // which never paint canvas) this resolves to transparent.
    return read()[name] || 'transparent';
  },
  font(size: number, weight: number): string {
    return weight + ' ' + size + "px 'IBM Plex Sans', sans-serif";
  },
  reset(): void {
    cache = null;
  },
};
