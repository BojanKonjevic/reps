<script lang="ts">
  import { onMount } from 'svelte';
  import { fmtD, fmtV } from '../lib/format';
  import { href } from '../routes';
  import type { Snapshot } from '../generated/snapshot';
  import { liftByName } from '../lib/select';
  import { vocabOf } from '../lib/vocab.svelte';
  import PageShell from '../components/PageShell.svelte';
  import LiftDetailChart from '../components/LiftDetailChart.svelte';
  import GoalChartView from '../components/GoalChartView.svelte';
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

  const sub = $derived.by(() => {
    if (!lift || !lift.sessions.length) return 'never logged';
    const best = lift.best!;
    return (
      'best ' +
      best.weight +
      ' x ' +
      best.reps +
      ' (e1RM ' +
      best.e1rm.toFixed(1) +
      ') on ' +
      fmtD(best.date) +
      (prog ? ' | progression ' + prog.verdict + ', next ' + prog.next + ' ' + prog.direction : '')
    );
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
      (goal.slippage ? ', slippage: deadline needs room' : '') +
      '. Dashed line is the plan, hollow points are future.'
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

  onMount(() => {
    document.title = ex;
    window.scrollTo(0, 0);
  });
</script>

<PageShell back>
  <div class="wrap" id="viewLift">
    <h1 id="liftTitle">{ex}</h1>
    <div class="sub" id="liftSub">{sub}</div>
    <div class="muscles" id="liftMuscles" hidden={!trained.length}>
      {#each trained as m, i}
        {#if i > 0},
        {/if}<a href={href.muscle(m)}><b>{m}</b></a>
      {/each}
    </div>
    <div class="card">
      <LiftDetailChart
        {pts}
        color={vocab.liftColor(ex)}
        futureEv={prog ? prog.next_e1rm : null}
        asOf={snap.as_of}
      />
      <div class="cap">
        Best set e1RM per session. New highs are PRs. Tap a point to open the session. Hollow
        diamond marks the progression next target.
      </div>
    </div>
    {#if goal && goalCps.length}
      <div class="card future futurebg" id="liftGoalCard">
        <h2>Trajectory</h2>
        <GoalChartView
          id="chGoal"
          actuals={goalActs}
          checkpoints={goalCps}
          color={vocab.liftColor(ex)}
          tops={goalTops}
        />
        <div class="cap" id="liftGoalCap">{goalCap}</div>
      </div>
    {/if}
    {#if setup.length}
      <div class="card" id="liftSetupCard">
        <div class="cap">Setup</div>
        <div class="notes" id="liftSetup">
          {#each setup as n}
            <div>{n}</div>
          {/each}
        </div>
      </div>
    {/if}
    <h2>PR history</h2>
    <div id="liftPRs">
      <div class="cap">{prNote}</div>
      {#each prItems as item}
        <a class="tl-item" href={item.link}>
          <div class="tl-date">{item.date}</div>
          <div class="tl-rail"></div>
          <div class="tl-what"><b>{item.detail}</b><span class="tl-delta">{item.jump}</span></div>
        </a>
      {/each}
    </div>
  </div>
</PageShell>
