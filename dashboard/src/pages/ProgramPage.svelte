<script lang="ts">
  import { onMount } from 'svelte';
  import { href } from '../routes';
  import type { Snapshot } from '../generated/snapshot';
  import PageShell from '../components/PageShell.svelte';

  interface Props {
    snap: Snapshot;
  }

  let { snap }: Props = $props();

  const sub = $derived(
    snap.program.rotation.length
      ? 'Active split, rotation: ' + snap.program.rotation.join(' / ')
      : 'Active split.'
  );

  onMount(() => {
    document.title = 'program';
  });
</script>

<PageShell back>
  <div class="wrap" id="viewProgram">
    <h1>Program</h1>
    <div class="sub" id="progSub">{sub}</div>
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
