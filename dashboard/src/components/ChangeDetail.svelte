<script lang="ts">
  // SSOT owner: change-detail presentation. Consumers: every annotated view.
  // Shared temporal primitive: what/when/before/after/why/reversal detail.
  import { fmtD } from '../lib/format';
  import { domainLabel, envelopeLines, reversalOf } from '../lib/temporal';
  import type { HistoryEvent } from '../generated/snapshot';

  interface Props {
    event: HistoryEvent;
    events: HistoryEvent[];
    stateOpen: boolean;
    onViewState: (date: string) => void;
    id?: string;
  }

  let { event: e, events, stateOpen, onViewState, id = undefined }: Props = $props();

  const rev = $derived(reversalOf(e, events));
  const before = $derived(envelopeLines(e.domain, e.before));
  const after = $derived(envelopeLines(e.domain, e.after));
</script>

<div class="changedetail" {id}>
  <div class="cdhead">
    <span class="cdomain">{domainLabel(e.domain)}</span>
    <b>{e.title}</b>
    <span class="meta">{fmtD(e.date)}</span>
  </div>
  <div class="cdcols">
    <div>
      <div class="cap">Before</div>
      {#each before as line}
        <div>{line}</div>
      {/each}
    </div>
    <div>
      <div class="cap">After</div>
      {#each after as line}
        <div>{line}</div>
      {/each}
    </div>
  </div>
  <div class="cdev">
    <span class="cap">Evidence</span>
    <span>{e.evidence || 'no reason recorded'}</span>
  </div>
  {#if rev.reverses}
    <div class="cdrev">Reversal of {rev.reverses.title} ({fmtD(rev.reverses.date)})</div>
  {/if}
  {#if rev.reversedBy}
    <div class="cdrev">Reversed {fmtD(rev.reversedBy.date)}</div>
  {/if}
  <button type="button" class="evbtn" onclick={() => onViewState(e.date)}>
    {stateOpen
      ? 'Hide training state on ' + fmtD(e.date)
      : 'View training state on ' + fmtD(e.date)}
  </button>
</div>
