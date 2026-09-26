// SSOT owner: shared event-selection state for temporal views. Consumers:
// every page pairing an EventStrip with ChangeDetail. One toggle semantic
// everywhere: selecting re-selects closed. The as-of date cursor lives in
// each page (AsOfControl/AsOfPanel), separate from event selection.
export function createEventSelection() {
  let selId: number | null = $state(null);

  function select(id: number) {
    selId = selId === id ? null : id;
  }

  return {
    get selId() {
      return selId;
    },
    select,
  };
}
