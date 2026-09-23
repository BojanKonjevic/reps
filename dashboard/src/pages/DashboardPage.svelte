<script lang="ts">
  import { onMount } from 'svelte';
  import { liftColor, MC } from '../charts';
  import { GROUPS } from '../charts';
  import { goalPercent, isStalling, deloadWatch } from '../forward';
  import { fmtD, fmtV } from '../utils';
  import type { Snapshot } from '../schemas/snapshot';
  import {
    bestSetRows,
    breakGap,
    computeTrend,
    dayDetailOf,
    deprioMuscles,
    goalExerciseSet,
    missedMap,
    musclesOf,
    nextUp,
    nowLines,
    prDatesOf,
    prioMuscles,
    programModel,
    prData,
    rankLifts,
    recentNotes,
    restDatesOf,
    slotOfDate,
    subLine,
    trendMarks,
    volumeWeeksOf,
    adherenceWeeksView,
  } from '../lib/dashboard';
  import {
    defaultHide,
    hideAllLifts,
    pruneHidden,
    resetTrend,
    showAllLifts,
    toggleHidden,
    ui,
  } from '../lib/filters.svelte';
  import TrendMini from '../components/TrendMini.svelte';
  import VolumeChart from '../components/VolumeChart.svelte';
  import BodyweightChart from '../components/BodyweightChart.svelte';
  import GoalChartView from '../components/GoalChartView.svelte';
  import Calendar from '../components/Calendar.svelte';

  interface Props {
    snap: Snapshot;
  }

  let { snap }: Props = $props();

  const top = $derived(rankLifts(snap));
  const trend = $derived(computeTrend(snap, top));
  const slots = $derived(slotOfDate(snap));
  const pr = $derived(prData(snap));
  const missed = $derived(missedMap(snap));
  const prog = $derived(programModel(snap));

  let paintedStamp = $state('');
  $effect(() => {
    if (snap.exported !== paintedStamp) {
      paintedStamp = snap.exported;
      pruneHidden(top);
      defaultHide(top);
    }
  });

  onMount(() => {
    document.title = 'reps dashboard';
  });

  function passFilter(t: string, i: number): boolean {
    if (ui.trendQ && !t.toLowerCase().includes(ui.trendQ)) return false;
    if (!ui.trendFacets.size) return true;
    for (const f of ui.trendFacets) {
      if (f === 'goal' && goalExerciseSet(snap).has(t.toLowerCase())) return true;
      if (f === 'stall') {
        const pts = trend.series[i].filter((v): v is number => v !== null).map(ev => ({ ev }));
        if (isStalling(pts) || deloadWatch(pts)) return true;
      }
      if (f === 'focus' && musclesOf(snap, t).some(m => prioMuscles(snap).has(m.toLowerCase())))
        return true;
    }
    return false;
  }

  const shownIdx = $derived(
    top.map((t, i) => i).filter(i => !ui.hidden.has(top[i]) && passFilter(top[i], i))
  );

  const prDateOf = $derived(prDatesOf(snap, pr));

  const dayDetail = $derived(dayDetailOf(snap));

  const restDates = $derived(restDatesOf(snap, dayDetail));

  const volumeWeeks = $derived(volumeWeeksOf(snap, GROUPS));

  const focus = $derived(prioMuscles(snap));
  const deprio = $derived(deprioMuscles(snap));
  const mevOf = (g: string) => (snap.constants?.muscles[g]?.mev as number | undefined) || 0;

  const next = $derived(nextUp(snap));
  const adhDays = $derived(snap.adherence?.days || []);
  const adhWeeks = $derived(adherenceWeeksView(snap));
  const goals = $derived(snap.goals);
  const progEntries = $derived(Object.keys(snap.progression).sort() as string[]);
</script>

<div class="wrap" id="viewDash">
  <div class="toprow">
    <div>
      <h1>Training dashboard</h1>
      <div class="sub" id="sub">{subLine(snap)}</div>
    </div>
    <div class="nowlines" id="nowLines">
      {#each nowLines(snap) as line}
        <div>
          {#each line as seg}
            {#if seg.b}<b>{seg.t}</b>{:else}{seg.t}{/if}
          {/each}
        </div>
      {/each}
    </div>
  </div>

  <div id="nextWrap">
    <h2>Next up</h2>
    <div class="card" id="nextCard">
      {#if 'empty' in next}
        <div class="empty">{next.empty}</div>
      {:else}
        <h3>Next up: {next.day}</h3>
        {#each next.rows as row}
          <div class="nextrow">
            <a href="#/l/{encodeURIComponent(row.movement)}">{row.movement}</a>
            <span class="meta">{row.detail}</span>
          </div>
        {/each}
        <div class="cap">{next.basis}</div>
      {/if}
    </div>
  </div>

  {#if snap.signals}
    <div id="sigWrap">
      <h2>Coach notes</h2>
      <div class="card" id="sigCard">
        {#if !snap.signals.length}
          <div class="empty">all clear, nothing flagged</div>
        {:else}
          {#each snap.signals as r}
            <div class="sigrow">
              <span class="sigtag sig-{r.severity}">{r.severity.toUpperCase()}</span>
              <span>{r.text}</span>
            </div>
          {/each}
        {/if}
      </div>
      <div class="cap">
        Warning signs in words, worst first. Every line restates a computed fact.
      </div>
    </div>
  {/if}

  <div>
    <h2>Estimated 1RM trend</h2>
    <div class="card">
      <div class="filterbar">
        <input
          id="trendSearch"
          type="search"
          placeholder="search lifts"
          aria-label="search lifts"
          value={ui.trendQ}
          oninput={e => {
            ui.trendQ = (e.target as HTMLInputElement).value.trim().toLowerCase();
          }}
        />
        <span class="legend" id="trendFacets">
          <button type="button" class="chip mini" onclick={resetTrend}>Reset</button>
          {#each [['Goals', 'goal'], ['Stalling', 'stall'], ['Focus', 'focus']] as [label, facet]}
            <button
              type="button"
              class="chip mini"
              class:off={!ui.trendFacets.has(facet)}
              data-facet={facet}
              aria-pressed={ui.trendFacets.has(facet)}
              onclick={() => {
                if (ui.trendFacets.has(facet)) ui.trendFacets.delete(facet);
                else ui.trendFacets.add(facet);
              }}>{label}</button
            >
          {/each}
        </span>
      </div>
      <div class="minigrid" id="trendGrid">
        {#if !shownIdx.length}
          <div class="empty">no lifts match, adjust filters or use Reset</div>
        {:else}
          {#each shownIdx as i}
            {@const t = top[i]}
            {@const vals = trend.series[i]}
            {@const marks = trendMarks(snap, t, vals)}
            <div class="mini">
              <div class="minititle">
                <a href="#/l/{encodeURIComponent(t)}">{t}</a>
                {#if marks.length}
                  <span class="ministat">
                    {#each marks as m}
                      <span class="minisub {m.cls}">{m.text}</span>
                    {/each}
                  </span>
                {/if}
              </div>
              <a href="#/l/{encodeURIComponent(t)}" aria-label={t} style="display:block">
                <TrendMini
                  days={trend.days}
                  {vals}
                  color={liftColor(t)}
                  meta={trend.meta[i]}
                  prDates={prDateOf[t] || {}}
                />
              </a>
            </div>
          {/each}
        {/if}
      </div>
      <div class="legend" id="legTrend">
        <button type="button" class="chip mini" onclick={showAllLifts}>All</button>
        <button type="button" class="chip mini" onclick={() => hideAllLifts(top)}>None</button>
        {#each top as t}
          <button
            type="button"
            class="chip"
            class:off={ui.hidden.has(t)}
            aria-pressed={!ui.hidden.has(t)}
            onclick={() => toggleHidden(t)}
          >
            <span class="sw" style:background={liftColor(t)}></span>{t}
          </button>
        {/each}
      </div>
      <div class="cap">
        Best set per session, each lift on its own scale. Tap a lift for detail.
      </div>
    </div>
  </div>

  <div class="cols2">
    <div>
      <h2>Weekly volume by muscle</h2>
      <div class="card">
        <VolumeChart
          labels={volumeWeeks.labels}
          weeks={volumeWeeks.rows}
          {mevOf}
          onSelect={g => (location.hash = '#/m/' + encodeURIComponent(g))}
        />
        <div class="legend" id="legMus">
          {#each GROUPS as g}
            <a
              href="#/m/{encodeURIComponent(g)}"
              class:chip={true}
              class:focus={focus.has(g.toLowerCase())}
              class:dim={deprio.has(g.toLowerCase())}
            >
              <span class="sw" style:background={MC[g]}></span>{g}
            </a>
          {/each}
        </div>
        <div class="cap">One set can count for several muscles.</div>
      </div>
      <h2>Bodyweight</h2>
      <div class="card">
        <BodyweightChart rows={snap.bodyweight} />
        <div class="cap">
          Gym scale weigh ins, as logged in chat. Dashed spans are gaps, not measurements. Thin line
          is the 7-day average.
        </div>
      </div>
    </div>
    <div>
      <h2>Training calendar</h2>
      <div class="card calcard">
        <Calendar
          {snap}
          prDates={pr.prDates}
          prIds={pr.prIds}
          slotOfDate={slots}
          {dayDetail}
          {restDates}
          {missed}
          breakDays={breakGap(snap)}
        />
        <ul class="notes" id="noteList">
          {#each recentNotes(snap) as n}
            <li style:color={n.hot ? '#f0d060' : undefined}>
              <a href="#/s/{n.date}">{n.text}</a>
            </li>
          {/each}
        </ul>
      </div>
      {#if adhDays.length}
        <div id="adhWrap">
          <h2>Consistency</h2>
          <div class="card" id="adhCard">
            <div class="dtstrip">
              {#each adhDays as d}
                <span
                  class="dt dt-{d.status.replace('_', '')}"
                  title="{d.date}: {d.status} (expected {d.expected})"
                ></span>
              {/each}
            </div>
            <div class="adhweeks">
              {#each adhWeeks as w}
                <div>{w.week} · {w.trained}/{w.expected} sessions</div>
              {/each}
            </div>
            <div class="cap">
              Green is trained as planned, red is missed, hollow is scheduled rest.
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>

  <h2>Program</h2>
  <div class="cap" id="rotLine">
    {#if !prog.days.length}
      No program synced yet, split show in chat is the source.
    {:else}
      {prog.rotLine}
      <a href="#/program" id="progLink">Full split</a> ·
      <a href="#/lifts">Movements</a> ·
      <a href="#/muscles">Muscles</a>.
    {/if}
  </div>

  <h2>Forward</h2>
  <div class="card future futurebg">
    <div class="goalgrid" id="goalGrid">
      {#each goals as g}
        {@const ex = String(g['exercise'] || '')}
        {@const acts = ((g['actuals'] || []) as Array<{ date: string; e1rm: number }>).map(a => ({
          date: a.date,
          ev: a.e1rm,
        }))}
        {@const cps = (g['checkpoints'] || []) as number[]}
        {@const pct = goalPercent({
          target_e1rm: Number(g['target_e1rm']),
          checkpoints: cps,
          actuals: acts,
        })}
        {@const nextCp = g['next_checkpoint'] as number | null | undefined}
        {@const onTrack = g['on_track'] as boolean | undefined}
        {@const slippage = g['slippage'] as boolean | undefined}
        <div class="goalcard card future" style="margin: 0">
          <h3><a href="#/l/{encodeURIComponent(ex)}">{ex}</a></h3>
          <GoalChartView actuals={acts} checkpoints={cps} exercise={ex} />
          <div class="goalmeta">
            target e1RM {fmtV(Number(g['target_e1rm']))} by {fmtD(String(g['deadline']))} |
            {nextCp !== null && nextCp !== undefined
              ? 'next checkpoint ' + fmtV(nextCp)
              : 'trajectory complete'}
            {#if pct !== null}| {pct}% there{#if onTrack === false}, off track{/if}{/if}
            {#if onTrack === false}| OFF TRACK{/if}
            {#if slippage}| slippage: deadline needs room{/if}
          </div>
        </div>
      {/each}
    </div>
    <div class="empty" id="goalEmpty" hidden={goals.length > 0}>
      no active goals, trajectories appear here once set in chat
    </div>
    <h2>Progression</h2>
    <table id="progTable">
      <thead>
        <tr><th>lift</th><th>verdict</th><th>next target</th><th>dir</th></tr>
      </thead>
      <tbody>
        {#if !progEntries.length}
          <tr><td colspan="4">no progression written yet, set at session end in chat</td></tr>
        {:else}
          {#each progEntries as ex}
            {@const p = snap.progression[ex] as {
              verdict?: string;
              next?: string;
              direction?: string;
            }}
            <tr>
              <td><a href="#/l/{encodeURIComponent(ex)}">{ex}</a></td>
              <td
                style:color={p.verdict === 'hit'
                  ? '#7fd67f'
                  : p.verdict === 'miss'
                    ? '#f09090'
                    : '#b0aca2'}
                style:font-weight="600">{p.verdict}</td
              >
              <td>{p.next}</td>
              <td
                title={p.direction}
                style:color={p.direction === 'up'
                  ? '#7fd67f'
                  : p.direction === 'down'
                    ? '#f09090'
                    : '#8a8478'}
                style:font-weight="600"
                >{p.direction === 'up' ? '↗' : p.direction === 'down' ? '↘' : '→'}</td
              >
            </tr>
          {/each}
        {/if}
      </tbody>
    </table>
    <div class="cap">
      Dashed cards are future: checkpoints, next targets, hollow points. Solid lines are logged
      sets.
    </div>
  </div>

  <h2>Best sets</h2>
  <div class="card">
    <table id="prs">
      <thead>
        <tr><th>lift</th><th>best set by e1RM</th><th>date</th></tr>
      </thead>
      <tbody>
        {#each bestSetRows(snap) as row}
          <tr>
            <td><a href="#/l/{encodeURIComponent(row.lift)}">{row.lift}</a></td>
            <td>{row.detail}</td>
            <td>{row.date}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>
