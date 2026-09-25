// Palette open state. Client-only UI state like filters.svelte; the page list
// itself lives in select.ts so filtering stays unit-testable without a DOM.

export const palette: { open: boolean } = $state({ open: false });
