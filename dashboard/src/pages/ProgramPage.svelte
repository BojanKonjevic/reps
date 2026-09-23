<script lang="ts">
  import { onMount } from 'svelte';
  import type { Snapshot } from '../schemas/snapshot';
  import { programModel } from '../lib/dashboard';

  interface Props {
    snap: Snapshot;
  }

  let { snap }: Props = $props();

  const model = $derived(programModel(snap));

  onMount(() => {
    document.title = 'program';
    window.scrollTo(0, 0);
  });
</script>

<div class="wrap" id="viewProgram">
  <div class="sesstop">
    <a class="iconbtn" href="#/" aria-label="dashboard"
      ><svg viewBox="0 0 16 16" width="22" height="22">
        <path
          d="M2.5 8 8 2.5 13.5 8M4.5 6.5v7h7v-7M7 13.5v-3h2v3"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
        /></svg
      ></a
    >
  </div>
  <h1>Program</h1>
  <div class="sub" id="progSub">{model.sub}</div>
  <div id="progGrid">
    {#if !model.days.length}
      <div class="empty">no program synced yet, split show in chat is the source</div>
    {:else}
      <div class="daypanels">
        {#each model.days as day}
          <div class="daypanel">
            <h2>{day.day}</h2>
            <div class="daymuscles">{day.muscles}</div>
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
                        {/if}<a href="#/l/{encodeURIComponent(m)}">{m}</a>
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
