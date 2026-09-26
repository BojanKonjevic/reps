<script lang="ts">
  import { onMount } from 'svelte';
  import { fmtD, fmtV } from '../lib/format';
  import { href } from '../routes';
  import type { Snapshot } from '../generated/snapshot';
  import { liftByName } from '../lib/select';
  import {
    chartMarks,
    coverageNote,
    defOf,
    eventsForGoal,
    eventsForLift,
    groupByDate,
    rangeBounds,
    ruleIdOf,
    scopeForLift,
    scopeOf,
    trajectoryLines,
  } from '../lib/temporal';
  import { createEventSelection } from '../lib/eventSelection.svelte';
  import { useHistoryStates } from '../queries/useHistoryStates.svelte';
  import { vocabOf } from '../lib/vocab.svelte';
  import PageHeader from '../components/PageHeader.svelte';
  import SectionHeader from '../components/SectionHeader.svelte';
  import LiftDetailChart from '../components/LiftDetailChart.svelte';
  import GoalChartView from '../components/GoalChartView.svelte';
  import EventStrip from '../components/EventStrip.svelte';
  import AsOfControl from '../components/AsOfControl.svelte';
  import AsOfPanel from '../components/AsOfPanel.svelte';
  import ChangeDetail from '../components/ChangeDetail.svelte';
  import Provenance from '../components/Provenance.svelte';
  import type { LiftPoint } from '../liftChart';

  interface Props {
    snap: Snapshot;
    exercise: string;
  }

  let { snap, exercise: ex }: Props = $props();

  const lift = $derived(liftByName(snap.lifts, ex));
  const vocab = $derived(vocabOf(snap));
  const trained = $derived(lift?.muscles ?? []);
  const setup = $derived(lift?.notes ?? []);

  const pts = $derived.by((): LiftPoint[] => {
    if (!lift) return [];
    return lift.sessions.map(s => ({
      date: s.date,
      w: s.weight,
      r: s.reps,
      ev: s.e1rm,
      pr: s.is_pr,
    }));
  });

  const prog = $derived(lift?.progression ?? null);

  const bestLine = $derived.by(() => {
    if (!lift || !lift.sessions.length) return 'never logged';
    const best = lift.best!;
    return (
      'best ' +
      best.weight +
      ' x ' +
      best.reps +
      ' · e1RM ' +
      best.e1rm.toFixed(1) +
      ' · ' +
      fmtD(best.date)
    );
  });

  const progLine = $derived.by(() => {
    if (!prog) return '';
    return prog.verdict + ', next ' + prog.next + ' ' + prog.direction;
  });

  const goal = $derived.by(() => {
    if (!lift?.goal_id) return null;
    return snap.goals.find(g => g.id === lift.goal_id) ?? null;
  });

  const goalActs = $derived((goal?.actuals ?? []).map(a => ({ date: a.date, ev: a.e1rm })));
  const goalCps = $derived(goal?.checkpoints ?? []);
  const goalTops = $derived.by(() => {
    const tops: Record<string, { w: number; r: number }> = {};
    for (const [d, t] of Object.entries(goal?.top_by_date ?? {}))
      tops[d] = { w: t.weight, r: t.reps };
    return tops;
  });
  const goalPct = $derived(goal?.percent ?? null);
  const goalCap = $derived.by(() => {
    if (!goal) return '';
    return (
      'Target e1RM ' +
      fmtV(goal.target_e1rm) +
      ' by ' +
      fmtD(goal.deadline) +
      (goalPct !== null ? ', ' + goalPct + '% there' : '') +
      (goal.next_checkpoint !== null && goal.next_checkpoint !== undefined
        ? ', next checkpoint ' + fmtV(goal.next_checkpoint)
        : ', trajectory complete') +
      (goal.on_track === false ? ', OFF TRACK' : '') +
      (goal.slippage ? ', slippage: deadline needs room' : '')
    );
  });

  interface PrItem {
    date: string;
    detail: string;
    jump: string;
    link: string;
  }

  const prItems = $derived.by((): PrItem[] => {
    if (!lift) return [];
    const out: PrItem[] = [];
    for (const s of lift.sessions) {
      if (!s.is_pr) continue;
      out.push({
        date: fmtD(s.date),
        detail: s.weight + ' x ' + s.reps + ' (e1RM ' + s.e1rm.toFixed(1) + ')',
        jump: '+' + (s.delta_e1rm ?? 0).toFixed(1),
        link: href.session(s.date),
      });
    }
    return out;
  });

  const prNote = $derived.by(() => {
    if (!lift) return 'never logged';
    if (lift.last_pr_date === null || lift.last_pr_date === undefined)
      return 'no PR yet, the first logged set is the baseline';
    const days = lift.days_since_pr ?? 0;
    return days <= 0 ? 'PR today' : 'last PR ' + days + 'd ago (' + fmtD(lift.last_pr_date) + ')';
  });

  const events = $derived(ex ? eventsForLift(snap, ex) : []);
  const groups = $derived(groupByDate(events));
  const marks = $derived(chartMarks(groups));
  const coverNote = $derived(coverageNote(events, lift?.sessions[0]?.date ?? null));
  const goalEvents = $derived(ex ? eventsForGoal(snap, ex) : []);
  const pageScope = $derived(
    ex ? scopeForLift(snap, ex) : { exercises: [], muscles: [], days: [] }
  );
  const bounds = $derived(rangeBounds(snap));

  const sel = createEventSelection();
  let asof: string | null = $state(null);
  const selected = $derived(events.find(e => e.id === sel.selId) ?? null);
  const statesQ = useHistoryStates(
    () => asof !== null,
    () => snap.exported
  );
  const panelScope = $derived(selected ? scopeOf(selected) : pageScope);
  const panelRule = $derived(selected ? ruleIdOf(selected) : null);

  function selectMark(date: string) {
    const hit = events.find(e => e.date === date);
    if (hit) sel.select(hit.id);
  }

  function toggleAsof(date: string) {
    asof = asof === date ? null : date;
  }

  onMount(() => {
    document.title = ex;
  });
</script>

<div id="viewLift">
  <div class="crumb"><a href={href.lifts()}>← Movements</a></div>
  <PageHeader title={ex} titleId="liftTitle" />
  <div class="liftmeta" id="liftSub">
    <span class="nextnum">{bestLine}</span>
    <span class="cap">{prNote}</span>
    {#if progLine}<span class="cap">{progLine}</span>{/if}
  </div>
  <div class="muscles" id="liftMuscles" hidden={!trained.length}>
    {#each trained as m, i}
      {#if i > 0},
      {/if}<a href={href.muscle(m)}><b>{m}</b></a>
    {/each}
  </div>
  <SectionHeader title="Estimated 1RM" />
  <div class="surface-flat">
    <LiftDetailChart
      {pts}
      color={vocab.liftColor(ex)}
      futureEv={prog ? prog.next_e1rm : null}
      asOf={snap.as_of}
      {marks}
      selDate={selected?.date ?? asof}
      onSelectMark={selectMark}
    />
    <div class="cap">
      Best set e1RM per session. New highs are PRs. Tap a point to open the session. Hollow diamond
      marks the progression next target. Ticks mark recorded training changes, tap one to inspect.
    </div>
    {#if coverNote}
      <div class="cap" id="liftHistNote">{coverNote}</div>
    {/if}
    <AsOfControl
      value={asof}
      min={bounds.min}
      max={bounds.max}
      eventDates={groups.map(g => g.date)}
      onPick={d => (asof = d)}
      id="liftAsof"
    />
    <EventStrip {groups} selectedId={sel.selId} onSelect={sel.select} id="liftEvents" />
    {#if selected}
      <ChangeDetail
        event={selected}
        events={snap.history}
        stateOpen={asof === selected.date}
        onViewState={toggleAsof}
        id="liftChange"
      />
    {/if}
    <AsOfPanel
      {snap}
      date={asof}
      scope={panelScope}
      ruleId={panelRule}
      states={statesQ.data?.states ?? null}
      loading={asof !== null && statesQ.isFetching}
      rangeMin={bounds.min}
      id="liftState"
    />
    <Provenance def={defOf(snap, 'lift_trend')} id="liftProv" />
  </div>
  {#if goal && goalCps.length}
    <div id="liftGoalCard">
      <SectionHeader title="Trajectory" sub={goalCap} />
      <div class="surface-flat">
        <GoalChartView
          id="chGoal"
          actuals={goalActs}
          checkpoints={goalCps}
          color={vocab.liftColor(ex)}
          tops={goalTops}
        />
        <div class="cap">Dashed line is the plan, hollow points are future.</div>
        {#if goalEvents.length}
          <div class="cap" id="liftGoalHist">Trajectory history</div>
          {#each goalEvents as ge}
            <div class="cap">{fmtD(ge.date)}: {trajectoryLines(ge).join('; ') || ge.summary}</div>
          {/each}
        {/if}
        <Provenance def={defOf(snap, 'goal_trajectory')} id="liftGoalProv" />
      </div>
    </div>
  {/if}
  {#if setup.length}
    <div id="liftSetupCard">
      <SectionHeader title="Setup" />
      <div class="notes" id="liftSetup">
        {#each setup as n}
          <div>{n}</div>
        {/each}
      </div>
    </div>
  {/if}
  <SectionHeader title="PR history" />
  <div id="liftPRs" class="surface-flat">
    {#each prItems as item}
      <a class="tl-item" href={item.link}>
        <div class="tl-date">{item.date}</div>
        <div class="tl-rail"></div>
        <div class="tl-what"><b>{item.detail}</b><span class="tl-delta">{item.jump}</span></div>
      </a>
    {/each}
  </div>
</div>

<style>
  .crumb {
    font-size: 12.5px;
    color: var(--ink-mute);
    margin-bottom: 8px;
  }
  .crumb a:hover {
    color: var(--ink);
  }
  .liftmeta {
    display: flex;
    gap: 8px 18px;
    flex-wrap: wrap;
    align-items: baseline;
    margin: -2px 0 4px;
  }
  .liftmeta .cap {
    margin-top: 0;
  }
</style>
