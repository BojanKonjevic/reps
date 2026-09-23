<script lang="ts">
  import { onMount } from 'svelte';
  import { e1rm, fmtD, fmtV } from '../utils';
  import { liftColor } from '../charts';
  import { goalPercent, parseNextTarget } from '../forward';
  import type { Snapshot } from '../schemas/snapshot';
  import { musclesOf, notesOf, prData, topSetOn } from '../lib/dashboard';
  import LiftDetailChart from '../components/LiftDetailChart.svelte';
  import GoalChartView from '../components/GoalChartView.svelte';
  import type { LiftPoint } from '../liftChart';

  interface Props {
    snap: Snapshot;
    exercise: string;
  }

  let { snap, exercise: ex }: Props = $props();

  const wdate = $derived.by(() => {
    const m: Record<number, string> = {};
    for (const w of snap.workouts) m[w.id] = w.date;
    return m;
  });

  const sets = $derived(snap.sets.filter(s => s.exercise === ex));
  const trained = $derived(musclesOf(snap, ex));
  const setup = $derived(notesOf(snap, ex));
  const pr = $derived(prData(snap));

  const pts = $derived.by((): LiftPoint[] => {
    const byDate: Record<string, typeof sets> = {};
    sets.forEach(s => {
      const d = wdate[s.workout_id];
      if (d) (byDate[d] = byDate[d] || []).push(s);
    });
    return Object.keys(byDate)
      .sort()
      .map(d => {
        const top = byDate[d].slice().sort((a, b) => b.weight - a.weight || b.reps - a.reps)[0];
        return {
          date: d,
          w: top.weight,
          r: top.reps,
          ev: e1rm(top.weight, top.reps),
          pr: byDate[d].some(s => pr.prIds.has(s.id)),
        };
      });
  });

  const prog = $derived(
    snap.progression[ex.toLowerCase()] as
      { verdict?: string; next?: string; direction?: string } | undefined
  );
  const progNext = $derived(prog?.next ? parseNextTarget(prog.next) : null);

  const sub = $derived.by(() => {
    if (!sets.length) return 'never logged';
    const best = pts.slice().sort((a, b) => b.ev - a.ev)[0];
    return (
      'best ' +
      best.w +
      ' x ' +
      best.r +
      ' (e1RM ' +
      best.ev.toFixed(1) +
      ') on ' +
      fmtD(best.date) +
      (prog ? ' | progression ' + prog.verdict + ', next ' + prog.next + ' ' + prog.direction : '')
    );
  });

  const goal = $derived.by(() => {
    const hit = snap.goals.filter(
      g => String(g['exercise'] || '').toLowerCase() === ex.toLowerCase()
    );
    return hit.length ? hit[0] : null;
  });

  const goalActs = $derived(
    (((goal?.['actuals'] || []) as Array<{ date: string; e1rm: number }>) || []).map(a => ({
      date: a.date,
      ev: a.e1rm,
    }))
  );
  const goalCps = $derived((goal?.['checkpoints'] || []) as number[]);
  const goalTops = $derived.by(() => {
    const tops: Record<string, { w: number; r: number }> = {};
    goalActs.forEach(a => {
      const top = topSetOn(snap.sets, wdate, ex, a.date);
      if (top) tops[a.date] = top;
    });
    return tops;
  });
  const goalPct = $derived(
    goal
      ? goalPercent({
          target_e1rm: Number(goal['target_e1rm']),
          checkpoints: goalCps,
          actuals: goalActs,
        })
      : null
  );
  const goalCap = $derived.by(() => {
    if (!goal) return '';
    const nextCp = goal['next_checkpoint'] as number | null | undefined;
    return (
      'Target e1RM ' +
      fmtV(Number(goal['target_e1rm'])) +
      ' by ' +
      fmtD(String(goal['deadline'])) +
      (goalPct !== null ? ', ' + goalPct + '% there' : '') +
      (nextCp !== null && nextCp !== undefined
        ? ', next checkpoint ' + fmtV(nextCp)
        : ', trajectory complete') +
      (goal['on_track'] === false ? ', OFF TRACK' : '') +
      (goal['slippage'] ? ', slippage: deadline needs room' : '') +
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
    const order = snap.sets
      .slice()
      .sort((a, b) => (a.created < b.created ? -1 : a.created > b.created ? 1 : a.id - b.id));
    const out: PrItem[] = [];
    let seen = false;
    let top = 0;
    order.forEach(s => {
      if (s.exercise !== ex) return;
      const ev = e1rm(s.weight, s.reps);
      if (!seen) {
        seen = true;
        top = ev;
        return;
      }
      if (ev > top) {
        const jump = ev - top;
        top = ev;
        const d = wdate[s.workout_id];
        out.push({
          date: fmtD(d),
          detail: s.weight + ' x ' + s.reps + ' (e1RM ' + ev.toFixed(1) + ')',
          jump: '+' + jump.toFixed(1),
          link: '#/s/' + d,
        });
      }
    });
    return out;
  });

  const lastPR = $derived.by((): string | null => {
    let top = 0;
    let seen = false;
    let last: string | null = null;
    const order = snap.sets
      .slice()
      .sort((a, b) => (a.created < b.created ? -1 : a.created > b.created ? 1 : a.id - b.id));
    order.forEach(s => {
      if (s.exercise !== ex) return;
      const ev = e1rm(s.weight, s.reps);
      if (!seen) {
        seen = true;
        top = ev;
        return;
      }
      if (ev > top) {
        top = ev;
        last = wdate[s.workout_id];
      }
    });
    return last;
  });

  const prNote = $derived.by(() => {
    if (!lastPR) return 'no PR yet, the first logged set is the baseline';
    const days = Math.round(
      (new Date().getTime() - new Date(lastPR + 'T12:00:00').getTime()) / 86400000
    );
    return days <= 0 ? 'PR today' : 'last PR ' + days + 'd ago (' + fmtD(lastPR) + ')';
  });

  onMount(() => {
    document.title = ex;
    window.scrollTo(0, 0);
  });
</script>

<div class="wrap" id="viewLift">
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
  <h1 id="liftTitle">{ex}</h1>
  <div class="sub" id="liftSub">{sub}</div>
  <div class="muscles" id="liftMuscles" hidden={!trained.length}>
    {#each trained as m, i}
      {#if i > 0},
      {/if}<a href="#/m/{encodeURIComponent(m)}"><b>{m}</b></a>
    {/each}
  </div>
  <div class="card">
    <LiftDetailChart {pts} exercise={ex} futureEv={progNext ? progNext.ev : null} />
    <div class="cap">
      Best set e1RM per session. New highs are PRs. Tap a point to open the session. Hollow diamond
      marks the progression next target.
    </div>
  </div>
  {#if goal && goalCps.length}
    <div class="card future futurebg" id="liftGoalCard">
      <h2>Trajectory</h2>
      <GoalChartView
        id="chGoal"
        actuals={goalActs}
        checkpoints={goalCps}
        exercise={ex}
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
