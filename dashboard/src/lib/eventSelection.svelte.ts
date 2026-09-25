// SSOT owner: shared event-selection state for temporal views. Consumers:
// every page pairing an EventStrip with ChangeDetail and TrainingState.
// One toggle semantic everywhere: selecting re-selects closed, opening a
// different event closes the state panel.
export function createEventSelection() {
  let selId: number | null = $state(null);
  let stateDate: string | null = $state(null);

  function select(id: number) {
    selId = selId === id ? null : id;
    stateDate = null;
  }

  function viewState(date: string) {
    stateDate = stateDate === date ? null : date;
  }

  return {
    get selId() {
      return selId;
    },
    get stateDate() {
      return stateDate;
    },
    select,
    viewState,
  };
}
