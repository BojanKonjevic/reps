<script lang="ts">
  import { onMount } from 'svelte';
  import { dayColor, liftColor } from '../charts';
  import { fmtD, fmtMin, fmtV } from '../lib/format';
  import {
    verdictClass,
    directionArrow,
    directionClass,
    markText,
    markClass,
  } from '../lib/present';
  import { href } from '../routes';
  import type { Snapshot } from '../generated/snapshot';
  import {
    bestSetRows,
    dayAvgs,
    rankLifts,
    statusLines,
    subLine,
    adherenceWeeksView,
  } from '../lib/dashboard';
  import { trendMatrix, liftByName, sessionSpans } from '../lib/select';
  import { vocabOf } from '../lib/vocab.svelte';
  import {
    defaultHide,
    hideAllLifts,
    pruneHidden,
    resetTrend,
    showAllLifts,
    toggleHidden,
    ui,
  } from '../lib/filters.svelte';
  import PageShell from '../components/PageShell.svelte';
  import FacetChips from '../components/FacetChips.svelte';
  import TrendMini from '../components/TrendMini.svelte';
  import VolumeChart from '../components/VolumeChart.svelte';
  import BodyweightChart from '../components/BodyweightChart.svelte';
  import SessionLengthChart from '../components/SessionLengthChart.svelte';
  import GoalChartView from '../components/GoalChartView.svelte';
  import Calendar from '../components/Calendar.svelte';

  interface Props {
    snap: Snapshot;
  }

  let { snap }: Props = $props();

  const vocab = $derived(vocabOf(snap));
  const lifts = $derived(snap.lifts);
  const top = $derived(rankLifts(snap));
  const matrix = $derived(trendMatrix(lifts));

  let paintedStamp = $state('');
  $effect(() => {
    if (snap.exported !== paintedStamp) {
      paintedStamp = snap.exported;
      pruneHidden(top);
      defaultHide(top, snap.constants.thresholds.trend_top_lifts);
    }
  });

  onMount(() => {
    document.title = 'reps dashboard';
  });

  function passFilter(t: string): boolean {
    if (ui.trendQ && !t.toLowerCase().includes(ui.trendQ)) return false;
    if (!ui.trendFacets.size) return true;
    const lift = liftByName(lifts, t);
    const tags = new Set(lift?.tags ?? []);
    for (const f of ui.trendFacets) {
      if (f === 'goal' && tags.has('goal')) return true;
      if (f === 'stall' && (tags.has('stalling') || tags.has('slipping'))) return true;
      if (f === 'focus' && tags.has('focus')) return true;
    }
    return false;
  }

  const shown = $derived(
    top
      .map(t => liftByName(lifts, t)!)
      .filter(l => l && !ui.hidden.has(l.exercise) && passFilter(l.exercise))
  );

  const focus = $derived(
    new Set(snap.muscles.filter(m => m.tier === 'priority').map(m => m.muscle.toLowerCase()))
  );
  const deprio = $derived(
    new Set(snap.muscles.filter(m => m.tier === 'deprioritize').map(m => m.muscle.toLowerCase()))
  );
  const mevOf = (g: string) => vocab.bands(g).mev;

  const next = $derived(snap.next_up);
  const adhDays = $derived(snap.adherence?.days || []);
  const adhWeeks = $derived(adherenceWeeksView(snap));
  const goals = $derived(snap.goals);
  const spans = $derived(sessionSpans(snap.sessions));
  const sessPoints = $derived(
    spans.map(s => ({ date: s.date, minutes: s.minutes, day: s.day, color: dayColor(s.day) }))
  );
  const sessAvgs = $derived(dayAvgs(spans));
  const progLifts = $derived(
    lifts.filter(l => l.progression).sort((a, b) => (a.exercise < b.exercise ? -1 : 1))
  );
</script>

<PageShell>
  <div class="wrap" id="viewDash">
    <div class="toprow">
      <div>
        <h1>Training dashboard</h1>
        <div class="sub" id="sub">{subLine(snap)}</div>
      </div>
      <div class="nowlines" id="nowLines">
        {#each statusLines(snap) as line}
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
        {#if next.empty}
          <div class="empty">{next.empty}</div>
        {:else}
          <h3>Next up: {next.day}</h3>
          {#each next.rows as row}
            <div class="nextrow">
              <a href={href.lift(row.movement)}>{row.movement}</a>
              <span class="meta"
                >{row.last
                  ? 'last ' + row.last.weight + ' x ' + row.last.reps + ' · ' + fmtD(row.last.date)
                  : 'never logged'}{row.target
                  ? ' → target ' + row.target
                  : ' · no target yet'}</span
              >
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
            <FacetChips
              facets={[
                ['Goals', 'goal'],
                ['Stalling', 'stall'],
                ['Focus', 'focus'],
              ]}
              active={ui.trendFacets}
              onToggle={f => {
                if (ui.trendFacets.has(f)) ui.trendFacets.delete(f);
                else ui.trendFacets.add(f);
              }}
              onReset={resetTrend}
            />
          </span>
        </div>
        <div class="minigrid" id="trendGrid">
          {#if !shown.length}
            <div class="empty">no lifts match, adjust filters or use Reset</div>
          {:else}
            {#each shown as lift}
              {@const idx = matrix.top.indexOf(lift.exercise)}
              {@const vals = matrix.series[idx]}
              <div class="mini">
                <div class="minititle">
                  <a href={href.lift(lift.exercise)}>{lift.exercise}</a>
                  {#if lift.marks.length}
                    <span class="ministat">
                      {#each lift.marks as m}
                        <span class="minisub {markClass(m.kind)}">{markText(m.kind)}</span>
                      {/each}
                    </span>
                  {/if}
                </div>
                <a href={href.lift(lift.exercise)} aria-label={lift.exercise} style="display:block">
                  <TrendMini {lift} days={matrix.days} {vals} color={liftColor(lift.exercise)} />
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
            labels={snap.volume_history.week_starts}
            weeks={snap.volume_history.week_starts.map((_, i) => {
              const row: Record<string, number> = {};
              for (const [m, arr] of Object.entries(snap.volume_history.by_muscle))
                row[m] = arr[i] ?? 0;
              return row;
            })}
            groups={vocab.groups}
            colors={vocab.colors}
            {mevOf}
            onSelect={g => (location.hash = href.muscle(g))}
          />
          <div class="legend" id="legMus">
            {#each vocab.groups as g}
              <a
                href={href.muscle(g)}
                class:chip={true}
                class:focus={focus.has(g.toLowerCase())}
                class:dim={deprio.has(g.toLowerCase())}
              >
                <span class="sw" style:background={vocab.colors[g]}></span>{g}
              </a>
            {/each}
          </div>
          <div class="cap">One set can count for several muscles.</div>
        </div>
        <h2>Bodyweight</h2>
        <div class="card">
          <BodyweightChart rows={snap.bodyweight} />
          <div class="cap">
            Gym scale weigh ins, as logged in chat. Dashed spans are gaps, not measurements. Thin
            line is the 7-day average.
          </div>
        </div>
      </div>
      <div>
        <h2>Training calendar</h2>
        <div class="card calcard">
          <Calendar days={snap.calendar} />
          <ul class="notes" id="noteList">
            {#each snap.recent_notes as n}
              <li class:hot={n.hot}>
                <a href={href.session(n.date)}>{n.text}</a>
              </li>
            {/each}
          </ul>
        </div>
        <h2>Session length</h2>
        <div class="card" id="sessLenWrap">
          <SessionLengthChart points={sessPoints} />
          <div class="pielegend" id="sessLenLegend">
            {#each sessAvgs as a}
              <div class="row">
                <span class="sw" style:background={dayColor(a.day)}></span>
                <a href={href.program()}>{a.day}</a>
                <span class="meta">avg {fmtMin(a.avg)} · {a.n} session{a.n === 1 ? '' : 's'}</span>
              </div>
            {/each}
          </div>
          <div class="cap">First set to last set. Colors mark split days.</div>
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
                  <div>{w.week_start} · {w.trained}/{w.expected} sessions</div>
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

    <h2>Forward</h2>
    <div class="card future futurebg">
      <div class="goalgrid" id="goalGrid">
        {#each goals as g}
          {@const acts = g.actuals.map(a => ({ date: a.date, ev: a.e1rm }))}
          <div class="goalcard card future" style="margin: 0">
            <h3><a href={href.lift(g.exercise)}>{g.exercise}</a></h3>
            <GoalChartView
              actuals={acts}
              checkpoints={g.checkpoints}
              color={liftColor(g.exercise)}
              tops={Object.fromEntries(
                Object.entries(g.top_by_date).map(([d, t]) => [d, { w: t.weight, r: t.reps }])
              )}
            />
            <div class="goalmeta">
              target e1RM {fmtV(g.target_e1rm)} by {fmtD(g.deadline)} |
              {g.next_checkpoint !== null && g.next_checkpoint !== undefined
                ? 'next checkpoint ' + fmtV(g.next_checkpoint)
                : 'trajectory complete'}
              {#if g.percent !== null}| {g.percent}% there{/if}
              {#if g.on_track === false}| OFF TRACK{/if}
              {#if g.slippage}| slippage: deadline needs room{/if}
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
          {#if !progLifts.length}
            <tr><td colspan="4">no progression written yet, set at session end in chat</td></tr>
          {:else}
            {#each progLifts as lift}
              <tr>
                <td><a href={href.lift(lift.exercise)}>{lift.exercise}</a></td>
                <td class={verdictClass(lift.progression!.verdict)} style:font-weight="600"
                  >{lift.progression!.verdict}</td
                >
                <td>{lift.progression!.next}</td>
                <td
                  title={lift.progression!.direction}
                  class={directionClass(lift.progression!.direction)}
                  style:font-weight="600">{directionArrow(lift.progression!.direction)}</td
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
              <td><a href={href.lift(row.lift)}>{row.lift}</a></td>
              <td>{row.detail}</td>
              <td>{row.date}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>
</PageShell>
