import { z } from 'zod';

// Runtime validation for the synchronized snapshot. Mirrors the Python
// SnapshotModel in reps/models.py: core fact collections are required,
// forward-evolved sections default so an older payload still parses where
// the dashboard renders null-safe. Unknown keys are stripped (tolerated,
// never trusted). Use the inferred Snapshot type downstream, never a
// parallel interface.

// Muscle entries stay partial-tolerant: the dashboard reads every bound
// with a fallback (stale payloads predate fields), while Python validates
// strictly before publication. Zod models what the dashboard can render.
const muscleEntrySchema = z.object({
  mev: z.number().optional(),
  mav: z.tuple([z.number(), z.number()]).nullable().optional(),
  mrv: z.number().nullable().optional(),
  freq: z.tuple([z.number(), z.number()]).optional(),
  tier: z.enum(['settled', 'contested', 'opinion']).optional(),
  source: z.string().optional(),
  color: z.string().optional(),
});

const constantsSchema = z.object({
  version: z.number().optional(),
  muscles: z.record(z.string(), muscleEntrySchema),
  untracked: z.array(z.string()).optional().default([]),
  rep_bands: z
    .array(z.object({ max_reps: z.number().nullable(), jump_pct: z.number().nullable() }))
    .optional()
    .default([]),
  thresholds: z.record(z.string(), z.number()).optional().default({}),
  explained_keywords: z.array(z.string()).optional().default([]),
  rep_scheme_default: z.array(z.number()).optional().default([3, 8]),
});

const workoutSchema = z.object({
  id: z.number(),
  date: z.string(),
  status: z.enum(['open', 'done', 'rest']),
  notes: z.string().optional().default(''),
});

const setSchema = z.object({
  id: z.number(),
  workout_id: z.number(),
  exercise: z.string(),
  weight: z.number(),
  reps: z.number(),
  note: z.string().optional().default(''),
  created: z.string().optional().default(''),
  muscles: z.string().optional().default(''),
});

const bodyweightSchema = z.object({
  id: z.number().optional(),
  date: z.string(),
  kg: z.number(),
  note: z.string().optional().default(''),
});

const splitRowSchema = z.object({
  day: z.string(),
  slot: z.number(),
  movements: z.string(),
  sets: z.number(),
});

const progressionSchema = z.object({
  verdict: z.enum(['hit', 'miss', 'hold', 'baseline']),
  next: z.string(),
  direction: z.enum(['up', 'flat', 'down']),
  workout_id: z.number(),
  note: z.string().optional().default(''),
});

const goalSchema = z.object({
  id: z.number(),
  exercise: z.string(),
  target_e1rm: z.number(),
  target_desc: z.string().optional().default(''),
  deadline: z.string(),
  status: z.string().optional(),
  created: z.string().optional(),
  checkpoints: z.array(z.number()).optional().default([]),
  actuals: z
    .array(z.object({ date: z.string(), e1rm: z.number() }))
    .optional()
    .default([]),
  next_checkpoint: z.number().nullable().optional(),
  remaining: z.number().optional(),
  on_track: z.boolean().optional(),
  slippage: z.boolean().optional(),
  consecutive_misses: z.number().optional(),
});

const prioritySchema = z.union([
  z.string(),
  z.object({
    tier: z.string(),
    since: z.string().optional(),
    until: z.string().nullable().optional(),
  }),
]);

const deloadSchema = z.object({
  id: z.number(),
  scope: z.enum(['lift', 'slot']),
  subject: z.string(),
  set_on: z.string(),
  cleared_on: z.string().nullable().optional(),
});

const ruleSchema = z.object({
  id: z.number(),
  subject: z.string(),
  text: z.string(),
  start_date: z.string().optional(),
  expiry: z.string().nullable().optional(),
  status: z.string().optional(),
  created: z.string().optional(),
  needs_confirm: z.boolean().optional(),
});

const flagSchema = z.object({
  id: z.number(),
  subject: z.string(),
  reason: z.string(),
  created: z.string(),
  consumed_at: z.string().nullable().optional(),
});

const mappingSchema = z.object({
  exercise: z.string(),
  muscles: z.string(),
  is_bodyweight_only: z.number(),
});

const movementNoteSchema = z.object({
  id: z.number().optional(),
  exercise: z.string(),
  note: z.string(),
  created: z.string().optional().default(''),
});

const autoregHoldSchema = z.object({
  id: z.number(),
  day: z.string(),
  movements: z.string(),
  action: z.string(),
  set_on: z.string(),
  hold_until: z.string(),
  reason: z.string().optional().default(''),
});

const autoregChangeSchema = z.object({
  id: z.number(),
  date: z.string(),
  action: z.string(),
  day: z.string(),
  slot: z.number(),
  before_movements: z.string(),
  before_sets: z.number(),
  after_movements: z.string(),
  after_sets: z.number(),
  evidence: z.string().optional().default(''),
  reverted_on: z.string().nullable().optional(),
});

const adherenceDaySchema = z.object({
  date: z.string(),
  expected: z.string(),
  trained: z.string().nullable().optional(),
  status: z.enum(['done', 'swapped', 'extra', 'rest_ok', 'rest_logged', 'missed']),
});
const adherenceSchema = z.object({
  anchor: z.object({ date: z.string(), index: z.number() }).nullable().optional(),
  days: z.array(adherenceDaySchema).optional().default([]),
  drift: z.boolean().optional().default(false),
  drift_days: z.number().optional().default(0),
  drift_threshold: z.number().optional().default(0),
});

const autoregSchema = z.object({
  permitted: z.boolean(),
  holds: z.array(autoregHoldSchema).optional().default([]),
  miss_streaks: z
    .array(z.object({ exercise: z.string(), streak: z.number() }))
    .optional()
    .default([]),
  drop_watch: z
    .array(z.object({ exercise: z.string(), drops_pct: z.array(z.number()) }))
    .optional()
    .default([]),
  grouped: z.record(z.string(), z.array(z.string())).optional().default({}),
  program_volume: z.record(z.string(), z.number()).optional().default({}),
});

const volumeEntrySchema = z.object({
  weekly: z.array(z.number()),
  mev: z.number(),
  mav: z.tuple([z.number(), z.number()]).nullable().optional(),
  mrv: z.number().nullable().optional(),
  freq: z.tuple([z.number(), z.number()]).nullable().optional(),
  status: z.string(),
});

export const snapshotSchema = z.object({
  exported: z.string(),
  workouts: z.array(workoutSchema),
  sets: z.array(setSchema),
  bodyweight: z.array(bodyweightSchema).optional().default([]),
  split_active: z.array(splitRowSchema).optional().default([]),
  rotation: z.array(z.string()).optional().default([]),
  constants: constantsSchema.nullable().optional(),
  progression: z.record(z.string(), progressionSchema).optional().default({}),
  goals: z.array(goalSchema).optional().default([]),
  priority: z.record(z.string(), prioritySchema).optional().default({}),
  deload: z.array(deloadSchema).optional().default([]),
  rules: z.array(ruleSchema).optional().default([]),
  flags: z.array(flagSchema).optional().default([]),
  mapping: z.array(mappingSchema).optional().default([]),
  movement_notes: z.array(movementNoteSchema).optional().default([]),
  adherence: adherenceSchema.nullable().optional(),
  signals: z.array(z.object({ severity: z.string(), text: z.string() })).optional(),
  autoreg: autoregSchema.nullable().optional(),
  autoreg_changes: z.array(autoregChangeSchema).optional().default([]),
  volume: z.record(z.string(), volumeEntrySchema).optional().default({}),
});

export type Snapshot = z.infer<typeof snapshotSchema>;
export type SnapWorkout = z.infer<typeof workoutSchema>;
export type SnapSet = z.infer<typeof setSchema>;
export type AdherenceDay = z.infer<typeof adherenceDaySchema>;
export type SnapGoal = z.infer<typeof goalSchema>;
export type SnapProgression = z.infer<typeof progressionSchema>;
export type SnapPriority = z.infer<typeof prioritySchema>;
export type SnapAutoregHold = z.infer<typeof autoregHoldSchema>;
export type SnapAutoregChange = z.infer<typeof autoregChangeSchema>;
