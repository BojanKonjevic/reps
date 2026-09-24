// SSOT owner: status -> color/arrow mapping. Consumers: every page table and badge.
// The only place verdict/direction/status maps to color or arrow.

import { theme } from './theme';

export function verdictClass(verdict: string): string {
  if (verdict === 'hit') return 'good';
  if (verdict === 'miss') return 'bad';
  return 'muted';
}

export function verdictColor(verdict: string): string {
  if (verdict === 'hit') return theme.color('good');
  if (verdict === 'miss') return theme.color('bad');
  return theme.color('ink-mute');
}

export function directionArrow(direction: string): string {
  if (direction === 'up') return '↗';
  if (direction === 'down') return '↘';
  return '→';
}

export function directionClass(direction: string): string {
  if (direction === 'up') return 'good';
  if (direction === 'down') return 'bad';
  return 'muted';
}

export function statusLabel(status: string): string {
  return status.replace(/_/g, ' ');
}

export function markText(kind: string): string {
  if (kind === 'stalling') return 'stalling';
  if (kind === 'slipping') return 'slipping';
  if (kind === 'goal') return 'goal';
  if (kind === 'focus') return 'focus';
  if (kind === 'autoreg') return 'autoreg';
  return 'grouped';
}

export function markClass(kind: string): string {
  if (kind === 'goal') return 'plan';
  return 'bad';
}
