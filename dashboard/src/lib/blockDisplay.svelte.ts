import type { BlockView } from '../generated/snapshot';

export const blockDisplay = $state<{
  selected: BlockView | null;
  boundaries: string[];
}>({ selected: null, boundaries: [] });
