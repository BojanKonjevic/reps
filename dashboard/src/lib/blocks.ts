// Selection of the block views emitted by Reps. Global records are kept on each lift.
import type { BlockView, Snapshot } from '../generated/snapshot';

export function scopeToBlock(snap: Snapshot, block: BlockView): Snapshot {
  const within = (date: string) =>
    date >= block.start_date && date <= (block.end_date ?? snap.as_of);
  return {
    ...snap,
    lifts: snap.lifts.map(lift => ({
      ...lift,
      sessions: lift.sessions.filter(s => within(s.date)),
      progression: block.end_date ? null : lift.progression,
      tags: block.end_date ? [] : lift.tags,
      marks: block.end_date ? [] : lift.marks,
    })),
    muscles: block.muscles,
    sessions: snap.sessions.filter(s => within(s.date)),
    calendar: snap.calendar.filter(day => within(day.date)),
    volume_history: block.volume_history,
    rotation_volume: block.rotation_volume,
    bodyweight: block.bodyweight,
    adherence: block.adherence,
    history: snap.history.filter(event => within(event.date)),
    recent_notes: snap.recent_notes.filter(n => within(n.date)),
    goals: snap.goals
      .map(goal => ({ ...goal, actuals: goal.actuals.filter(point => within(point.date)) }))
      .filter(goal => !block.end_date || goal.actuals.length > 0),
  };
}
