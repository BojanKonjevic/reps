// PWA installability contract: the manifest carries every field Chrome
// needs for the install prompt, its icons exist at the declared sizes, and
// its colors mirror design/tokens.css (JSON cannot read CSS vars, so the
// test keeps the two copies aligned).
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const PUBLIC = join(__dirname, '..', '..', 'public');

function pngSize(p: string): { w: number; h: number } {
  const b = Buffer.from(readFileSync(p));
  expect(b.subarray(0, 8)).toEqual(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]));
  expect(b.toString('ascii', 12, 16)).toBe('IHDR');
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}

describe('PWA manifest', () => {
  it('declares an installable app whose colors match tokens.css', () => {
    const manifest = JSON.parse(readFileSync(join(PUBLIC, 'manifest.webmanifest'), 'utf8'));
    expect(manifest.name).toBeTruthy();
    expect(manifest.short_name).toBeTruthy();
    expect(manifest.start_url).toBe('/');
    expect(manifest.scope).toBe('/');
    expect(manifest.display).toBe('standalone');
    const tokens = readFileSync(join(__dirname, '..', 'design', 'tokens.css'), 'utf8');
    const bg = tokens.match(/--bg:\s*(#[0-9a-fA-F]+)/)?.[1];
    expect(bg).toBeTruthy();
    expect(manifest.background_color).toBe(bg);
    expect(manifest.theme_color).toBe(bg);
    const sizes = manifest.icons.map((i: { sizes: string; purpose?: string }) =>
      (i.sizes + ' ' + (i.purpose || 'any')).trim()
    );
    expect(sizes).toContain('192x192 any');
    expect(sizes).toContain('512x512 any');
    expect(sizes).toContain('512x512 maskable');
  });

  it('ships every declared icon at its declared size', () => {
    const manifest = JSON.parse(readFileSync(join(PUBLIC, 'manifest.webmanifest'), 'utf8'));
    for (const icon of manifest.icons as Array<{
      src: string;
      sizes: string;
      type: string;
    }>) {
      const file = join(PUBLIC, icon.src.replace(/^\//, ''));
      expect(existsSync(file), icon.src).toBe(true);
      if (icon.type === 'image/png') {
        const [w, h] = icon.sizes.split('x').map(Number);
        expect(pngSize(file)).toEqual({ w, h });
      }
    }
  });
});
