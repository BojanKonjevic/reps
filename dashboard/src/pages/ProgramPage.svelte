<script lang="ts">
  import { onMount } from 'svelte';
  import { href } from '../routes';
  import type { Snapshot } from '../generated/snapshot';
  import { defOf, groupByDate, programEvents, ruleIdOf, scopeOf, stateOn } from '../lib/temporal';
  import { createEventSelection } from '../lib/eventSelection.svelte';
  import PageShell from '../components/PageShell.svelte';
  import EventStrip from '../components/EventStrip.svelte';
  import ChangeDetail from '../components/ChangeDetail.svelte';
  import TrainingState from '../components/TrainingState.svelte';
  import Provenance from '../components/Provenance.svelte';

  interface Props {
    snap: Snapshot;
  }

  let { snap }: Props = $props();

  const sub = $derived(
    snap.program.rotation.length
      ? 'Active split, rotation: ' + snap.program.rotation.join(' / ')
      : 'Active split.'
  );

  const events = $derived(programEvents(snap));
  const groups = $derived(groupByDate(events));

  const sel = createEventSelection();
  const selected = $derived(events.find(e => e.id === sel.selId) ?? null);
  const histState = $derived(sel.stateDate ? stateOn(snap, sel.stateDate) : null);

  onMount(() => {
    document.title = 'program';
  });
</script>

<PageShell back>
  <div class="wrap" id="viewProgram">
    <h1>Program</h1>
    <div class="sub" id="progSub">{sub}</div>
    {#if groups.length}
      <div class="card" id="progHistCard">
        <div class="cap">Recorded program, rotation, deload, and rule changes</div>
        <EventStrip {groups} selectedId={sel.selId} onSelect={sel.select} id="progEvents" />
        {#if selected}
          <ChangeDetail
            event={selected}
            events={snap.history}
            stateOpen={sel.stateDate === selected.date}
            onViewState={sel.viewState}
            id="progChange"
          />
          {#if histState && sel.stateDate === selected.date}
            <TrainingState
              {histState}
              {snap}
              scope={scopeOf(selected)}
              ruleId={ruleIdOf(selected)}
              id="progState"
            />
          {/if}
        {/if}
        <Provenance def={defOf(snap, 'program_activity')} id="progProv" />
      </div>
    {/if}
    <div id="progGrid">
      {#if !snap.program.days.length}
        <div class="empty">no program synced yet</div>
      {:else}
        <div class="daypanels">
          {#each snap.program.days as day}
            <div class="daypanel">
              <h2>{day.day}</h2>
              <div class="daymuscles">{day.muscles.join(' · ')}</div>
              <table>
                <thead>
                  <tr>
                    <th scope="col"></th>
                    <th scope="col">movement</th>
                    <th scope="col">sets</th>
                    <th scope="col">muscles</th>
                  </tr>
                </thead>
                <tbody>
                  {#each day.slots as r}
                    <tr>
                      <td>{r.slot}</td>
                      <td>
                        {#each r.moves as m, mi}
                          {#if mi > 0}
                            /
                          {/if}<a href={href.lift(m)}>{m}</a>
                        {/each}
                      </td>
                      <td>{r.sets}</td>
                      <td>
                        {#each r.muscles as m, mi}
                          {#if mi > 0},
                          {/if}{#if r.focus.includes(m)}<b>{m}</b>{:else}{m}{/if}
                        {/each}
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
</PageShell>
