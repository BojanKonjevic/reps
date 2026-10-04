BEGIN TRANSACTION;
CREATE TABLE autoreg_changes (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN ('trim', 'swap', 'add')),
  day TEXT NOT NULL,
  slot INTEGER NOT NULL,
  before_movements TEXT NOT NULL,
  before_sets INTEGER NOT NULL,
  after_movements TEXT NOT NULL,
  after_sets INTEGER NOT NULL,
  evidence TEXT NOT NULL DEFAULT '',
  reverted_on TEXT
);
CREATE TABLE autoreg_holds (
  id INTEGER PRIMARY KEY,
  day TEXT NOT NULL,
  movements TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN ('trim', 'swap', 'add')),
  set_on TEXT NOT NULL,
  hold_until TEXT NOT NULL,
  reason TEXT NOT NULL DEFAULT ''
);
CREATE TABLE bodyweight (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  kg REAL NOT NULL,
  note TEXT NOT NULL DEFAULT ''
);
INSERT INTO "bodyweight" VALUES(1,'2026-09-23',79.8,'shoes shorts tank top');
INSERT INTO "bodyweight" VALUES(2,'2026-09-24',78.6,'');
INSERT INTO "bodyweight" VALUES(3,'2026-09-26',79.3,'');
INSERT INTO "bodyweight" VALUES(4,'2026-09-27',78.6,'');
INSERT INTO "bodyweight" VALUES(5,'2026-09-28',78.9,'');
INSERT INTO "bodyweight" VALUES(6,'2026-09-30',79.4,'');
INSERT INTO "bodyweight" VALUES(7,'2026-10-01',79.4,'');
INSERT INTO "bodyweight" VALUES(8,'2026-10-02',79.9,'gym scale, shoes shorts tank');
CREATE TABLE compaction (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  last_compacted TEXT NULL,
  postponed_until TEXT NULL
);
INSERT INTO "compaction" VALUES(1,'Oct 2 2026','2026-10-01');
CREATE TABLE deload_state (
  id INTEGER PRIMARY KEY,
  scope TEXT NOT NULL CHECK (scope IN ('lift', 'slot')),
  subject TEXT NOT NULL,
  set_on TEXT NOT NULL,
  cleared_on TEXT
);
CREATE TABLE flags (
  id INTEGER PRIMARY KEY,
  subject TEXT NOT NULL,
  reason TEXT NOT NULL,
  created TEXT NOT NULL,
  consumed_at TEXT
);
CREATE TABLE goal_checkpoints (
  goal_id INTEGER NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
  session_no INTEGER NOT NULL,
  target_e1rm REAL NOT NULL,
  PRIMARY KEY (goal_id, session_no)
);
CREATE TABLE goals (
  id INTEGER PRIMARY KEY,
  exercise TEXT NOT NULL REFERENCES lift(exercise) ON UPDATE CASCADE,
  target_e1rm REAL NOT NULL,
  target_desc TEXT NOT NULL,
  deadline TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'dropped', 'done')),
  created TEXT NOT NULL
);
CREATE TABLE lift (
  exercise TEXT PRIMARY KEY,
  is_bodyweight_only INTEGER NOT NULL CHECK (is_bodyweight_only IN (0, 1))
);
INSERT INTO "lift" VALUES('adductor machine',0);
INSERT INTO "lift" VALUES('back squat',0);
INSERT INTO "lift" VALUES('bayesian curl',0);
INSERT INTO "lift" VALUES('cable crunch',0);
INSERT INTO "lift" VALUES('cable lat raise',0);
INSERT INTO "lift" VALUES('cable pullover',0);
INSERT INTO "lift" VALUES('cable pushdown',0);
INSERT INTO "lift" VALUES('cable reverse curl',0);
INSERT INTO "lift" VALUES('cable wrist curl',0);
INSERT INTO "lift" VALUES('cable wrist extension',0);
INSERT INTO "lift" VALUES('crunch machine',0);
INSERT INTO "lift" VALUES('dips',0);
INSERT INTO "lift" VALUES('dumbbell lat raise',0);
INSERT INTO "lift" VALUES('ezbar curl',0);
INSERT INTO "lift" VALUES('ezbar skullcrusher',0);
INSERT INTO "lift" VALUES('face pull',0);
INSERT INTO "lift" VALUES('flat barbell bench press',0);
INSERT INTO "lift" VALUES('hack squat',0);
INSERT INTO "lift" VALUES('hammer strength press',0);
INSERT INTO "lift" VALUES('hammer strength row',0);
INSERT INTO "lift" VALUES('hanging leg raise',1);
INSERT INTO "lift" VALUES('incline barbell bench press',0);
INSERT INTO "lift" VALUES('incline dumbbell curl',0);
INSERT INTO "lift" VALUES('leg extension',0);
INSERT INTO "lift" VALUES('leg press',0);
INSERT INTO "lift" VALUES('lying leg curl',0);
INSERT INTO "lift" VALUES('machine lat raise',0);
INSERT INTO "lift" VALUES('machine preacher curl',0);
INSERT INTO "lift" VALUES('overhead cable extension',0);
INSERT INTO "lift" VALUES('pec deck',0);
INSERT INTO "lift" VALUES('rdl',0);
INSERT INTO "lift" VALUES('rear delt cable fly',0);
INSERT INTO "lift" VALUES('reverse-grip smith incline press',0);
INSERT INTO "lift" VALUES('rope hammer curl',0);
INSERT INTO "lift" VALUES('seated leg curl',0);
INSERT INTO "lift" VALUES('smith jm press',0);
INSERT INTO "lift" VALUES('straight bar pulldown',0);
INSERT INTO "lift" VALUES('unilateral cable pushdown',0);
INSERT INTO "lift" VALUES('dumbbell reverse curl',0);
INSERT INTO "lift" VALUES('bench',0);
CREATE TABLE lift_muscle (
  exercise TEXT NOT NULL REFERENCES lift(exercise) ON UPDATE CASCADE ON DELETE CASCADE,
  muscle TEXT NOT NULL,
  PRIMARY KEY (exercise, muscle)
);
INSERT INTO "lift_muscle" VALUES('back squat','quads');
INSERT INTO "lift_muscle" VALUES('back squat','glutes');
INSERT INTO "lift_muscle" VALUES('dips','triceps');
INSERT INTO "lift_muscle" VALUES('flat barbell bench press','chest');
INSERT INTO "lift_muscle" VALUES('flat barbell bench press','front delts');
INSERT INTO "lift_muscle" VALUES('incline barbell bench press','chest');
INSERT INTO "lift_muscle" VALUES('incline barbell bench press','front delts');
INSERT INTO "lift_muscle" VALUES('reverse-grip smith incline press','chest');
INSERT INTO "lift_muscle" VALUES('hammer strength press','chest');
INSERT INTO "lift_muscle" VALUES('pec deck','chest');
INSERT INTO "lift_muscle" VALUES('hammer strength row','back');
INSERT INTO "lift_muscle" VALUES('straight bar pulldown','back');
INSERT INTO "lift_muscle" VALUES('cable pullover','back');
INSERT INTO "lift_muscle" VALUES('face pull','rear delts');
INSERT INTO "lift_muscle" VALUES('cable lat raise','side delts');
INSERT INTO "lift_muscle" VALUES('machine lat raise','side delts');
INSERT INTO "lift_muscle" VALUES('hack squat','quads');
INSERT INTO "lift_muscle" VALUES('leg press','quads');
INSERT INTO "lift_muscle" VALUES('leg press','glutes');
INSERT INTO "lift_muscle" VALUES('rdl','hamstrings');
INSERT INTO "lift_muscle" VALUES('rdl','glutes');
INSERT INTO "lift_muscle" VALUES('leg extension','quads');
INSERT INTO "lift_muscle" VALUES('seated leg curl','hamstrings');
INSERT INTO "lift_muscle" VALUES('lying leg curl','hamstrings');
INSERT INTO "lift_muscle" VALUES('adductor machine','adductors');
INSERT INTO "lift_muscle" VALUES('crunch machine','abs');
INSERT INTO "lift_muscle" VALUES('bayesian curl','biceps');
INSERT INTO "lift_muscle" VALUES('ezbar curl','biceps');
INSERT INTO "lift_muscle" VALUES('incline dumbbell curl','biceps');
INSERT INTO "lift_muscle" VALUES('rope hammer curl','biceps');
INSERT INTO "lift_muscle" VALUES('rope hammer curl','forearms');
INSERT INTO "lift_muscle" VALUES('cable reverse curl','forearms');
INSERT INTO "lift_muscle" VALUES('cable pushdown','triceps');
INSERT INTO "lift_muscle" VALUES('unilateral cable pushdown','triceps');
INSERT INTO "lift_muscle" VALUES('ezbar skullcrusher','triceps');
INSERT INTO "lift_muscle" VALUES('cable wrist curl','forearms');
INSERT INTO "lift_muscle" VALUES('cable wrist extension','forearms');
INSERT INTO "lift_muscle" VALUES('dumbbell lat raise','side delts');
INSERT INTO "lift_muscle" VALUES('smith jm press','triceps');
INSERT INTO "lift_muscle" VALUES('overhead cable extension','triceps');
INSERT INTO "lift_muscle" VALUES('hanging leg raise','abs');
INSERT INTO "lift_muscle" VALUES('rear delt cable fly','rear delts');
INSERT INTO "lift_muscle" VALUES('machine preacher curl','biceps');
INSERT INTO "lift_muscle" VALUES('cable crunch','abs');
INSERT INTO "lift_muscle" VALUES('dumbbell reverse curl','forearms');
INSERT INTO "lift_muscle" VALUES('bench','chest');
CREATE TABLE movement_note (
  id INTEGER PRIMARY KEY,
  exercise TEXT NOT NULL REFERENCES lift(exercise) ON UPDATE CASCADE,
  note TEXT NOT NULL,
  created TEXT NOT NULL
);
INSERT INTO "movement_note" VALUES(1,'dips','my form, elbows tucked, triceps main','2026-09-20T15:14:08');
INSERT INTO "movement_note" VALUES(2,'flat barbell bench press','triceps excluded by convention','2026-09-20T15:14:08');
INSERT INTO "movement_note" VALUES(3,'reverse-grip smith incline press','upper chest emphasis','2026-09-20T15:14:08');
INSERT INTO "movement_note" VALUES(5,'hammer strength row','logged as total both sides (45 per side = 90)','2026-09-20T15:14:08');
INSERT INTO "movement_note" VALUES(6,'straight bar pulldown','attachment matters','2026-09-20T15:14:08');
INSERT INTO "movement_note" VALUES(7,'straight bar pulldown','stack jumps 10kg: 47, 57, 67, 77, 87, 97, 107, 117, 127','2026-09-20T15:14:08');
INSERT INTO "movement_note" VALUES(8,'cable lat raise','stack micro-increments .625, all cable stacks share this','2026-09-22T09:19:36');
INSERT INTO "movement_note" VALUES(9,'machine lat raise','2.5kg increments','2026-09-22T09:39:04');
INSERT INTO "movement_note" VALUES(10,'smith jm press','bench 2 incline','2026-09-22T10:21:15');
INSERT INTO "movement_note" VALUES(11,'overhead cable extension','cable just under height 8','2026-09-22T10:27:37');
INSERT INTO "movement_note" VALUES(12,'seated leg curl','stack steps: 50 57 63 70 77 84 90 97 (6-7 increments)','2026-09-23T08:39:43');
INSERT INTO "movement_note" VALUES(13,'adductor machine','width setting 7','2026-09-23T08:49:04');
INSERT INTO "movement_note" VALUES(14,'adductor machine','stack increments 3.75','2026-09-23T08:50:46');
INSERT INTO "movement_note" VALUES(15,'crunch machine','single loading horn, starter unknown, logged weight is plates only; seat height middle (unnumbered)','2026-09-23T09:01:31');
INSERT INTO "movement_note" VALUES(16,'cable reverse curl','bilateral','2026-09-23T09:39:08');
INSERT INTO "movement_note" VALUES(17,'cable wrist curl','unilateral, log weaker side with L/R when sides diverge','2026-09-23T09:39:08');
INSERT INTO "movement_note" VALUES(18,'reverse-grip smith incline press','incline 2','2026-09-24T09:36:23');
INSERT INTO "movement_note" VALUES(19,'incline dumbbell curl','incline 4','2026-09-24T09:58:14');
INSERT INTO "movement_note" VALUES(20,'machine preacher curl','stack 5,10,15,20,25,32,39,46,53,60,67 plus 2 unmarked micros at top','2026-09-24T10:07:12');
INSERT INTO "movement_note" VALUES(21,'machine preacher curl','top 2 micros guessed 1.75 each','2026-09-24T10:08:31');
INSERT INTO "movement_note" VALUES(22,'ezbar skullcrusher','ez bar guessed 7.5, totals include bar','2026-09-24T10:13:38');
INSERT INTO "movement_note" VALUES(23,'rear delt cable fly','height under 6','2026-09-24T10:24:48');
INSERT INTO "movement_note" VALUES(24,'cable crunch','height just under 6','2026-09-27T09:41:46');
INSERT INTO "movement_note" VALUES(25,'dumbbell reverse curl','dumbbells, both arms at once, each wrist tracks free; log weaker side with L/R when sides diverge','2026-09-27T10:30:13');
INSERT INTO "movement_note" VALUES(26,'unilateral cable pushdown','height under 4','2026-09-28T09:39:23');
INSERT INTO "movement_note" VALUES(27,'unilateral cable pushdown','cable increments 0.625','2026-09-28T09:39:23');
INSERT INTO "movement_note" VALUES(28,'bayesian curl','cable just under height 14','2026-09-30T08:54:05');
INSERT INTO "movement_note" VALUES(29,'hack squat','starter 57, totals include sled','2026-10-01T09:08:19');
CREATE TABLE priority (
  muscle TEXT PRIMARY KEY,
  tier TEXT NOT NULL CHECK (tier IN ('priority', 'maintain', 'deprioritize')),
  since TEXT NOT NULL,
  until TEXT
);
CREATE TABLE progression (
  id INTEGER PRIMARY KEY,
  workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
  exercise TEXT NOT NULL REFERENCES lift(exercise) ON UPDATE CASCADE,
  verdict TEXT NOT NULL CHECK (verdict IN ('hit', 'miss', 'hold', 'baseline')),
  next_weight REAL NOT NULL,
  next_reps INTEGER NOT NULL,
  direction TEXT NOT NULL CHECK (direction IN ('up', 'flat', 'down')),
  note TEXT NOT NULL DEFAULT '',
  created TEXT NOT NULL,
  UNIQUE (workout_id, exercise)
);
INSERT INTO "progression" VALUES(1,4,'incline barbell bench press','baseline',75.0,6,'flat','','2026-09-22T17:11:12');
INSERT INTO "progression" VALUES(2,4,'cable lat raise','baseline',11.25,8,'flat','','2026-09-22T17:11:12');
INSERT INTO "progression" VALUES(3,4,'hammer strength row','baseline',90.0,8,'flat','','2026-09-22T17:11:12');
INSERT INTO "progression" VALUES(4,4,'machine lat raise','baseline',60.0,9,'flat','','2026-09-22T17:13:42');
INSERT INTO "progression" VALUES(5,4,'pec deck','baseline',85.0,8,'flat','','2026-09-22T17:13:42');
INSERT INTO "progression" VALUES(6,4,'straight bar pulldown','baseline',77.0,8,'flat','','2026-09-22T17:13:42');
INSERT INTO "progression" VALUES(7,4,'ezbar curl','baseline',35.0,6,'flat','','2026-09-22T17:11:12');
INSERT INTO "progression" VALUES(8,4,'bayesian curl','baseline',11.25,8,'flat','','2026-09-22T17:11:12');
INSERT INTO "progression" VALUES(9,4,'smith jm press','baseline',30.0,8,'flat','','2026-09-22T17:13:42');
INSERT INTO "progression" VALUES(10,4,'overhead cable extension','baseline',25.0,12,'up','','2026-09-22T17:13:42');
INSERT INTO "progression" VALUES(11,4,'face pull','baseline',38.75,10,'flat','','2026-09-22T17:11:12');
INSERT INTO "progression" VALUES(12,5,'hack squat','baseline',87.0,8,'flat','','2026-09-23T09:35:01');
INSERT INTO "progression" VALUES(13,5,'leg extension','baseline',89.0,10,'flat','','2026-09-23T09:35:01');
INSERT INTO "progression" VALUES(14,5,'leg press','baseline',115.0,10,'flat','','2026-09-23T09:35:01');
INSERT INTO "progression" VALUES(15,5,'seated leg curl','baseline',63.0,8,'flat','','2026-09-23T09:35:02');
INSERT INTO "progression" VALUES(16,5,'adductor machine','baseline',41.25,12,'flat','','2026-09-23T09:35:02');
INSERT INTO "progression" VALUES(17,5,'crunch machine','baseline',35.0,10,'flat','','2026-09-23T09:35:02');
INSERT INTO "progression" VALUES(18,5,'cable crunch','baseline',28.75,11,'flat','','2026-09-23T09:35:02');
INSERT INTO "progression" VALUES(19,5,'cable wrist curl','baseline',11.25,15,'flat','','2026-09-23T09:35:02');
INSERT INTO "progression" VALUES(20,5,'cable reverse curl','baseline',16.25,11,'flat','','2026-09-23T09:35:02');
INSERT INTO "progression" VALUES(21,6,'straight bar pulldown','hit',87.0,8,'up','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(22,6,'machine lat raise','hit',62.5,10,'up','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(23,6,'reverse-grip smith incline press','baseline',20.0,10,'flat','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(24,6,'cable lat raise','hit',11.875,10,'up','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(25,6,'hammer strength row','hit',95.0,10,'up','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(26,6,'incline dumbbell curl','baseline',12.5,12,'flat','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(27,6,'machine preacher curl','baseline',46.0,11,'flat','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(28,6,'ezbar skullcrusher','baseline',37.5,11,'flat','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(29,6,'cable pushdown','baseline',28.75,12,'flat','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(30,6,'rear delt cable fly','baseline',8.75,11,'flat','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(31,8,'hammer strength press','baseline',60.0,8,'flat','first session 60x9/7','2026-09-26T09:46:45');
INSERT INTO "progression" VALUES(32,8,'dumbbell lat raise','baseline',12.5,10,'flat','first session 12.5x10/9','2026-09-26T09:46:45');
INSERT INTO "progression" VALUES(33,8,'cable pullover','baseline',36.25,11,'flat','first session 36.25x10/10','2026-09-26T09:46:45');
INSERT INTO "progression" VALUES(34,8,'cable lat raise','hit',12.5,10,'up','11.875x10/10 clean','2026-09-26T09:46:45');
INSERT INTO "progression" VALUES(35,8,'pec deck','hit',87.5,8,'up','85x9/8','2026-09-26T09:46:45');
INSERT INTO "progression" VALUES(36,8,'hammer strength row','hit',100.0,8,'up','95x10/10 clean','2026-09-26T09:46:45');
INSERT INTO "progression" VALUES(37,8,'ezbar curl','hit',37.5,8,'up','35x9/8 premade bar','2026-09-26T09:46:45');
INSERT INTO "progression" VALUES(38,8,'bayesian curl','hit',11.875,8,'up','11.25x9/8','2026-09-26T09:46:45');
INSERT INTO "progression" VALUES(39,8,'smith jm press','hit',52.5,8,'up','accidental 60x8 bad form, clean 50x9 resets standard','2026-09-26T09:46:45');
INSERT INTO "progression" VALUES(40,8,'overhead cable extension','hit',26.25,12,'up','25x12/12 clean','2026-09-26T09:46:45');
INSERT INTO "progression" VALUES(41,8,'face pull','hit',40.0,10,'up','38.75x10/10 clean','2026-09-26T09:46:45');
INSERT INTO "progression" VALUES(42,9,'rdl','baseline',90.0,10,'flat','seed 90x10/8/8','2026-09-27T10:05:01');
INSERT INTO "progression" VALUES(43,9,'leg press','hit',115.0,11,'up','','2026-09-27T10:05:01');
INSERT INTO "progression" VALUES(44,9,'hack squat','hit',87.0,9,'up','','2026-09-27T10:05:01');
INSERT INTO "progression" VALUES(45,9,'leg extension','hit',89.0,11,'up','','2026-09-27T10:05:01');
INSERT INTO "progression" VALUES(46,9,'seated leg curl','hit',63.0,9,'up','','2026-09-27T10:05:01');
INSERT INTO "progression" VALUES(47,9,'adductor machine','hit',41.25,13,'up','','2026-09-27T10:05:01');
INSERT INTO "progression" VALUES(48,9,'crunch machine','hit',35.0,12,'up','35x11 over target','2026-09-27T10:05:01');
INSERT INTO "progression" VALUES(49,9,'cable crunch','hit',28.75,12,'up','','2026-09-27T10:05:01');
INSERT INTO "progression" VALUES(50,9,'cable reverse curl','hit',16.25,12,'up','','2026-09-27T10:05:01');
INSERT INTO "progression" VALUES(51,10,'hammer strength row','hit',112.5,8,'up','','2026-09-28T09:46:37');
INSERT INTO "progression" VALUES(52,10,'machine lat raise','hit',65.0,10,'up','','2026-09-28T09:46:37');
INSERT INTO "progression" VALUES(53,10,'reverse-grip smith incline press','hit',32.5,8,'up','','2026-09-28T09:46:37');
INSERT INTO "progression" VALUES(54,10,'dumbbell lat raise','hit',15.0,8,'up','','2026-09-28T09:46:37');
INSERT INTO "progression" VALUES(55,10,'hammer strength press','hit',65.0,8,'up','','2026-09-28T09:46:37');
INSERT INTO "progression" VALUES(56,10,'straight bar pulldown','hit',87.0,9,'flat','','2026-09-28T09:46:37');
INSERT INTO "progression" VALUES(57,10,'incline dumbbell curl','hit',15.0,8,'up','','2026-09-28T09:46:37');
INSERT INTO "progression" VALUES(58,10,'machine preacher curl','hit',46.0,12,'flat','','2026-09-28T09:46:37');
INSERT INTO "progression" VALUES(59,10,'ezbar skullcrusher','hit',40.0,10,'up','','2026-09-28T09:46:37');
INSERT INTO "progression" VALUES(60,10,'unilateral cable pushdown','baseline',13.75,10,'flat','','2026-09-28T09:46:37');
INSERT INTO "progression" VALUES(61,10,'rear delt cable fly','hit',8.75,13,'flat','','2026-09-28T09:46:37');
INSERT INTO "progression" VALUES(62,12,'incline barbell bench press','hit',77.5,6,'up','3x6 at 75, solid','2026-09-30T09:21:29');
INSERT INTO "progression" VALUES(63,12,'cable lat raise','hit',12.5,11,'up','10 then 9','2026-09-30T09:21:29');
INSERT INTO "progression" VALUES(64,12,'hammer strength row','hit',117.5,8,'up','115x9,8 over target','2026-09-30T09:21:29');
INSERT INTO "progression" VALUES(65,12,'machine lat raise','hit',67.5,10,'up','11 then 10','2026-09-30T09:21:29');
INSERT INTO "progression" VALUES(66,12,'pec deck','hit',90.0,8,'up','2x8','2026-09-30T09:21:29');
INSERT INTO "progression" VALUES(67,12,'ezbar curl','hit',37.5,9,'up','9 then 7','2026-09-30T09:21:29');
INSERT INTO "progression" VALUES(68,12,'bayesian curl','hit',12.5,8,'up','2x8, height just under 14','2026-09-30T09:21:29');
INSERT INTO "progression" VALUES(69,12,'straight bar pulldown','hold',87.0,9,'flat','87x7 then 77x9, order swap fatigue','2026-09-30T09:21:29');
INSERT INTO "progression" VALUES(70,12,'smith jm press','hit',55.0,8,'up','2x8 form dialed','2026-09-30T09:21:29');
INSERT INTO "progression" VALUES(71,12,'overhead cable extension','hit',27.5,12,'up','2x12','2026-09-30T09:21:29');
INSERT INTO "progression" VALUES(72,12,'face pull','hit',42.5,10,'up','40x12 then 41.25x10','2026-09-30T09:21:29');
INSERT INTO "progression" VALUES(73,13,'hack squat','hit',87.0,10,'up','','2026-10-01T10:19:02');
INSERT INTO "progression" VALUES(74,13,'leg extension','hit',89.0,12,'up','','2026-10-01T10:19:02');
INSERT INTO "progression" VALUES(75,13,'leg press','hit',125.0,10,'up','125 jump','2026-10-01T10:19:02');
INSERT INTO "progression" VALUES(76,13,'adductor machine','hit',45.0,12,'up','','2026-10-01T10:19:02');
INSERT INTO "progression" VALUES(77,13,'crunch machine','hold',35.0,12,'flat','13 over cap then 9','2026-10-01T10:19:02');
INSERT INTO "progression" VALUES(78,13,'cable crunch','hit',30.0,11,'up','','2026-10-01T10:19:02');
INSERT INTO "progression" VALUES(79,13,'cable wrist curl','baseline',13.75,12,'flat','new weight seed','2026-10-01T10:19:02');
INSERT INTO "progression" VALUES(80,14,'machine lat raise','hit',72.5,10,'up','','2026-10-02T10:07:44');
INSERT INTO "progression" VALUES(81,14,'straight bar pulldown','hit',87.0,10,'up','','2026-10-02T10:07:44');
INSERT INTO "progression" VALUES(82,14,'reverse-grip smith incline press','hit',37.5,8,'up','','2026-10-02T10:07:44');
INSERT INTO "progression" VALUES(83,14,'cable lat raise','hit',12.5,12,'up','','2026-10-02T10:07:44');
INSERT INTO "progression" VALUES(84,14,'hammer strength row','hit',125.0,8,'up','','2026-10-02T10:07:44');
INSERT INTO "progression" VALUES(85,14,'incline dumbbell curl','hit',17.5,9,'up','','2026-10-02T10:07:44');
INSERT INTO "progression" VALUES(86,14,'machine preacher curl','hit',53.0,12,'up','','2026-10-02T10:07:44');
INSERT INTO "progression" VALUES(87,14,'ezbar skullcrusher','hit',40.0,11,'up','','2026-10-02T10:07:44');
INSERT INTO "progression" VALUES(88,14,'cable pushdown','hit',30.0,12,'up','','2026-10-02T10:07:44');
INSERT INTO "progression" VALUES(89,14,'rear delt cable fly','hit',10.0,11,'up','','2026-10-02T10:07:44');
CREATE TABLE rotation (
  position INTEGER PRIMARY KEY,
  day TEXT NULL REFERENCES split_day(name) ON UPDATE CASCADE ON DELETE SET NULL
);
INSERT INTO "rotation" VALUES(0,'U1');
INSERT INTO "rotation" VALUES(1,'L1');
INSERT INTO "rotation" VALUES(2,'U2');
INSERT INTO "rotation" VALUES(3,NULL);
INSERT INTO "rotation" VALUES(4,'U3');
INSERT INTO "rotation" VALUES(5,'L2');
INSERT INTO "rotation" VALUES(6,'U4');
INSERT INTO "rotation" VALUES(7,NULL);
CREATE TABLE rotation_anchor (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  anchor_date TEXT NOT NULL,
  position INTEGER NOT NULL REFERENCES rotation(position)
);
INSERT INTO "rotation_anchor" VALUES(1,'2026-10-04',3);
CREATE TABLE rules (
  id INTEGER PRIMARY KEY,
  subject TEXT NOT NULL,
  text TEXT NOT NULL,
  start_date TEXT NOT NULL,
  expiry TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'superseded', 'archived')),
  created TEXT NOT NULL
);
INSERT INTO "rules" VALUES(1,'straps/grip','straps on anything grip-limited, including wrapping straps around cable attachments instead of handles. Grip is never a limiter.','2026-09-18',NULL,'active','2026-09-20T15:14:08');
INSERT INTO "rules" VALUES(2,'autoreg','autoreg: manage training volume within MEV to MRV bounds and swap movements only at strong evidence, narrate every change with evidence, everything revertible','2026-09-21',NULL,'active','2026-09-21T22:14:01');
INSERT INTO "rules" VALUES(3,'coaching','after every logged set, state the next set: same movement with weight and reps call, or next movement with setup notes and conservative first-set target when cold start','2026-09-22',NULL,'active','2026-09-22T09:13:06');
INSERT INTO "rules" VALUES(4,'bodyweight','ask for bodyweight at session start so it gets measured on the gym scale','2026-09-22',NULL,'active','2026-09-22T10:45:59');
INSERT INTO "rules" VALUES(5,'coaching','don''t prompt for sleep or pain at session close, sleep is consistent and pain none unless volunteered','2026-09-23',NULL,'active','2026-09-23T09:34:57');
INSERT INTO "rules" VALUES(6,'coaching','at every session end, show two separate blocks: what the agent wrote this session (notes, memory, rules, progression, sync/commit), and chat-only thoughts, conversational','2026-09-23',NULL,'active','2026-09-23T09:38:03');
INSERT INTO "rules" VALUES(7,'coaching','laterality (unilateral/bilateral) and setup facts go to movement notes via map note on first sight, never left only in set notes','2026-09-23',NULL,'active','2026-09-23T09:39:41');
INSERT INTO "rules" VALUES(8,'smith','Smith movements log added plates only, bar counts as 0','2026-09-24',NULL,'active','2026-09-24T09:30:32');
INSERT INTO "rules" VALUES(9,'coaching','got it / done means hit the prescribed target exactly, log it as-is','2026-09-27',NULL,'active','2026-09-27T08:58:57');
INSERT INTO "rules" VALUES(10,'coaching','when a movement has a known starting weight, calculate off the total but always tell both: total plus starter and added split (e.g. 87 total = 57 starter + 30 added)','2026-10-01',NULL,'active','2026-10-01T09:08:19');
INSERT INTO "rules" VALUES(11,'coaching','never prescribe over 12 reps for any movement; when reps would exceed 12, bump weight instead and keep target at 12 or below','2026-10-01',NULL,'active','2026-10-01T09:59:08');
CREATE TABLE schema_version (version INTEGER NOT NULL);
INSERT INTO "schema_version" VALUES(3);
CREATE TABLE sets (
  id INTEGER PRIMARY KEY,
  workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
  exercise TEXT NOT NULL REFERENCES lift(exercise) ON UPDATE CASCADE,
  weight REAL NOT NULL,
  reps INTEGER NOT NULL CHECK (reps > 0),
  note TEXT NOT NULL DEFAULT '',
  created TEXT NOT NULL
);
INSERT INTO "sets" VALUES(1,4,'incline barbell bench press',75.0,7,'','2026-09-22T09:04:30');
INSERT INTO "sets" VALUES(2,4,'incline barbell bench press',75.0,6,'','2026-09-22T09:07:40');
INSERT INTO "sets" VALUES(3,4,'incline barbell bench press',75.0,6,'','2026-09-22T09:13:02');
INSERT INTO "sets" VALUES(4,4,'cable lat raise',11.25,8,'','2026-09-22T09:19:32');
INSERT INTO "sets" VALUES(5,4,'cable lat raise',11.25,8,'','2026-09-22T09:23:01');
INSERT INTO "sets" VALUES(6,4,'hammer strength row',90.0,8,'','2026-09-22T09:27:29');
INSERT INTO "sets" VALUES(7,4,'hammer strength row',90.0,8,'','2026-09-22T09:31:47');
INSERT INTO "sets" VALUES(8,4,'machine lat raise',60.0,9,'','2026-09-22T09:35:23');
INSERT INTO "sets" VALUES(9,4,'machine lat raise',60.0,9,'','2026-09-22T09:39:03');
INSERT INTO "sets" VALUES(10,4,'pec deck',85.0,10,'','2026-09-22T09:42:10');
INSERT INTO "sets" VALUES(11,4,'pec deck',85.0,8,'','2026-09-22T09:45:26');
INSERT INTO "sets" VALUES(12,4,'straight bar pulldown',77.0,9,'','2026-09-22T09:49:50');
INSERT INTO "sets" VALUES(13,4,'straight bar pulldown',77.0,8,'','2026-09-22T09:53:47');
INSERT INTO "sets" VALUES(14,4,'ezbar curl',35.0,7,'first time doing this in over a year','2026-09-22T09:58:15');
INSERT INTO "sets" VALUES(15,4,'ezbar curl',35.0,6,'','2026-09-22T10:02:22');
INSERT INTO "sets" VALUES(16,4,'bayesian curl',11.25,8,'','2026-09-22T10:06:34');
INSERT INTO "sets" VALUES(17,4,'bayesian curl',11.25,8,'','2026-09-22T10:12:41');
INSERT INTO "sets" VALUES(18,4,'smith jm press',30.0,8,'bicep pump nasty at bottom','2026-09-22T10:21:15');
INSERT INTO "sets" VALUES(19,4,'smith jm press',30.0,8,'','2026-09-22T10:24:26');
INSERT INTO "sets" VALUES(20,4,'overhead cable extension',23.75,12,'','2026-09-22T10:29:35');
INSERT INTO "sets" VALUES(21,4,'overhead cable extension',23.75,12,'forearms push into pumped biceps at bottom','2026-09-22T10:34:05');
INSERT INTO "sets" VALUES(22,4,'face pull',38.75,12,'','2026-09-22T10:36:43');
INSERT INTO "sets" VALUES(23,4,'face pull',38.75,10,'','2026-09-22T10:39:34');
INSERT INTO "sets" VALUES(24,5,'hack squat',87.0,8,'','2026-09-23T08:13:07');
INSERT INTO "sets" VALUES(25,5,'hack squat',87.0,7,'','2026-09-23T08:17:56');
INSERT INTO "sets" VALUES(26,5,'leg extension',89.0,10,'','2026-09-23T08:23:29');
INSERT INTO "sets" VALUES(27,5,'leg extension',89.0,10,'','2026-09-23T08:26:11');
INSERT INTO "sets" VALUES(28,5,'leg extension',89.0,8,'','2026-09-23T08:27:15');
INSERT INTO "sets" VALUES(29,5,'leg press',115.0,10,'','2026-09-23T08:30:38');
INSERT INTO "sets" VALUES(30,5,'leg press',115.0,9,'','2026-09-23T08:35:02');
INSERT INTO "sets" VALUES(31,5,'seated leg curl',63.0,8,'','2026-09-23T08:39:43');
INSERT INTO "sets" VALUES(32,5,'seated leg curl',63.0,8,'','2026-09-23T08:43:01');
INSERT INTO "sets" VALUES(33,5,'seated leg curl',63.0,6,'','2026-09-23T08:47:23');
INSERT INTO "sets" VALUES(34,5,'adductor machine',41.25,12,'','2026-09-23T08:50:46');
INSERT INTO "sets" VALUES(35,5,'adductor machine',41.25,11,'','2026-09-23T08:54:15');
INSERT INTO "sets" VALUES(36,5,'crunch machine',35.0,10,'','2026-09-23T09:01:31');
INSERT INTO "sets" VALUES(37,5,'crunch machine',35.0,8,'','2026-09-23T09:03:48');
INSERT INTO "sets" VALUES(38,5,'cable crunch',28.75,11,'best feeling of any crunch yet','2026-09-23T09:09:34');
INSERT INTO "sets" VALUES(39,5,'cable crunch',28.75,11,'','2026-09-23T09:13:09');
INSERT INTO "sets" VALUES(40,5,'cable wrist curl',11.25,15,'both sides 15 unilateral','2026-09-23T09:19:51');
INSERT INTO "sets" VALUES(41,5,'cable wrist curl',11.25,13,'','2026-09-23T09:22:17');
INSERT INTO "sets" VALUES(42,5,'cable wrist curl',11.25,12,'','2026-09-23T09:24:54');
INSERT INTO "sets" VALUES(43,5,'cable reverse curl',16.25,11,'bilateral','2026-09-23T09:28:09');
INSERT INTO "sets" VALUES(44,5,'cable reverse curl',16.25,9,'','2026-09-23T09:30:54');
INSERT INTO "sets" VALUES(45,6,'straight bar pulldown',77.0,12,'','2026-09-24T09:03:39');
INSERT INTO "sets" VALUES(46,6,'straight bar pulldown',87.0,8,'','2026-09-24T09:08:06');
INSERT INTO "sets" VALUES(47,6,'straight bar pulldown',87.0,6,'','2026-09-24T09:12:52');
INSERT INTO "sets" VALUES(48,6,'machine lat raise',60.0,12,'','2026-09-24T09:16:54');
INSERT INTO "sets" VALUES(49,6,'machine lat raise',62.5,10,'','2026-09-24T09:21:24');
INSERT INTO "sets" VALUES(50,6,'reverse-grip smith incline press',20.0,9,'wrists awkward, wants to rotate, not painful','2026-09-24T09:30:30');
INSERT INTO "sets" VALUES(51,6,'reverse-grip smith incline press',20.0,9,'form much nicer','2026-09-24T09:32:19');
INSERT INTO "sets" VALUES(52,6,'reverse-grip smith incline press',20.0,7,'','2026-09-24T09:36:20');
INSERT INTO "sets" VALUES(53,6,'cable lat raise',11.25,10,'','2026-09-24T09:40:39');
INSERT INTO "sets" VALUES(54,6,'cable lat raise',11.25,10,'','2026-09-24T09:44:57');
INSERT INTO "sets" VALUES(55,6,'hammer strength row',90.0,11,'','2026-09-24T09:49:02');
INSERT INTO "sets" VALUES(56,6,'hammer strength row',95.0,9,'','2026-09-24T09:53:17');
INSERT INTO "sets" VALUES(57,6,'incline dumbbell curl',12.5,11,'','2026-09-24T09:58:12');
INSERT INTO "sets" VALUES(58,6,'incline dumbbell curl',12.5,9,'','2026-09-24T10:02:32');
INSERT INTO "sets" VALUES(59,6,'machine preacher curl',46.0,10,'','2026-09-24T10:07:10');
INSERT INTO "sets" VALUES(60,6,'machine preacher curl',46.0,9,'','2026-09-24T10:09:37');
INSERT INTO "sets" VALUES(61,6,'ezbar skullcrusher',37.5,10,'','2026-09-24T10:15:38');
INSERT INTO "sets" VALUES(62,6,'ezbar skullcrusher',37.5,9,'','2026-09-24T10:18:57');
INSERT INTO "sets" VALUES(63,6,'cable pushdown',28.75,11,'','2026-09-24T10:21:33');
INSERT INTO "sets" VALUES(64,6,'cable pushdown',28.75,11,'','2026-09-24T10:24:46');
INSERT INTO "sets" VALUES(65,6,'rear delt cable fly',8.75,10,'','2026-09-24T10:26:11');
INSERT INTO "sets" VALUES(66,6,'rear delt cable fly',8.75,9,'','2026-09-24T10:28:08');
INSERT INTO "sets" VALUES(67,8,'hammer strength press',60.0,9,'','2026-09-26T08:22:48');
INSERT INTO "sets" VALUES(68,8,'hammer strength press',60.0,7,'','2026-09-26T08:27:30');
INSERT INTO "sets" VALUES(69,8,'dumbbell lat raise',12.5,10,'','2026-09-26T08:31:14');
INSERT INTO "sets" VALUES(70,8,'dumbbell lat raise',12.5,9,'','2026-09-26T08:35:21');
INSERT INTO "sets" VALUES(71,8,'cable pullover',36.25,10,'','2026-09-26T08:38:25');
INSERT INTO "sets" VALUES(72,8,'cable pullover',36.25,10,'','2026-09-26T08:42:30');
INSERT INTO "sets" VALUES(73,8,'cable lat raise',11.875,10,'','2026-09-26T08:47:45');
INSERT INTO "sets" VALUES(74,8,'cable lat raise',11.875,10,'','2026-09-26T08:51:21');
INSERT INTO "sets" VALUES(75,8,'pec deck',85.0,9,'','2026-09-26T08:55:50');
INSERT INTO "sets" VALUES(76,8,'pec deck',85.0,8,'','2026-09-26T08:59:49');
INSERT INTO "sets" VALUES(77,8,'hammer strength row',95.0,10,'','2026-09-26T09:03:48');
INSERT INTO "sets" VALUES(78,8,'hammer strength row',95.0,10,'','2026-09-26T09:09:03');
INSERT INTO "sets" VALUES(79,8,'ezbar curl',35.0,9,'','2026-09-26T09:12:26');
INSERT INTO "sets" VALUES(80,8,'ezbar curl',35.0,8,'','2026-09-26T09:16:12');
INSERT INTO "sets" VALUES(81,8,'bayesian curl',11.25,9,'','2026-09-26T09:20:16');
INSERT INTO "sets" VALUES(82,8,'bayesian curl',11.25,8,'','2026-09-26T09:23:55');
INSERT INTO "sets" VALUES(83,8,'smith jm press',60.0,8,'accidental 30 per side, bad form','2026-09-26T09:32:49');
INSERT INTO "sets" VALUES(84,8,'smith jm press',50.0,9,'','2026-09-26T09:35:39');
INSERT INTO "sets" VALUES(85,8,'overhead cable extension',25.0,12,'','2026-09-26T09:39:59');
INSERT INTO "sets" VALUES(86,8,'overhead cable extension',25.0,12,'','2026-09-26T09:43:28');
INSERT INTO "sets" VALUES(87,8,'face pull',38.75,10,'','2026-09-26T09:46:01');
INSERT INTO "sets" VALUES(88,8,'face pull',38.75,10,'','2026-09-26T09:46:01');
INSERT INTO "sets" VALUES(89,9,'rdl',90.0,10,'','2026-09-27T08:25:23');
INSERT INTO "sets" VALUES(90,9,'rdl',90.0,8,'','2026-09-27T08:30:55');
INSERT INTO "sets" VALUES(91,9,'rdl',90.0,8,'','2026-09-27T08:39:29');
INSERT INTO "sets" VALUES(92,9,'leg press',115.0,10,'','2026-09-27T08:45:30');
INSERT INTO "sets" VALUES(93,9,'leg press',115.0,9,'','2026-09-27T08:50:14');
INSERT INTO "sets" VALUES(94,9,'leg press',115.0,8,'','2026-09-27T08:54:26');
INSERT INTO "sets" VALUES(95,9,'hack squat',87.0,8,'','2026-09-27T08:58:57');
INSERT INTO "sets" VALUES(96,9,'hack squat',87.0,7,'','2026-09-27T09:04:14');
INSERT INTO "sets" VALUES(97,9,'leg extension',89.0,10,'','2026-09-27T09:08:30');
INSERT INTO "sets" VALUES(98,9,'leg extension',89.0,9,'','2026-09-27T09:12:41');
INSERT INTO "sets" VALUES(99,9,'adductor machine',41.25,12,'','2026-09-27T09:15:16');
INSERT INTO "sets" VALUES(100,9,'adductor machine',41.25,11,'','2026-09-27T09:18:16');
INSERT INTO "sets" VALUES(101,9,'adductor machine',41.25,9,'','2026-09-27T09:19:15');
INSERT INTO "sets" VALUES(102,9,'seated leg curl',63.0,8,'','2026-09-27T09:21:53');
INSERT INTO "sets" VALUES(103,9,'seated leg curl',63.0,7,'','2026-09-27T09:25:27');
INSERT INTO "sets" VALUES(104,9,'seated leg curl',63.0,6,'','2026-09-27T09:29:16');
INSERT INTO "sets" VALUES(105,9,'crunch machine',35.0,11,'','2026-09-27T09:31:58');
INSERT INTO "sets" VALUES(106,9,'crunch machine',35.0,9,'','2026-09-27T09:36:23');
INSERT INTO "sets" VALUES(107,9,'cable crunch',28.75,11,'','2026-09-27T09:41:46');
INSERT INTO "sets" VALUES(108,9,'cable crunch',28.75,10,'','2026-09-27T09:44:57');
INSERT INTO "sets" VALUES(109,9,'cable reverse curl',16.25,11,'','2026-09-27T09:53:03');
INSERT INTO "sets" VALUES(110,9,'cable reverse curl',16.25,10,'','2026-09-27T09:55:30');
INSERT INTO "sets" VALUES(111,9,'cable reverse curl',16.25,9,'','2026-09-27T09:57:56');
INSERT INTO "sets" VALUES(112,10,'hammer strength row',110.0,10,'','2026-09-28T08:16:12');
INSERT INTO "sets" VALUES(113,10,'hammer strength row',110.0,9,'','2026-09-28T08:21:30');
INSERT INTO "sets" VALUES(114,10,'machine lat raise',62.5,12,'','2026-09-28T08:25:23');
INSERT INTO "sets" VALUES(115,10,'machine lat raise',65.0,9,'','2026-09-28T08:29:35');
INSERT INTO "sets" VALUES(116,10,'reverse-grip smith incline press',30.0,8,'','2026-09-28T08:33:31');
INSERT INTO "sets" VALUES(117,10,'reverse-grip smith incline press',30.0,9,'','2026-09-28T08:40:43');
INSERT INTO "sets" VALUES(118,10,'reverse-grip smith incline press',30.0,9,'','2026-09-28T08:42:30');
INSERT INTO "sets" VALUES(119,10,'dumbbell lat raise',12.5,11,'','2026-09-28T08:47:10');
INSERT INTO "sets" VALUES(120,10,'dumbbell lat raise',12.5,11,'','2026-09-28T08:52:20');
INSERT INTO "sets" VALUES(121,10,'hammer strength press',60.0,10,'','2026-09-28T08:56:12');
INSERT INTO "sets" VALUES(122,10,'hammer strength press',65.0,7,'','2026-09-28T09:00:03');
INSERT INTO "sets" VALUES(123,10,'straight bar pulldown',87.0,8,'','2026-09-28T09:04:50');
INSERT INTO "sets" VALUES(124,10,'straight bar pulldown',87.0,7,'','2026-09-28T09:09:35');
INSERT INTO "sets" VALUES(125,10,'incline dumbbell curl',12.5,12,'','2026-09-28T09:16:01');
INSERT INTO "sets" VALUES(126,10,'incline dumbbell curl',12.5,11,'','2026-09-28T09:17:21');
INSERT INTO "sets" VALUES(127,10,'machine preacher curl',46.0,11,'','2026-09-28T09:21:23');
INSERT INTO "sets" VALUES(128,10,'machine preacher curl',46.0,9,'','2026-09-28T09:24:54');
INSERT INTO "sets" VALUES(129,10,'ezbar skullcrusher',37.5,12,'','2026-09-28T09:29:31');
INSERT INTO "sets" VALUES(130,10,'ezbar skullcrusher',37.5,9,'','2026-09-28T09:34:39');
INSERT INTO "sets" VALUES(131,10,'unilateral cable pushdown',13.75,8,'','2026-09-28T09:39:23');
INSERT INTO "sets" VALUES(132,10,'unilateral cable pushdown',13.75,8,'','2026-09-28T09:43:43');
INSERT INTO "sets" VALUES(133,10,'rear delt cable fly',8.75,12,'','2026-09-28T09:46:33');
INSERT INTO "sets" VALUES(134,12,'incline barbell bench press',75.0,6,'','2026-09-30T08:12:25');
INSERT INTO "sets" VALUES(135,12,'incline barbell bench press',75.0,6,'','2026-09-30T08:16:36');
INSERT INTO "sets" VALUES(136,12,'incline barbell bench press',75.0,6,'','2026-09-30T08:20:23');
INSERT INTO "sets" VALUES(137,12,'cable lat raise',12.5,10,'','2026-09-30T08:23:46');
INSERT INTO "sets" VALUES(138,12,'cable lat raise',12.5,9,'','2026-09-30T08:27:06');
INSERT INTO "sets" VALUES(139,12,'hammer strength row',115.0,9,'','2026-09-30T08:31:14');
INSERT INTO "sets" VALUES(140,12,'hammer strength row',115.0,8,'','2026-09-30T08:34:30');
INSERT INTO "sets" VALUES(141,12,'machine lat raise',65.0,11,'','2026-09-30T08:36:17');
INSERT INTO "sets" VALUES(142,12,'machine lat raise',65.0,10,'','2026-09-30T08:38:59');
INSERT INTO "sets" VALUES(143,12,'pec deck',87.5,8,'','2026-09-30T08:41:25');
INSERT INTO "sets" VALUES(144,12,'pec deck',87.5,8,'','2026-09-30T08:44:10');
INSERT INTO "sets" VALUES(145,12,'ezbar curl',37.5,9,'','2026-09-30T08:47:51');
INSERT INTO "sets" VALUES(146,12,'ezbar curl',37.5,7,'','2026-09-30T08:50:25');
INSERT INTO "sets" VALUES(147,12,'bayesian curl',11.875,8,'','2026-09-30T08:54:05');
INSERT INTO "sets" VALUES(148,12,'bayesian curl',11.875,8,'','2026-09-30T08:57:14');
INSERT INTO "sets" VALUES(149,12,'straight bar pulldown',87.0,7,'','2026-09-30T08:59:20');
INSERT INTO "sets" VALUES(150,12,'straight bar pulldown',77.0,9,'','2026-09-30T09:02:21');
INSERT INTO "sets" VALUES(151,12,'smith jm press',52.5,8,'form dialed, consistent','2026-09-30T09:06:59');
INSERT INTO "sets" VALUES(152,12,'smith jm press',52.5,8,'','2026-09-30T09:09:55');
INSERT INTO "sets" VALUES(153,12,'overhead cable extension',26.25,12,'','2026-09-30T09:12:56');
INSERT INTO "sets" VALUES(154,12,'overhead cable extension',26.25,12,'','2026-09-30T09:15:13');
INSERT INTO "sets" VALUES(155,12,'face pull',40.0,12,'','2026-09-30T09:18:06');
INSERT INTO "sets" VALUES(156,12,'face pull',41.25,10,'','2026-09-30T09:21:22');
INSERT INTO "sets" VALUES(157,13,'hack squat',87.0,9,'','2026-10-01T09:09:36');
INSERT INTO "sets" VALUES(158,13,'hack squat',87.0,9,'','2026-10-01T09:14:48');
INSERT INTO "sets" VALUES(159,13,'leg extension',89.0,12,'','2026-10-01T09:20:51');
INSERT INTO "sets" VALUES(160,13,'leg extension',89.0,10,'','2026-10-01T09:28:21');
INSERT INTO "sets" VALUES(161,13,'leg extension',89.0,9,'','2026-10-01T09:28:25');
INSERT INTO "sets" VALUES(162,13,'leg press',125.0,9,'','2026-10-01T09:32:41');
INSERT INTO "sets" VALUES(163,13,'leg press',125.0,8,'','2026-10-01T09:37:43');
INSERT INTO "sets" VALUES(164,13,'adductor machine',45.0,11,'','2026-10-01T09:39:46');
INSERT INTO "sets" VALUES(165,13,'adductor machine',45.0,10,'','2026-10-01T09:42:53');
INSERT INTO "sets" VALUES(166,13,'crunch machine',35.0,13,'','2026-10-01T09:45:32');
INSERT INTO "sets" VALUES(167,13,'crunch machine',35.0,9,'','2026-10-01T09:49:36');
INSERT INTO "sets" VALUES(168,13,'cable crunch',28.75,12,'','2026-10-01T09:53:38');
INSERT INTO "sets" VALUES(169,13,'cable crunch',28.75,11,'','2026-10-01T09:57:00');
INSERT INTO "sets" VALUES(170,13,'cable wrist curl',13.75,12,'','2026-10-01T10:00:16');
INSERT INTO "sets" VALUES(171,13,'cable wrist curl',13.75,12,'','2026-10-01T10:01:56');
INSERT INTO "sets" VALUES(172,13,'cable wrist curl',13.75,10,'','2026-10-01T10:04:21');
INSERT INTO "sets" VALUES(173,14,'machine lat raise',67.5,12,'','2026-10-02T08:42:35');
INSERT INTO "sets" VALUES(174,14,'machine lat raise',70.0,10,'','2026-10-02T08:45:18');
INSERT INTO "sets" VALUES(175,14,'straight bar pulldown',87.0,9,'','2026-10-02T08:52:22');
INSERT INTO "sets" VALUES(176,14,'straight bar pulldown',87.0,7,'','2026-10-02T08:52:52');
INSERT INTO "sets" VALUES(177,14,'straight bar pulldown',77.0,8,'','2026-10-02T08:56:26');
INSERT INTO "sets" VALUES(178,14,'reverse-grip smith incline press',35.0,10,'','2026-10-02T09:02:31');
INSERT INTO "sets" VALUES(179,14,'reverse-grip smith incline press',35.0,9,'','2026-10-02T09:05:24');
INSERT INTO "sets" VALUES(180,14,'reverse-grip smith incline press',35.0,8,'','2026-10-02T09:10:06');
INSERT INTO "sets" VALUES(181,14,'cable lat raise',12.5,11,'','2026-10-02T09:15:07');
INSERT INTO "sets" VALUES(182,14,'cable lat raise',12.5,11,'','2026-10-02T09:18:59');
INSERT INTO "sets" VALUES(183,14,'incline dumbbell curl',15.0,10,'','2026-10-02T09:23:51');
INSERT INTO "sets" VALUES(184,14,'incline dumbbell curl',17.5,8,'','2026-10-02T09:31:02');
INSERT INTO "sets" VALUES(185,14,'hammer strength row',120.0,8,'','2026-10-02T09:31:28');
INSERT INTO "sets" VALUES(186,14,'hammer strength row',122.5,8,'','2026-10-02T09:36:11');
INSERT INTO "sets" VALUES(187,14,'machine preacher curl',53.0,11,'','2026-10-02T09:38:36');
INSERT INTO "sets" VALUES(188,14,'machine preacher curl',53.0,10,'','2026-10-02T09:44:14');
INSERT INTO "sets" VALUES(189,14,'ezbar skullcrusher',40.0,10,'','2026-10-02T09:48:56');
INSERT INTO "sets" VALUES(190,14,'ezbar skullcrusher',40.0,8,'','2026-10-02T09:54:11');
INSERT INTO "sets" VALUES(191,14,'cable pushdown',29.375,12,'','2026-10-02T09:56:41');
INSERT INTO "sets" VALUES(192,14,'cable pushdown',29.375,10,'','2026-10-02T09:59:35');
INSERT INTO "sets" VALUES(193,14,'rear delt cable fly',9.375,12,'','2026-10-02T10:02:15');
INSERT INTO "sets" VALUES(194,14,'rear delt cable fly',9.375,10,'','2026-10-02T10:07:01');
CREATE TABLE split_day (
  name TEXT PRIMARY KEY
);
INSERT INTO "split_day" VALUES('L1');
INSERT INTO "split_day" VALUES('L2');
INSERT INTO "split_day" VALUES('U1');
INSERT INTO "split_day" VALUES('U2');
INSERT INTO "split_day" VALUES('U3');
INSERT INTO "split_day" VALUES('U4');
INSERT INTO "split_day" VALUES('rest');
CREATE TABLE split_slot (
  id INTEGER PRIMARY KEY,
  variant TEXT NOT NULL CHECK (variant IN ('active', 'baseline')),
  day TEXT NOT NULL REFERENCES split_day(name) ON UPDATE CASCADE ON DELETE CASCADE,
  slot INTEGER NOT NULL,
  sets INTEGER NOT NULL,
  UNIQUE (variant, day, slot)
);
INSERT INTO "split_slot" VALUES(1,'active','L1',1,2);
INSERT INTO "split_slot" VALUES(2,'baseline','L1',1,2);
INSERT INTO "split_slot" VALUES(3,'active','L1',2,3);
INSERT INTO "split_slot" VALUES(4,'baseline','L1',2,3);
INSERT INTO "split_slot" VALUES(5,'active','L1',3,2);
INSERT INTO "split_slot" VALUES(6,'baseline','L1',3,2);
INSERT INTO "split_slot" VALUES(7,'active','L1',4,3);
INSERT INTO "split_slot" VALUES(8,'baseline','L1',4,3);
INSERT INTO "split_slot" VALUES(9,'active','L1',5,2);
INSERT INTO "split_slot" VALUES(10,'baseline','L1',5,2);
INSERT INTO "split_slot" VALUES(11,'active','L1',6,2);
INSERT INTO "split_slot" VALUES(12,'baseline','L1',6,2);
INSERT INTO "split_slot" VALUES(13,'active','L1',7,2);
INSERT INTO "split_slot" VALUES(14,'baseline','L1',7,2);
INSERT INTO "split_slot" VALUES(15,'active','L1',8,3);
INSERT INTO "split_slot" VALUES(16,'baseline','L1',8,2);
INSERT INTO "split_slot" VALUES(17,'active','L1',9,2);
INSERT INTO "split_slot" VALUES(18,'baseline','L1',9,2);
INSERT INTO "split_slot" VALUES(19,'active','L2',1,3);
INSERT INTO "split_slot" VALUES(20,'baseline','L2',1,3);
INSERT INTO "split_slot" VALUES(21,'active','L2',2,3);
INSERT INTO "split_slot" VALUES(22,'baseline','L2',2,3);
INSERT INTO "split_slot" VALUES(23,'active','L2',3,2);
INSERT INTO "split_slot" VALUES(24,'baseline','L2',3,2);
INSERT INTO "split_slot" VALUES(25,'active','L2',4,2);
INSERT INTO "split_slot" VALUES(26,'baseline','L2',4,2);
INSERT INTO "split_slot" VALUES(27,'active','L2',5,3);
INSERT INTO "split_slot" VALUES(28,'baseline','L2',5,3);
INSERT INTO "split_slot" VALUES(29,'active','L2',6,3);
INSERT INTO "split_slot" VALUES(30,'baseline','L2',6,3);
INSERT INTO "split_slot" VALUES(31,'active','L2',7,2);
INSERT INTO "split_slot" VALUES(32,'baseline','L2',7,2);
INSERT INTO "split_slot" VALUES(33,'active','L2',8,2);
INSERT INTO "split_slot" VALUES(34,'baseline','L2',8,2);
INSERT INTO "split_slot" VALUES(35,'active','L2',9,3);
INSERT INTO "split_slot" VALUES(36,'baseline','L2',9,2);
INSERT INTO "split_slot" VALUES(37,'active','U1',1,3);
INSERT INTO "split_slot" VALUES(38,'baseline','U1',1,3);
INSERT INTO "split_slot" VALUES(39,'active','U1',2,2);
INSERT INTO "split_slot" VALUES(40,'baseline','U1',2,2);
INSERT INTO "split_slot" VALUES(41,'active','U1',3,2);
INSERT INTO "split_slot" VALUES(42,'baseline','U1',3,2);
INSERT INTO "split_slot" VALUES(43,'active','U1',4,2);
INSERT INTO "split_slot" VALUES(44,'baseline','U1',4,2);
INSERT INTO "split_slot" VALUES(45,'active','U1',5,2);
INSERT INTO "split_slot" VALUES(46,'baseline','U1',5,2);
INSERT INTO "split_slot" VALUES(47,'active','U1',6,2);
INSERT INTO "split_slot" VALUES(48,'baseline','U1',6,2);
INSERT INTO "split_slot" VALUES(49,'active','U1',7,2);
INSERT INTO "split_slot" VALUES(50,'baseline','U1',7,2);
INSERT INTO "split_slot" VALUES(51,'active','U1',8,2);
INSERT INTO "split_slot" VALUES(52,'baseline','U1',8,2);
INSERT INTO "split_slot" VALUES(53,'active','U1',9,2);
INSERT INTO "split_slot" VALUES(54,'baseline','U1',9,2);
INSERT INTO "split_slot" VALUES(55,'active','U1',10,2);
INSERT INTO "split_slot" VALUES(56,'baseline','U1',10,2);
INSERT INTO "split_slot" VALUES(57,'active','U1',11,2);
INSERT INTO "split_slot" VALUES(58,'baseline','U1',11,2);
INSERT INTO "split_slot" VALUES(59,'active','U2',1,3);
INSERT INTO "split_slot" VALUES(60,'baseline','U2',1,3);
INSERT INTO "split_slot" VALUES(61,'active','U2',2,2);
INSERT INTO "split_slot" VALUES(62,'baseline','U2',2,2);
INSERT INTO "split_slot" VALUES(63,'active','U2',3,3);
INSERT INTO "split_slot" VALUES(64,'baseline','U2',3,3);
INSERT INTO "split_slot" VALUES(65,'active','U2',4,2);
INSERT INTO "split_slot" VALUES(66,'baseline','U2',4,2);
INSERT INTO "split_slot" VALUES(67,'active','U2',5,2);
INSERT INTO "split_slot" VALUES(68,'baseline','U2',5,2);
INSERT INTO "split_slot" VALUES(69,'active','U2',6,2);
INSERT INTO "split_slot" VALUES(70,'baseline','U2',6,2);
INSERT INTO "split_slot" VALUES(71,'active','U2',7,2);
INSERT INTO "split_slot" VALUES(72,'baseline','U2',7,2);
INSERT INTO "split_slot" VALUES(73,'active','U2',8,2);
INSERT INTO "split_slot" VALUES(74,'baseline','U2',8,2);
INSERT INTO "split_slot" VALUES(75,'active','U2',9,2);
INSERT INTO "split_slot" VALUES(76,'baseline','U2',9,2);
INSERT INTO "split_slot" VALUES(77,'active','U2',10,2);
INSERT INTO "split_slot" VALUES(78,'baseline','U2',10,2);
INSERT INTO "split_slot" VALUES(79,'active','U3',1,2);
INSERT INTO "split_slot" VALUES(80,'baseline','U3',1,2);
INSERT INTO "split_slot" VALUES(81,'active','U3',2,2);
INSERT INTO "split_slot" VALUES(82,'baseline','U3',2,2);
INSERT INTO "split_slot" VALUES(83,'active','U3',3,2);
INSERT INTO "split_slot" VALUES(84,'baseline','U3',3,2);
INSERT INTO "split_slot" VALUES(85,'active','U3',4,2);
INSERT INTO "split_slot" VALUES(86,'baseline','U3',4,2);
INSERT INTO "split_slot" VALUES(87,'active','U3',5,2);
INSERT INTO "split_slot" VALUES(88,'baseline','U3',5,2);
INSERT INTO "split_slot" VALUES(89,'active','U3',6,2);
INSERT INTO "split_slot" VALUES(90,'baseline','U3',6,2);
INSERT INTO "split_slot" VALUES(91,'active','U3',7,2);
INSERT INTO "split_slot" VALUES(92,'baseline','U3',7,2);
INSERT INTO "split_slot" VALUES(93,'active','U3',8,2);
INSERT INTO "split_slot" VALUES(94,'baseline','U3',8,2);
INSERT INTO "split_slot" VALUES(95,'active','U3',9,2);
INSERT INTO "split_slot" VALUES(96,'baseline','U3',9,2);
INSERT INTO "split_slot" VALUES(97,'active','U3',10,2);
INSERT INTO "split_slot" VALUES(98,'baseline','U3',10,2);
INSERT INTO "split_slot" VALUES(99,'active','U3',11,2);
INSERT INTO "split_slot" VALUES(100,'baseline','U3',11,2);
INSERT INTO "split_slot" VALUES(101,'active','U4',1,2);
INSERT INTO "split_slot" VALUES(102,'baseline','U4',1,2);
INSERT INTO "split_slot" VALUES(103,'active','U4',2,2);
INSERT INTO "split_slot" VALUES(104,'baseline','U4',2,2);
INSERT INTO "split_slot" VALUES(105,'active','U4',3,3);
INSERT INTO "split_slot" VALUES(106,'baseline','U4',3,3);
INSERT INTO "split_slot" VALUES(107,'active','U4',4,2);
INSERT INTO "split_slot" VALUES(108,'baseline','U4',4,2);
INSERT INTO "split_slot" VALUES(109,'active','U4',5,2);
INSERT INTO "split_slot" VALUES(110,'baseline','U4',5,2);
INSERT INTO "split_slot" VALUES(111,'active','U4',6,2);
INSERT INTO "split_slot" VALUES(112,'baseline','U4',6,2);
INSERT INTO "split_slot" VALUES(113,'active','U4',7,2);
INSERT INTO "split_slot" VALUES(114,'baseline','U4',7,2);
INSERT INTO "split_slot" VALUES(115,'active','U4',8,2);
INSERT INTO "split_slot" VALUES(116,'baseline','U4',8,2);
INSERT INTO "split_slot" VALUES(117,'active','U4',9,2);
INSERT INTO "split_slot" VALUES(118,'baseline','U4',9,2);
INSERT INTO "split_slot" VALUES(119,'active','U4',10,2);
INSERT INTO "split_slot" VALUES(120,'baseline','U4',10,2);
INSERT INTO "split_slot" VALUES(121,'active','U4',11,2);
INSERT INTO "split_slot" VALUES(122,'baseline','U4',11,2);
CREATE TABLE split_slot_lift (
  slot_id INTEGER NOT NULL REFERENCES split_slot(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  exercise TEXT NOT NULL REFERENCES lift(exercise) ON UPDATE CASCADE,
  PRIMARY KEY (slot_id, position)
);
INSERT INTO "split_slot_lift" VALUES(1,0,'hack squat');
INSERT INTO "split_slot_lift" VALUES(2,0,'hack squat');
INSERT INTO "split_slot_lift" VALUES(3,0,'leg extension');
INSERT INTO "split_slot_lift" VALUES(4,0,'leg extension');
INSERT INTO "split_slot_lift" VALUES(5,0,'leg press');
INSERT INTO "split_slot_lift" VALUES(6,0,'leg press');
INSERT INTO "split_slot_lift" VALUES(7,0,'seated leg curl');
INSERT INTO "split_slot_lift" VALUES(8,0,'seated leg curl');
INSERT INTO "split_slot_lift" VALUES(9,0,'adductor machine');
INSERT INTO "split_slot_lift" VALUES(10,0,'adductor machine');
INSERT INTO "split_slot_lift" VALUES(11,0,'crunch machine');
INSERT INTO "split_slot_lift" VALUES(12,0,'crunch machine');
INSERT INTO "split_slot_lift" VALUES(13,0,'cable crunch');
INSERT INTO "split_slot_lift" VALUES(14,0,'hanging leg raise');
INSERT INTO "split_slot_lift" VALUES(15,0,'cable wrist curl');
INSERT INTO "split_slot_lift" VALUES(16,0,'cable wrist curl');
INSERT INTO "split_slot_lift" VALUES(18,0,'cable reverse curl');
INSERT INTO "split_slot_lift" VALUES(19,0,'rdl');
INSERT INTO "split_slot_lift" VALUES(20,0,'rdl');
INSERT INTO "split_slot_lift" VALUES(21,0,'leg press');
INSERT INTO "split_slot_lift" VALUES(22,0,'leg press');
INSERT INTO "split_slot_lift" VALUES(23,0,'hack squat');
INSERT INTO "split_slot_lift" VALUES(24,0,'hack squat');
INSERT INTO "split_slot_lift" VALUES(25,0,'leg extension');
INSERT INTO "split_slot_lift" VALUES(26,0,'leg extension');
INSERT INTO "split_slot_lift" VALUES(27,0,'seated leg curl');
INSERT INTO "split_slot_lift" VALUES(28,0,'seated leg curl');
INSERT INTO "split_slot_lift" VALUES(29,0,'adductor machine');
INSERT INTO "split_slot_lift" VALUES(30,0,'adductor machine');
INSERT INTO "split_slot_lift" VALUES(31,0,'crunch machine');
INSERT INTO "split_slot_lift" VALUES(32,0,'crunch machine');
INSERT INTO "split_slot_lift" VALUES(33,0,'cable crunch');
INSERT INTO "split_slot_lift" VALUES(34,0,'hanging leg raise');
INSERT INTO "split_slot_lift" VALUES(36,0,'cable wrist extension');
INSERT INTO "split_slot_lift" VALUES(37,0,'incline barbell bench press');
INSERT INTO "split_slot_lift" VALUES(38,0,'incline barbell bench press');
INSERT INTO "split_slot_lift" VALUES(39,0,'cable lat raise');
INSERT INTO "split_slot_lift" VALUES(40,0,'cable lat raise');
INSERT INTO "split_slot_lift" VALUES(41,0,'hammer strength row');
INSERT INTO "split_slot_lift" VALUES(42,0,'hammer strength row');
INSERT INTO "split_slot_lift" VALUES(43,0,'machine lat raise');
INSERT INTO "split_slot_lift" VALUES(44,0,'machine lat raise');
INSERT INTO "split_slot_lift" VALUES(45,0,'pec deck');
INSERT INTO "split_slot_lift" VALUES(46,0,'pec deck');
INSERT INTO "split_slot_lift" VALUES(47,0,'straight bar pulldown');
INSERT INTO "split_slot_lift" VALUES(48,0,'straight bar pulldown');
INSERT INTO "split_slot_lift" VALUES(49,0,'ezbar curl');
INSERT INTO "split_slot_lift" VALUES(50,0,'ezbar curl');
INSERT INTO "split_slot_lift" VALUES(51,0,'bayesian curl');
INSERT INTO "split_slot_lift" VALUES(52,0,'bayesian curl');
INSERT INTO "split_slot_lift" VALUES(53,0,'smith jm press');
INSERT INTO "split_slot_lift" VALUES(54,0,'smith jm press');
INSERT INTO "split_slot_lift" VALUES(55,0,'overhead cable extension');
INSERT INTO "split_slot_lift" VALUES(56,0,'overhead cable extension');
INSERT INTO "split_slot_lift" VALUES(57,0,'face pull');
INSERT INTO "split_slot_lift" VALUES(58,0,'face pull');
INSERT INTO "split_slot_lift" VALUES(59,0,'straight bar pulldown');
INSERT INTO "split_slot_lift" VALUES(60,0,'straight bar pulldown');
INSERT INTO "split_slot_lift" VALUES(61,0,'machine lat raise');
INSERT INTO "split_slot_lift" VALUES(62,0,'machine lat raise');
INSERT INTO "split_slot_lift" VALUES(63,0,'reverse-grip smith incline press');
INSERT INTO "split_slot_lift" VALUES(64,0,'reverse-grip smith incline press');
INSERT INTO "split_slot_lift" VALUES(65,0,'cable lat raise');
INSERT INTO "split_slot_lift" VALUES(66,0,'cable lat raise');
INSERT INTO "split_slot_lift" VALUES(67,0,'hammer strength row');
INSERT INTO "split_slot_lift" VALUES(68,0,'hammer strength row');
INSERT INTO "split_slot_lift" VALUES(69,0,'incline dumbbell curl');
INSERT INTO "split_slot_lift" VALUES(70,0,'incline dumbbell curl');
INSERT INTO "split_slot_lift" VALUES(71,0,'machine preacher curl');
INSERT INTO "split_slot_lift" VALUES(72,0,'machine preacher curl');
INSERT INTO "split_slot_lift" VALUES(73,0,'ezbar skullcrusher');
INSERT INTO "split_slot_lift" VALUES(74,0,'ezbar skullcrusher');
INSERT INTO "split_slot_lift" VALUES(75,0,'cable pushdown');
INSERT INTO "split_slot_lift" VALUES(76,0,'cable pushdown');
INSERT INTO "split_slot_lift" VALUES(77,0,'rear delt cable fly');
INSERT INTO "split_slot_lift" VALUES(78,0,'rear delt cable fly');
INSERT INTO "split_slot_lift" VALUES(79,0,'hammer strength press');
INSERT INTO "split_slot_lift" VALUES(80,0,'hammer strength press');
INSERT INTO "split_slot_lift" VALUES(81,0,'dumbbell lat raise');
INSERT INTO "split_slot_lift" VALUES(82,0,'dumbbell lat raise');
INSERT INTO "split_slot_lift" VALUES(83,0,'cable pullover');
INSERT INTO "split_slot_lift" VALUES(84,0,'cable pullover');
INSERT INTO "split_slot_lift" VALUES(85,0,'cable lat raise');
INSERT INTO "split_slot_lift" VALUES(86,0,'cable lat raise');
INSERT INTO "split_slot_lift" VALUES(87,0,'pec deck');
INSERT INTO "split_slot_lift" VALUES(88,0,'pec deck');
INSERT INTO "split_slot_lift" VALUES(89,0,'hammer strength row');
INSERT INTO "split_slot_lift" VALUES(90,0,'hammer strength row');
INSERT INTO "split_slot_lift" VALUES(91,0,'ezbar curl');
INSERT INTO "split_slot_lift" VALUES(92,0,'ezbar curl');
INSERT INTO "split_slot_lift" VALUES(93,0,'bayesian curl');
INSERT INTO "split_slot_lift" VALUES(94,0,'bayesian curl');
INSERT INTO "split_slot_lift" VALUES(95,0,'smith jm press');
INSERT INTO "split_slot_lift" VALUES(96,0,'overhead cable extension');
INSERT INTO "split_slot_lift" VALUES(97,0,'overhead cable extension');
INSERT INTO "split_slot_lift" VALUES(98,0,'unilateral cable pushdown');
INSERT INTO "split_slot_lift" VALUES(99,0,'face pull');
INSERT INTO "split_slot_lift" VALUES(100,0,'face pull');
INSERT INTO "split_slot_lift" VALUES(101,0,'hammer strength row');
INSERT INTO "split_slot_lift" VALUES(102,0,'hammer strength row');
INSERT INTO "split_slot_lift" VALUES(103,0,'machine lat raise');
INSERT INTO "split_slot_lift" VALUES(104,0,'machine lat raise');
INSERT INTO "split_slot_lift" VALUES(105,0,'reverse-grip smith incline press');
INSERT INTO "split_slot_lift" VALUES(106,0,'reverse-grip smith incline press');
INSERT INTO "split_slot_lift" VALUES(107,0,'dumbbell lat raise');
INSERT INTO "split_slot_lift" VALUES(108,0,'dumbbell lat raise');
INSERT INTO "split_slot_lift" VALUES(109,0,'hammer strength press');
INSERT INTO "split_slot_lift" VALUES(110,0,'hammer strength press');
INSERT INTO "split_slot_lift" VALUES(111,0,'straight bar pulldown');
INSERT INTO "split_slot_lift" VALUES(112,0,'straight bar pulldown');
INSERT INTO "split_slot_lift" VALUES(113,0,'incline dumbbell curl');
INSERT INTO "split_slot_lift" VALUES(114,0,'incline dumbbell curl');
INSERT INTO "split_slot_lift" VALUES(115,0,'machine preacher curl');
INSERT INTO "split_slot_lift" VALUES(116,0,'machine preacher curl');
INSERT INTO "split_slot_lift" VALUES(117,0,'ezbar skullcrusher');
INSERT INTO "split_slot_lift" VALUES(118,0,'smith jm press');
INSERT INTO "split_slot_lift" VALUES(119,0,'unilateral cable pushdown');
INSERT INTO "split_slot_lift" VALUES(120,0,'ezbar skullcrusher');
INSERT INTO "split_slot_lift" VALUES(121,0,'rear delt cable fly');
INSERT INTO "split_slot_lift" VALUES(122,0,'rear delt cable fly');
INSERT INTO "split_slot_lift" VALUES(17,0,'dumbbell reverse curl');
INSERT INTO "split_slot_lift" VALUES(35,0,'dumbbell reverse curl');
CREATE TABLE state_change (
  id INTEGER PRIMARY KEY,
  domain TEXT NOT NULL CHECK (domain IN ('program', 'priority', 'goal', 'deload', 'rule', 'rotation')),
  subject TEXT NOT NULL DEFAULT '',
  date TEXT NOT NULL,
  created TEXT NOT NULL,
  before_json TEXT NOT NULL DEFAULT '{}',
  after_json TEXT NOT NULL DEFAULT '{}',
  evidence TEXT NOT NULL DEFAULT '',
  superseded_by INTEGER REFERENCES state_change(id),
  reverses INTEGER REFERENCES state_change(id),
  sequence INTEGER NOT NULL DEFAULT 0
);
INSERT INTO "state_change" VALUES(1,'program','active:U1','2026-09-20','2026-09-26T10:12:48','{"day": "U1", "slots": [], "variant": "active"}','{"day": "U1", "slots": [{"movements": "incline barbell bench press", "sets": 3, "slot": 1}, {"movements": "cable lat raise", "sets": 2, "slot": 2}, {"movements": "hammer strength row", "sets": 2, "slot": 3}, {"movements": "machine lat raise", "sets": 2, "slot": 4}, {"movements": "pec deck", "sets": 2, "slot": 5}, {"movements": "straight bar pulldown", "sets": 2, "slot": 6}, {"movements": "ezbar curl", "sets": 2, "slot": 7}, {"movements": "bayesian curl", "sets": 2, "slot": 8}, {"movements": "smith jm press", "sets": 2, "slot": 9}, {"movements": "overhead cable extension", "sets": 2, "slot": 10}, {"movements": "face pull", "sets": 2, "slot": 11}], "variant": "active"}','backfill 2026-09-26: user confirms split unchanged since Sep 20',NULL,NULL,0);
INSERT INTO "state_change" VALUES(2,'program','active:L1','2026-09-20','2026-09-26T10:12:48','{"day": "L1", "slots": [], "variant": "active"}','{"day": "L1", "slots": [{"movements": "hack squat", "sets": 2, "slot": 1}, {"movements": "leg extension", "sets": 3, "slot": 2}, {"movements": "leg press", "sets": 2, "slot": 3}, {"movements": "seated leg curl", "sets": 3, "slot": 4}, {"movements": "adductor machine", "sets": 2, "slot": 5}, {"movements": "crunch machine", "sets": 2, "slot": 6}, {"movements": "cable crunch", "sets": 2, "slot": 7}, {"movements": "cable wrist curl", "sets": 3, "slot": 8}, {"movements": "cable reverse curl", "sets": 2, "slot": 9}], "variant": "active"}','backfill 2026-09-26: user confirms split unchanged since Sep 20',NULL,NULL,0);
INSERT INTO "state_change" VALUES(3,'program','active:U2','2026-09-20','2026-09-26T10:12:48','{"day": "U2", "slots": [], "variant": "active"}','{"day": "U2", "slots": [{"movements": "straight bar pulldown", "sets": 3, "slot": 1}, {"movements": "machine lat raise", "sets": 2, "slot": 2}, {"movements": "reverse-grip smith incline press", "sets": 3, "slot": 3}, {"movements": "cable lat raise", "sets": 2, "slot": 4}, {"movements": "hammer strength row", "sets": 2, "slot": 5}, {"movements": "incline dumbbell curl", "sets": 2, "slot": 6}, {"movements": "machine preacher curl", "sets": 2, "slot": 7}, {"movements": "ezbar skullcrusher", "sets": 2, "slot": 8}, {"movements": "cable pushdown", "sets": 2, "slot": 9}, {"movements": "rear delt cable fly", "sets": 2, "slot": 10}], "variant": "active"}','backfill 2026-09-26: user confirms split unchanged since Sep 20',NULL,NULL,0);
INSERT INTO "state_change" VALUES(4,'program','active:U3','2026-09-20','2026-09-26T10:12:48','{"day": "U3", "slots": [], "variant": "active"}','{"day": "U3", "slots": [{"movements": "hammer strength press", "sets": 2, "slot": 1}, {"movements": "dumbbell lat raise", "sets": 2, "slot": 2}, {"movements": "cable pullover", "sets": 2, "slot": 3}, {"movements": "cable lat raise", "sets": 2, "slot": 4}, {"movements": "pec deck", "sets": 2, "slot": 5}, {"movements": "hammer strength row", "sets": 2, "slot": 6}, {"movements": "ezbar curl", "sets": 2, "slot": 7}, {"movements": "bayesian curl", "sets": 2, "slot": 8}, {"movements": "smith jm press", "sets": 2, "slot": 9}, {"movements": "overhead cable extension", "sets": 2, "slot": 10}, {"movements": "face pull", "sets": 2, "slot": 11}], "variant": "active"}','backfill 2026-09-26: user confirms split unchanged since Sep 20',NULL,NULL,0);
INSERT INTO "state_change" VALUES(5,'program','active:L2','2026-09-20','2026-09-26T10:12:48','{"day": "L2", "slots": [], "variant": "active"}','{"day": "L2", "slots": [{"movements": "rdl", "sets": 3, "slot": 1}, {"movements": "leg press", "sets": 3, "slot": 2}, {"movements": "hack squat", "sets": 2, "slot": 3}, {"movements": "leg extension", "sets": 2, "slot": 4}, {"movements": "seated leg curl", "sets": 3, "slot": 5}, {"movements": "adductor machine", "sets": 3, "slot": 6}, {"movements": "crunch machine", "sets": 2, "slot": 7}, {"movements": "cable crunch", "sets": 2, "slot": 8}, {"movements": "cable wrist extension", "sets": 3, "slot": 9}], "variant": "active"}','backfill 2026-09-26: user confirms split unchanged since Sep 20',NULL,NULL,0);
INSERT INTO "state_change" VALUES(6,'program','active:U4','2026-09-20','2026-09-26T10:12:48','{"day": "U4", "slots": [], "variant": "active"}','{"day": "U4", "slots": [{"movements": "hammer strength row", "sets": 2, "slot": 1}, {"movements": "machine lat raise", "sets": 2, "slot": 2}, {"movements": "reverse-grip smith incline press", "sets": 3, "slot": 3}, {"movements": "dumbbell lat raise", "sets": 2, "slot": 4}, {"movements": "hammer strength press", "sets": 2, "slot": 5}, {"movements": "straight bar pulldown", "sets": 2, "slot": 6}, {"movements": "incline dumbbell curl", "sets": 2, "slot": 7}, {"movements": "machine preacher curl", "sets": 2, "slot": 8}, {"movements": "ezbar skullcrusher", "sets": 2, "slot": 9}, {"movements": "unilateral cable pushdown", "sets": 2, "slot": 10}, {"movements": "rear delt cable fly", "sets": 2, "slot": 11}], "variant": "active"}','backfill 2026-09-26: user confirms split unchanged since Sep 20',NULL,NULL,0);
INSERT INTO "state_change" VALUES(7,'rotation','rotation','2026-09-20','2026-09-26T10:12:48','{"rotation": []}','{"rotation": ["U1", "L1", "U2", null, "U3", "L2", "U4", null]}','backfill 2026-09-26: user confirms rotation in effect since Sep 20',NULL,NULL,0);
INSERT INTO "state_change" VALUES(8,'rotation','anchor','2026-09-22','2026-09-26T10:12:48','{"anchor_date": null, "position": null, "rotation": null}','{"anchor_date": "2026-09-22", "position": 0, "rotation": null}','backfill 2026-09-26: Sep 22 session matches U1, U1/L1/U2/rest/U3 sequence holds Sep 22-26',NULL,NULL,0);
INSERT INTO "state_change" VALUES(9,'rotation','anchor','2026-09-26','2026-09-26T10:12:48','{"anchor_date": null, "position": null, "rotation": null}','{"anchor_date": "2026-09-22", "position": 0, "rotation": null}','mid-rotation anchor, verified against logged sessions',NULL,NULL,0);
INSERT INTO "state_change" VALUES(10,'rule','9','2026-09-27','2026-09-27T08:58:57','{"action": "add", "expiry": null, "rule_id": 9, "status": null, "subject": null, "text": null}','{"action": "add", "expiry": null, "rule_id": 9, "status": "active", "subject": "coaching", "text": "got it / done means hit the prescribed target exactly, log it as-is"}','',NULL,NULL,0);
INSERT INTO "state_change" VALUES(11,'program','active:L2','2026-09-27','2026-09-27T09:53:03','{"day": "L2", "slots": [{"movements": "rdl", "sets": 3, "slot": 1}, {"movements": "leg press", "sets": 3, "slot": 2}, {"movements": "hack squat", "sets": 2, "slot": 3}, {"movements": "leg extension", "sets": 2, "slot": 4}, {"movements": "seated leg curl", "sets": 3, "slot": 5}, {"movements": "adductor machine", "sets": 3, "slot": 6}, {"movements": "crunch machine", "sets": 2, "slot": 7}, {"movements": "cable crunch", "sets": 2, "slot": 8}, {"movements": "cable wrist extension", "sets": 3, "slot": 9}], "variant": "active"}','{"day": "L2", "slots": [{"movements": "rdl", "sets": 3, "slot": 1}, {"movements": "leg press", "sets": 3, "slot": 2}, {"movements": "hack squat", "sets": 2, "slot": 3}, {"movements": "leg extension", "sets": 2, "slot": 4}, {"movements": "seated leg curl", "sets": 3, "slot": 5}, {"movements": "adductor machine", "sets": 3, "slot": 6}, {"movements": "crunch machine", "sets": 2, "slot": 7}, {"movements": "cable crunch", "sets": 2, "slot": 8}, {"movements": "cable reverse curl", "sets": 3, "slot": 9}], "variant": "active"}','wrist extension ROM feels off, no pain, swap to reverse curl',NULL,NULL,0);
INSERT INTO "state_change" VALUES(12,'program','active:L1','2026-09-27','2026-09-27T10:30:13','{"day": "L1", "slots": [{"movements": "hack squat", "sets": 2, "slot": 1}, {"movements": "leg extension", "sets": 3, "slot": 2}, {"movements": "leg press", "sets": 2, "slot": 3}, {"movements": "seated leg curl", "sets": 3, "slot": 4}, {"movements": "adductor machine", "sets": 2, "slot": 5}, {"movements": "crunch machine", "sets": 2, "slot": 6}, {"movements": "cable crunch", "sets": 2, "slot": 7}, {"movements": "cable wrist curl", "sets": 3, "slot": 8}, {"movements": "cable reverse curl", "sets": 2, "slot": 9}], "variant": "active"}','{"day": "L1", "slots": [{"movements": "hack squat", "sets": 2, "slot": 1}, {"movements": "leg extension", "sets": 3, "slot": 2}, {"movements": "leg press", "sets": 2, "slot": 3}, {"movements": "seated leg curl", "sets": 3, "slot": 4}, {"movements": "adductor machine", "sets": 2, "slot": 5}, {"movements": "crunch machine", "sets": 2, "slot": 6}, {"movements": "cable crunch", "sets": 2, "slot": 7}, {"movements": "cable wrist curl", "sets": 3, "slot": 8}, {"movements": "dumbbell reverse curl", "sets": 2, "slot": 9}], "variant": "active"}','cable EZ flips on swivel, wrists fight path; dumbbells free',NULL,NULL,0);
INSERT INTO "state_change" VALUES(13,'program','active:L2','2026-09-27','2026-09-27T10:30:13','{"day": "L2", "slots": [{"movements": "rdl", "sets": 3, "slot": 1}, {"movements": "leg press", "sets": 3, "slot": 2}, {"movements": "hack squat", "sets": 2, "slot": 3}, {"movements": "leg extension", "sets": 2, "slot": 4}, {"movements": "seated leg curl", "sets": 3, "slot": 5}, {"movements": "adductor machine", "sets": 3, "slot": 6}, {"movements": "crunch machine", "sets": 2, "slot": 7}, {"movements": "cable crunch", "sets": 2, "slot": 8}, {"movements": "cable reverse curl", "sets": 3, "slot": 9}], "variant": "active"}','{"day": "L2", "slots": [{"movements": "rdl", "sets": 3, "slot": 1}, {"movements": "leg press", "sets": 3, "slot": 2}, {"movements": "hack squat", "sets": 2, "slot": 3}, {"movements": "leg extension", "sets": 2, "slot": 4}, {"movements": "seated leg curl", "sets": 3, "slot": 5}, {"movements": "adductor machine", "sets": 3, "slot": 6}, {"movements": "crunch machine", "sets": 2, "slot": 7}, {"movements": "cable crunch", "sets": 2, "slot": 8}, {"movements": "dumbbell reverse curl", "sets": 3, "slot": 9}], "variant": "active"}','cable EZ flips on swivel, wrists fight path; dumbbells free',NULL,NULL,1);
INSERT INTO "state_change" VALUES(14,'rule','10','2026-10-01','2026-10-01T09:08:19','{"action": "add", "expiry": null, "rule_id": 10, "status": null, "subject": null, "text": null}','{"action": "add", "expiry": null, "rule_id": 10, "status": "active", "subject": "coaching", "text": "when a movement has a known starting weight, calculate off the total but always tell both: total plus starter and added split (e.g. 87 total = 57 starter + 30 added)"}','user asked at L1 start so no mental math at the machine',NULL,NULL,0);
INSERT INTO "state_change" VALUES(15,'rule','11','2026-10-01','2026-10-01T09:59:08','{"action": "add", "expiry": null, "rule_id": 11, "status": null, "subject": null, "text": null}','{"action": "add", "expiry": null, "rule_id": 11, "status": "active", "subject": "coaching", "text": "never prescribe over 12 reps for any movement; when reps would exceed 12, bump weight instead and keep target at 12 or below"}','user rejected 15-rep wrist curl target mid-L1; cap matches e1rm_cap_reps',NULL,NULL,0);
INSERT INTO "state_change" VALUES(16,'rotation','anchor','2026-10-04','2026-10-04T09:21:32','{"anchor_date": "2026-09-22", "position": 0, "rotation": null}','{"anchor_date": "2026-10-04", "position": 3, "rotation": null}','user sick Oct4, shifts everything 1 day forward: Oct4 rest, U3 Oct5, L2 Oct6',NULL,NULL,0);
CREATE TABLE workouts (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'done', 'rest')),
  notes TEXT NOT NULL DEFAULT ''
);
INSERT INTO "workouts" VALUES(2,'2026-09-20','rest','split transition friction, fewer rest days since last leg day than usual');
INSERT INTO "workouts" VALUES(3,'2026-09-21','rest','');
INSERT INTO "workouts" VALUES(4,'2026-09-22','done','U1 baseline. Came in slightly sore, 2d since last bench vs usual 3. JM first time to above Adam''s apple, fantastic. Bicep pump squeezed at bottom on JM and overhead.');
INSERT INTO "workouts" VALUES(5,'2026-09-23','done','L1 baseline. Cable crunch best ab feeling yet.');
INSERT INTO "workouts" VALUES(6,'2026-09-24','done','U2. Reverse-grip first time, wrists awkward then clicked. Hurry at end.');
INSERT INTO "workouts" VALUES(7,'2026-09-25','rest','planned');
INSERT INTO "workouts" VALUES(8,'2026-09-26','done','U3 U3, smith 60 accidental bad form, standard reset 50. BW 79.3.');
INSERT INTO "workouts" VALUES(9,'2026-09-27','done','L2 Legs wrecked but held all targets. Wrist extension ROM felt off, no pain, swapped slot to reverse curl.');
INSERT INTO "workouts" VALUES(10,'2026-09-28','done','U4 U4, had to cut last rear delt set, otherwise strong');
INSERT INTO "workouts" VALUES(11,'2026-09-29','rest','planned rest');
INSERT INTO "workouts" VALUES(12,'2026-09-30','done','U1 U1 solid. pulldown swapped after curls, backed off second. JM form dialed consistent.');
INSERT INTO "workouts" VALUES(13,'2026-10-01','done','L1 L1. Hams skipped sore from first RDL back, DB reverse curl skipped bus baseline next time. Wrist curl reseeded at 13.75.');
INSERT INTO "workouts" VALUES(14,'2026-10-02','done','U2 U2 solid, 10/10 PRs. pulldown/lat raise and hammer/curl order swapped for equipment, pulldown backed to 77 third.');
INSERT INTO "workouts" VALUES(15,'2026-10-03','rest','');
INSERT INTO "workouts" VALUES(16,'2026-10-04','rest','sick, slept terribly, resting instead of U3');
CREATE INDEX idx_sets_workout ON sets(workout_id);
CREATE INDEX idx_sets_exercise ON sets(exercise);
CREATE INDEX idx_bw_date ON bodyweight(date);
CREATE VIEW set_muscle AS
  SELECT s.id AS set_id, lm.muscle AS muscle FROM sets s JOIN lift_muscle lm USING (exercise);
CREATE UNIQUE INDEX idx_deload_active ON deload_state(scope, subject) WHERE cleared_on IS NULL;
CREATE INDEX idx_state_change_domain_subject_date
  ON state_change(domain, subject, date, created, id);
CREATE UNIQUE INDEX idx_state_change_sequence
  ON state_change(domain, subject, date, sequence);
COMMIT;
