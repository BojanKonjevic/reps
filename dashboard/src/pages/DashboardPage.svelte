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
    statusLabel,
  } from '../lib/present';
  import { href } from '../routes';
  import type { Snapshot } from '../generated/snapshot';
  import {
    defOf,
    eventsForGoal,
    nearbyEvents,
    rangeBounds,
    recentChanges,
    rotOrder,
    ruleIdOf,
    scopeOf,
    selectStateForDate,
    trajectoryLines,
  } from '../lib/temporal';
  import { createEventSelection } from '../lib/eventSelection.svelte';
  import { useHistoryStates } from '../queries/useHistoryStates.svelte';
  import {
    bestSetRows,
    dayAvgs,
    rankLifts,
    statusLines,
    subLine,
    adherenceWeeksView,
  } from '../lib/dashboard';
  import { trendMatrix, liftByName, sessionSpans, latestE1rm, tagFacetsPass } from '../lib/select';
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
  import PageHeader from '../components/PageHeader.svelte';
  import SectionHeader from '../components/SectionHeader.svelte';
  import FacetChips from '../components/FacetChips.svelte';
  import TrendMini from '../components/TrendMini.svelte';
  import VolumeChart from '../components/VolumeChart.svelte';
  import BodyweightChart from '../components/BodyweightChart.svelte';
  import SessionLengthChart from '../components/SessionLengthChart.svelte';
  import GoalChartView from '../components/GoalChartView.svelte';
  import Calendar from '../components/Calendar.svelte';
  import ChangeDetail from '../components/ChangeDetail.svelte';
  import AsOfPanel from '../components/AsOfPanel.svelte';
  import Provenance from '../components/Provenance.svelte';

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
    const tags = new Set(liftByName(lifts, t)?.tags ?? []);
    return tagFacetsPass(tags, ui.trendFacets);
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

  const changed = $derived(recentChanges(snap, 5));
  const sel = createEventSelection();
  let asof: string | null = $state(null);
  const selected = $derived(changed.find(e => e.id === sel.selId) ?? null);
  const bounds = $derived(rangeBounds(snap));

  function toggleAsof(date: string) {
    asof = asof === date ? null : date;
  }

  let bwIdx: number | null = $state(null);
  const bwRow = $derived(bwIdx !== null ? (snap.bodyweight[bwIdx] ?? null) : null);
  const bwNear = $derived(bwRow ? nearbyEvents(snap, bwRow.date, 7) : []);

  function pickBw(i: number | null) {
    bwIdx = i === null || i === bwIdx ? null : i;
  }

  let adhDate: string | null = $state(null);
  const adhDay = $derived(adhDays.find(d => d.date === adhDate) ?? null);
  const adhContext = $derived(
    adhDate ? nearbyEvents(snap, adhDate, 30).filter(e => e.domain === 'rotation') : []
  );

  const statesQ = useHistoryStates(
    () => asof !== null || adhDate !== null,
    () => snap.exported
  );
  const states = $derived(statesQ.data?.states ?? null);
  const adhRotation = $derived.by((): string | null => {
    if (!adhDate || !states) return null;
    const bundle = selectStateForDate(states, adhDate);
    if (!bundle || !bundle.rotation_known || !bundle.rotation) return null;
    return rotOrder(bundle.rotation);
  });
</script>

<div id="viewDash">
  <div class="dashhead">
    <PageHeader title="Overview" sub={subLine(snap)} subId="sub" />
    {#if statusLines(snap).length}
      <div class="nowlines" id="nowLines">
        {#each statusLines(snap) as line}
          <div>
            {#each line as seg}
              {#if seg.b}<b>{seg.t}</b>{:else}{seg.t}{/if}
            {/each}
          </div>
        {/each}
      </div>
    {/if}
  </div>

  <div id="nextWrap">
    <SectionHeader title="Next up" sub={next.empty ? '' : (next.day ?? '')} />
    <div id="nextCard" class="surface-flat">
      {#if next.empty}
        <div class="empty">{next.empty}</div>
      {:else}
        <table class="nexttable" aria-label="Next training session">
          <thead>
            <tr>
              <th scope="col">Movement</th>
              <th scope="col">Last</th>
              <th scope="col">Target</th>
            </tr>
          </thead>
          <tbody>
            {#each next.rows as row}
              <tr class="nextline">
                <td><a class="nextmove" href={href.lift(row.movement)}>{row.movement}</a></td>
                <td class="nextnum">
                  {#if row.last}
                    {row.last.weight} x {row.last.reps}
                    <span class="nextmeta">{fmtD(row.last.date)}</span>
                  {:else}
                    never logged
                  {/if}
                </td>
                <td class="nexttarget">
                  {#if row.target}
                    target {row.target}
                  {:else}
                    —
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
        <div class="cap">{next.basis}</div>
      {/if}
    </div>
  </div>

  {#if snap.signals}
    <div id="sigWrap">
      <SectionHeader title="Coach notes" />
      <div id="sigCard" class="surface-flat">
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
    </div>
  {/if}

  {#if changed.length}
    <div id="changedWrap">
      <SectionHeader title="What changed" actionLabel="Full history" actionHref={href.history()} />
      <div id="changedCard" class="surface-flat">
        {#each changed as e}
          <div class="histrow">
            <div class="hhead">
              <span class="hdate">{fmtD(e.date)}</span>
              <button
                type="button"
                class="evbtn"
                onclick={() => sel.select(e.id)}
                aria-pressed={sel.selId === e.id}
              >
                <b>{e.title}</b>
              </button>
            </div>
            <div class="hsum">{e.summary}</div>
            {#if selected && selected.id === e.id}
              <ChangeDetail
                event={selected}
                events={snap.history}
                stateOpen={asof === selected.date}
                onViewState={toggleAsof}
              />
              <AsOfPanel
                {snap}
                date={asof}
                scope={scopeOf(selected)}
                ruleId={ruleIdOf(selected)}
                {states}
                loading={asof !== null && statesQ.isFetching}
                rangeMin={bounds.min}
              />
            {/if}
          </div>
        {/each}
      </div>
    </div>
  {/if}

  <div>
    <SectionHeader title="Estimated 1RM" sub="Best set per session, each lift on its own scale." />
    <div class="surface-flat">
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
                <span class="minivalue">{latestE1rm(lifts, lift.exercise)}</span>
              </div>
              {#if lift.marks.length}
                <div>
                  {#each lift.marks as m}
                    <span class="minisub {markClass(m.kind)}">{markText(m.kind)}</span>
                  {/each}
                </div>
              {/if}
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
      <Provenance def={defOf(snap, 'lift_trend')} id="trendProv" />
    </div>
  </div>

  <div class="cols2">
    <div>
      <SectionHeader
        title="Weekly volume"
        sub="By muscle. One set can count for several muscles."
      />
      <div class="surface-flat">
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
              class:focus={focus.has(g.toLowerCase())}
              class:dim={deprio.has(g.toLowerCase())}
            >
              <span class="sw" style:background={vocab.colors[g]}></span>{g}
            </a>
          {/each}
        </div>
        <Provenance def={defOf(snap, 'muscle_volume')} id="volProv" />
      </div>
      <SectionHeader title="Bodyweight" sub="Gym scale weigh ins, as logged in chat." />
      <div class="surface-flat">
        <BodyweightChart rows={snap.bodyweight} onSelect={pickBw} />
        <div class="cap">
          Dashed spans are gaps, not measurements. Thin line is the 7-day average. Tap a point to
          see what else was happening around then.
        </div>
        {#if bwRow}
          <div class="daydetail" id="bwNear">
            <b>Around {fmtD(bwRow.date)}</b>
            {#each bwNear as e}
              <div>{fmtD(e.date)} · <b>{e.title}</b> · {e.summary}</div>
            {:else}
              <div>no recorded training changes within a week of this weigh in</div>
            {/each}
            {#if bwNear.length}
              <div class="cap"><a href={href.history()}>Full history</a></div>
            {/if}
          </div>
        {/if}
        <Provenance def={defOf(snap, 'bodyweight_trend')} id="bwProv" />
      </div>
    </div>
    <div>
      <SectionHeader title="Training calendar" />
      <div class="surface-flat calcard">
        <Calendar days={snap.calendar} />
        <ul class="notes" id="noteList">
          {#each snap.recent_notes as n}
            <li class:hot={n.hot}>
              <a href={href.session(n.date)}>{n.text}</a>
            </li>
          {/each}
        </ul>
      </div>
      <SectionHeader title="Session length" sub="First set to last set." />
      <div class="surface-flat" id="sessLenWrap">
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
      </div>
      {#if adhDays.length}
        <div id="adhWrap">
          <SectionHeader title="Consistency" />
          <div class="surface-flat" id="adhCard">
            <div class="dtstrip">
              {#each adhDays as d}
                <button
                  type="button"
                  class="dt dt-{d.status.replace('_', '')}"
                  class:sel={adhDate === d.date}
                  title="{d.date}: {d.status} (expected {d.expected})"
                  aria-label="{d.date}: {statusLabel(d.status)}, expected {d.expected}"
                  aria-pressed={adhDate === d.date}
                  onclick={() => (adhDate = adhDate === d.date ? null : d.date)}
                ></button>
              {/each}
            </div>
            {#if adhDay}
              <div class="daydetail" id="adhDetail">
                <b>{fmtD(adhDay.date)}</b>
                <div>Expected: {adhDay.expected}</div>
                <div>Actual: {adhDay.trained ?? 'nothing logged'}</div>
                <div>Status: {statusLabel(adhDay.status)}</div>
                {#if adhRotation}
                  <div>Rotation at this time: {adhRotation}</div>
                {:else if adhDate && statesQ.isFetching}
                  <div>Rotation at this time: loading…</div>
                {:else if adhDate && bounds.min && adhDate < bounds.min}
                  <div>Rotation at this time: unavailable before {fmtD(bounds.min)}.</div>
                {/if}
                {#each adhContext as e}
                  <div>{fmtD(e.date)} · <b>{e.title}</b> · {e.summary}</div>
                {/each}
              </div>
            {/if}
            <div class="adhweeks">
              {#each adhWeeks as w}
                <div>{w.week_start} · {w.trained}/{w.expected} sessions</div>
              {/each}
            </div>
            <div class="cap">
              Green is trained as planned, red is missed, hollow is scheduled rest.
            </div>
            <Provenance def={defOf(snap, 'adherence_summary')} id="adhProv" />
          </div>
        </div>
      {/if}
    </div>
  </div>

  <SectionHeader title="Forward" sub="Checkpoints, next targets, hollow points are future." />
  <div class="surface-flat">
    <div class="goalgrid" id="goalGrid">
      {#each goals as g}
        {@const acts = g.actuals.map(a => ({ date: a.date, ev: a.e1rm }))}
        <div class="goalcard">
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
          {#each eventsForGoal(snap, g.exercise) as ge}
            <div class="cap">{fmtD(ge.date)}: {trajectoryLines(ge).join('; ') || ge.summary}</div>
          {/each}
        </div>
      {/each}
    </div>
    <div class="empty" id="goalEmpty" hidden={goals.length > 0}>
      no active goals, trajectories appear here once set in chat
    </div>
    <SectionHeader title="Progression" />
    <table id="progTable">
      <thead>
        <tr
          ><th scope="col">lift</th><th scope="col">verdict</th><th scope="col">next target</th><th
            scope="col">dir</th
          ></tr
        >
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
              <td class="num">{lift.progression!.next}</td>
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
    <Provenance def={defOf(snap, 'goal_trajectory')} id="goalProv" />
  </div>

  <SectionHeader title="Best sets" />
  <div class="surface-flat">
    <table id="prs">
      <thead>
        <tr
          ><th scope="col">lift</th><th scope="col">best set by e1RM</th><th scope="col">date</th
          ></tr
        >
      </thead>
      <tbody>
        {#each bestSetRows(snap) as row}
          <tr>
            <td><a href={href.lift(row.lift)}>{row.lift}</a></td>
            <td class="num">{row.detail}</td>
            <td class="num">{row.date}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>
