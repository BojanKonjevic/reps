// SSOT gate tests: fail the build when a second mechanism appears.
// Mirrors scripts/ssot_check.py G6-G11 on the TS side. Each failure names the
// owner to use instead (agents self-correct from the error).
import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'fs';
import { join } from 'path';

const SRC = join(__dirname, '..');

function files(dir: string, exts: string[]): string[] {
  const out: string[] = [];
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    if (statSync(p).isDirectory()) {
      if (e === 'generated' || e === 'fixtures' || e === '__tests__') continue;
      out.push(...files(p, exts));
    } else if (exts.some(x => p.endsWith(x))) out.push(p);
  }
  return out;
}

const TS = () => files(SRC, ['.ts', '.svelte']);
const CSS = () => files(SRC, ['.css']).filter(f => !f.endsWith('tokens.css'));

describe('SSOT gates', () => {
  it('G1: no e1RM formula outside generated code (use reps/e1rm.py, snapshot fields)', () => {
    const bad = TS().filter(f => /\/ 30(\.0)?/.test(readFileSync(f, 'utf8')));
    expect(bad).toEqual([]);
  });

  it('no domain-logic identifiers outside their owners', () => {
    const banned = [
      'isStalling',
      'deloadWatch',
      'labelSession',
      'nextSlot',
      'computePRs',
      'weekKey',
    ];
    const offenders: string[] = [];
    for (const f of TS()) {
      const text = readFileSync(f, 'utf8');
      for (const id of banned) {
        if (new RegExp(`\\b${id}\\b`).test(text)) offenders.push(`${f}: ${id}`);
      }
    }
    expect(offenders).toEqual([]);
  });

  it('G6: no hex colors or rgba() outside design/tokens.css', () => {
    const offenders: string[] = [];
    for (const f of [...TS(), ...CSS()]) {
      const text = readFileSync(f, 'utf8');
      const hits = text.match(/#[0-9a-fA-F]{3,8}\b|rgba?\(/g);
      if (hits) offenders.push(`${f}: ${hits.join(', ')}`);
    }
    expect(offenders).toEqual([]);
  });

  it('G7: no route literals or encodeURIComponent outside routes.ts', () => {
    const offenders = TS().filter(f => {
      if (f.endsWith('routes.ts')) return false;
      const text = readFileSync(f, 'utf8');
      return text.includes("'#/") || text.includes('encodeURIComponent');
    });
    expect(offenders).toEqual([]);
  });

  it('G8: no inline SVG outside Icon.svelte', () => {
    const offenders = TS().filter(
      f => !f.endsWith('Icon.svelte') && readFileSync(f, 'utf8').includes('<svg')
    );
    expect(offenders).toEqual([]);
  });

  it('G9: no viewer-clock reads outside lib/clock.ts and lib/format.ts', () => {
    const offenders: string[] = [];
    for (const f of TS()) {
      if (f.endsWith('lib/clock.ts') || f.endsWith('lib/format.ts')) continue;
      const text = readFileSync(f, 'utf8');
      if (/Date\.now\(/.test(text)) offenders.push(`${f}: Date.now`);
      if (/new Date\(\s*\)/.test(text)) offenders.push(`${f}: new Date()`);
    }
    expect(offenders).toEqual([]);
  });

  it('G10: no constants.json imports (use snapshot.constants via lib/vocab)', () => {
    const offenders = TS().filter(f => readFileSync(f, 'utf8').includes('constants.json'));
    expect(offenders).toEqual([]);
  });

  it('G11: no hand-written snapshot types outside generated/', () => {
    const offenders: string[] = [];
    for (const f of TS()) {
      const text = readFileSync(f, 'utf8');
      const decls = text.match(/(interface Snap\w*|type Snap\w*\s*=)/g);
      const imports = (text.match(/import [^;]*;/g) || []).join(' ');
      if (decls && !imports.includes(decls[0])) offenders.push(`${f}: ${decls.join(', ')}`);
    }
    expect(offenders).toEqual([]);
  });
});
