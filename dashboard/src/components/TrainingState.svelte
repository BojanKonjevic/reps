<script lang="ts">
  // SSOT owner: as-of state presentation. Consumers: every annotated view.
  // Shared temporal primitive: as-of bundle with then/now comparison.
  import { fmtD } from '../lib/format';
  import { diffSlots, rotOrder, type EventScope } from '../lib/temporal';
  import type { HistoryState } from '../generated/historyStates';
  import type { Snapshot } from '../generated/snapshot';

  interface Props {
    histState: HistoryState;
    date: string;
    snap: Snapshot;
    scope: EventScope;
    ruleId?: number | null;
    id?: string;
  }

  let { histState: st, date, snap, scope, ruleId = null, id = undefined }: Props = $props();

  let compare = $state(false);

  const scoped = $derived(scope.exercises.length + scope.muscles.length + scope.days.length > 0);

  const nowRot = $derived(snap.program.rotation.join(' / ') || 'no rotation set');

  const dayNames = $derived.by((): string[] => {
    if (scope.days.length) return scope.days;
    const ex = new Set(scope.exercises.map(s => s.toLowerCase()));
    const hit = snap.program.days.filter(d =>
      d.slots.some(s => s.moves.some(m => ex.has(m.toLowerCase())))
    );
    if (hit.length) return hit.map(d => d.day);
    return scoped ? [] : st.program.map(d => d.day);
  });

  const goalEx = $derived.by((): string[] => {
    if (scope.exercises.length) return scope.exercises;
    return scoped ? [] : st.goals.map(g => g.exercise);
  });

  const priMus = $derived.by((): string[] => {
    if (scope.muscles.length) return scope.muscles;
    return st.priorities.filter(p => p.known).map(p => p.muscle);
  });

  const nowTier = (muscle: string): string =>
    snap.muscles.find(m => m.muscle.toLowerCase() === muscle.toLowerCase())?.tier ?? 'maintain';

  const nowGoal = (exercise: string) =>
    snap.goals.find(g => g.exercise.toLowerCase() === exercise.toLowerCase()) ?? null;

  const nowDay = (day: string) => snap.program.days.find(d => d.day === day) ?? null;

  const deloadScope = $derived.by(() => {
    const ex = new Set(scope.exercises.map(s => s.toLowerCase()));
    const dy = new Set(scope.days);
    if (!ex.size && !dy.size) return scoped ? [] : st.deloads;
    return st.deloads.filter(
      d =>
        (d.scope === 'lift' && d.subject !== null && ex.has(d.subject.toLowerCase())) ||
        (d.scope === 'slot' && d.subject !== null && dy.has(d.subject))
    );
  });

  const ruleScope = $derived.by(() => {
    if (ruleId === null || ruleId === undefined) return [];
    return st.rules.filter(r => r.rule_id === ruleId);
  });

  function unavailable(first: string | null): string {
    return first ? 'Historical state unavailable before ' + fmtD(first) + '.' : 'never recorded';
  }

  function goalThen(g: (typeof st.goals)[number]): string {
    if (!g.known) return unavailable(g.first_date);
    return (
      (g.target_e1rm ?? 'unset') +
      ' e1RM by ' +
      (g.deadline ? fmtD(g.deadline) : 'unset') +
      ' (' +
      (g.status ?? 'unset') +
      ')'
    );
  }

  function goalNow(exercise: string): string {
    const g = nowGoal(exercise);
    return g
      ? g.target_e1rm + ' e1RM by ' + fmtD(g.deadline) + ' (' + g.status + ')'
      : 'no active goal now';
  }

  const rotThen = $derived(st.rotation === null ? 'not recorded' : rotOrder(st.rotation));
  const anchorThen = $derived(
    st.anchor_known
      ? 'position ' + st.anchor_position + ' from ' + fmtD(st.anchor_date ?? '')
      : unavailable(st.anchor_first_date)
  );
  const anchorNow = $derived(
    snap.program.anchor
      ? 'position ' + snap.program.anchor.index + ' from ' + fmtD(snap.program.anchor.date)
      : 'no anchor set'
  );

  const partial = $derived.by(() => {
    if (st.program.some(d => !d.known)) return true;
    if (st.goals.some(g => !g.known)) return true;
    if (st.deloads.some(d => !d.known)) return true;
    if (st.rules.some(r => !r.known)) return true;
    if (!st.rotation_known && (st.rotation_first_date !== null || snap.program.rotation.length > 0))
      return true;
    if (!st.anchor_known && (st.anchor_first_date !== null || snap.program.anchor !== null))
      return true;
    return false;
  });

  const rotSame = $derived(
    st.rotation_known
      ? rotThen === nowRot
      : st.rotation_first_date === null && snap.program.rotation.length === 0
  );
  const anchSame = $derived(
    st.anchor_known
      ? anchorThen === anchorNow
      : st.anchor_first_date === null && snap.program.anchor === null
  );

  const noDiff = $derived.by(() => {
    // Compare-mode emptiness: every scoped section reads identical then/now.
    const days = dayNames.map(day => {
      const then = st.program.find(d => d.day === day);
      const now = nowDay(day);
      if (!then || !then.known || !now) return false;
      return diffSlots(then.slots, now.slots).every(d => !d.changed);
    });
    const goalsOk = goalEx.map(ex => {
      const then = st.goals.find(g => g.exercise === ex);
      if (!then) return !nowGoal(ex);
      return then.known && goalThen(then) === goalNow(ex);
    });
    const pris = priMus.map(mu => {
      const then = st.priorities.find(p => p.muscle === mu);
      return (
        !!then &&
        (then.tier ?? 'maintain') === nowTier(mu) &&
        (then.known || nowTier(mu) === 'maintain')
      );
    });
    const deloadsOk = deloadScope.map(d => {
      const now = snap.deload.find(r => r.scope === d.scope && r.subject === d.subject);
      if (!d.known) return !now;
      return (d.active ? 'active' : 'not active') === (now ? 'active' : 'not active');
    });
    return (
      days.every(Boolean) &&
      goalsOk.every(Boolean) &&
      pris.every(Boolean) &&
      deloadsOk.every(Boolean) &&
      rotSame &&
      anchSame
    );
  });
</script>

<div class="asof" {id}>
  <div class="asofhead">
    <span><b>Training state</b> <span class="meta">As of {fmtD(date)} · historical</span></span>
    <button type="button" class="evbtn" onclick={() => (compare = !compare)} aria-pressed={compare}>
      {compare ? 'Hide comparison' : 'Compare with today'}
    </button>
  </div>
  {#if partial}
    <div class="cap">Some training state could not be reconstructed for {fmtD(date)}.</div>
  {/if}
  {#if compare && noDiff}
    <div class="cap">No relevant changes since {fmtD(date)}.</div>
  {/if}

  {#each dayNames as day}
    {@const then = st.program.find(d => d.day === day)}
    {@const now = nowDay(day)}
    {@const diffs = then && then.known && now ? diffSlots(then.slots, now.slots) : []}
    {@const show = !compare || !then?.known || !now || diffs.some(d => d.changed)}
    {#if show}
      <div class="asofsec">
        <div class="cap">Program · {day}</div>
        {#if !then || !then.known}
          <div>{unavailable(then?.first_date ?? null)}</div>
        {:else if !compare}
          {#each then.slots as s}
            <div>{s.movements} · {s.sets} sets</div>
          {:else}
            <div>no slots recorded</div>
          {/each}
        {:else if !now}
          {#each then.slots as s}
            <div>{fmtD(date)}: {s.movements} · {s.sets} sets · today: day removed</div>
          {/each}
        {:else}
          {#each diffs.filter(d => d.changed) as d}
            <div>{fmtD(date)}: {d.then} · today: {d.now}</div>
          {/each}
        {/if}
      </div>
    {/if}
  {/each}

  {#each goalEx as ex}
    {@const then = st.goals.find(g => g.exercise === ex)}
    {@const hasNow = !!nowGoal(ex)}
    {@const now = goalNow(ex)}
    {@const t = then ? goalThen(then) : unavailable(null)}
    {@const show = (then || hasNow) && (!compare || t !== now)}
    {#if show}
      <div class="asofsec">
        <div class="cap">Goal · {ex}</div>
        {#if !compare}
          <div>{t}</div>
        {:else}
          <div>{fmtD(date)}: {t} · today: {now}</div>
        {/if}
      </div>
    {/if}
  {/each}

  {#each priMus as mu}
    {@const then = st.priorities.find(p => p.muscle === mu)}
    {@const t = then ? then.tier + (then.known ? '' : ' (default)') : 'maintain (default)'}
    {@const n = nowTier(mu)}
    {@const show =
      !compare || (then?.tier ?? 'maintain') !== n || (then && !then.known && n !== 'maintain')}
    {#if show}
      <div class="asofsec">
        <div class="cap">Priority · {mu}</div>
        {#if !compare}
          <div>{t}</div>
        {:else}
          <div>{fmtD(date)}: {t} · today: {n}</div>
        {/if}
      </div>
    {/if}
  {/each}

  {#if !compare || !rotSame}
    <div class="asofsec">
      <div class="cap">Rotation</div>
      {#if !compare}
        <div>{st.rotation_known ? rotThen : unavailable(st.rotation_first_date)}</div>
      {:else}
        <div>
          {fmtD(date)}: {st.rotation_known ? rotThen : unavailable(st.rotation_first_date)} · today:
          {nowRot}
        </div>
      {/if}
      {#if !compare}
        <div>Anchor: {anchorThen}</div>
      {:else if !anchSame}
        <div>Anchor: {fmtD(date)}: {anchorThen} · today: {anchorNow}</div>
      {/if}
    </div>
  {/if}

  {#each deloadScope as d}
    {@const now = snap.deload.find(r => r.scope === d.scope && r.subject === d.subject)}
    {@const t = !d.known ? unavailable(d.first_date) : d.active ? 'active' : 'not active'}
    {@const n = now ? 'active' : 'not active'}
    {@const show = !compare || t !== n}
    {#if show}
      <div class="asofsec">
        <div class="cap">Deload · {d.scope} {d.subject}</div>
        {#if !compare}
          <div>{t}</div>
        {:else}
          <div>{fmtD(date)}: {t} · today: {n}</div>
        {/if}
      </div>
    {/if}
  {/each}

  {#each ruleScope as r}
    {@const now = snap.rules.find(q => q.id === r.rule_id)}
    {@const t = r.known
      ? (r.text ?? '') + ' (' + (r.status ?? 'unset') + ')'
      : unavailable(r.first_date)}
    {@const n = now ? now.text + ' (' + now.status + ')' : 'gone now'}
    {@const show = !compare || t !== n}
    {#if show}
      <div class="asofsec">
        <div class="cap">Rule</div>
        {#if !compare}
          <div>{t}</div>
        {:else}
          <div>{fmtD(date)}: {t} · today: {n}</div>
        {/if}
      </div>
    {/if}
  {/each}
</div>
