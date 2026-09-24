BEGIN TRANSACTION;
CREATE TABLE autoreg_changes (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  action TEXT NOT NULL,
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
  action TEXT NOT NULL,
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
CREATE TABLE deload_state (
  id INTEGER PRIMARY KEY,
  scope TEXT NOT NULL,
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
  exercise TEXT NOT NULL,
  target_e1rm REAL NOT NULL,
  target_desc TEXT NOT NULL,
  deadline TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created TEXT NOT NULL
);
CREATE TABLE lift_muscle_map (
  exercise TEXT PRIMARY KEY,
  muscles TEXT NOT NULL,
  is_bodyweight_only INTEGER NOT NULL DEFAULT 0
);
INSERT INTO "lift_muscle_map" VALUES('back squat','quads,glutes',0);
INSERT INTO "lift_muscle_map" VALUES('dips','triceps',0);
INSERT INTO "lift_muscle_map" VALUES('flat barbell bench press','chest,front delts',0);
INSERT INTO "lift_muscle_map" VALUES('incline barbell bench press','chest,front delts',0);
INSERT INTO "lift_muscle_map" VALUES('reverse-grip smith incline press','chest',0);
INSERT INTO "lift_muscle_map" VALUES('hammer strength press','chest',0);
INSERT INTO "lift_muscle_map" VALUES('pec deck','chest',0);
INSERT INTO "lift_muscle_map" VALUES('hammer strength row','back',0);
INSERT INTO "lift_muscle_map" VALUES('straight bar pulldown','back',0);
INSERT INTO "lift_muscle_map" VALUES('cable pullover','back',0);
INSERT INTO "lift_muscle_map" VALUES('face pull','rear delts',0);
INSERT INTO "lift_muscle_map" VALUES('cable lat raise','side delts',0);
INSERT INTO "lift_muscle_map" VALUES('machine lat raise','side delts',0);
INSERT INTO "lift_muscle_map" VALUES('hack squat','quads',0);
INSERT INTO "lift_muscle_map" VALUES('leg press','quads,glutes',0);
INSERT INTO "lift_muscle_map" VALUES('rdl','hamstrings,glutes',0);
INSERT INTO "lift_muscle_map" VALUES('leg extension','quads',0);
INSERT INTO "lift_muscle_map" VALUES('seated leg curl','hamstrings',0);
INSERT INTO "lift_muscle_map" VALUES('lying leg curl','hamstrings',0);
INSERT INTO "lift_muscle_map" VALUES('adductor machine','adductors',0);
INSERT INTO "lift_muscle_map" VALUES('crunch machine','abs',0);
INSERT INTO "lift_muscle_map" VALUES('bayesian curl','biceps',0);
INSERT INTO "lift_muscle_map" VALUES('ezbar curl','biceps',0);
INSERT INTO "lift_muscle_map" VALUES('incline dumbbell curl','biceps',0);
INSERT INTO "lift_muscle_map" VALUES('rope hammer curl','biceps,forearms',0);
INSERT INTO "lift_muscle_map" VALUES('cable reverse curl','forearms',0);
INSERT INTO "lift_muscle_map" VALUES('cable pushdown','triceps',0);
INSERT INTO "lift_muscle_map" VALUES('unilateral cable pushdown','triceps',0);
INSERT INTO "lift_muscle_map" VALUES('ezbar skullcrusher','triceps',0);
INSERT INTO "lift_muscle_map" VALUES('cable wrist curl','forearms',0);
INSERT INTO "lift_muscle_map" VALUES('cable wrist extension','forearms',0);
INSERT INTO "lift_muscle_map" VALUES('dumbbell lat raise','side delts',0);
INSERT INTO "lift_muscle_map" VALUES('smith jm press','triceps',0);
INSERT INTO "lift_muscle_map" VALUES('overhead cable extension','triceps',0);
INSERT INTO "lift_muscle_map" VALUES('hanging leg raise','abs',1);
INSERT INTO "lift_muscle_map" VALUES('rear delt cable fly','rear delts',0);
INSERT INTO "lift_muscle_map" VALUES('machine preacher curl','biceps',0);
INSERT INTO "lift_muscle_map" VALUES('cable crunch','abs',0);
CREATE TABLE meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
INSERT INTO "meta" VALUES('last_compacted','never');
INSERT INTO "meta" VALUES('rotation','["U1", "L1", "U2", "rest", "U3", "L2", "U4", "rest"]');
INSERT INTO "meta" VALUES('compaction_postponed_until','2026-10-01');
CREATE TABLE movement_notes (
  id INTEGER PRIMARY KEY,
  exercise TEXT NOT NULL,
  note TEXT NOT NULL,
  created TEXT NOT NULL
);
INSERT INTO "movement_notes" VALUES(1,'dips','my form, elbows tucked, triceps main','2026-09-20T15:14:08');
INSERT INTO "movement_notes" VALUES(2,'flat barbell bench press','triceps excluded by convention','2026-09-20T15:14:08');
INSERT INTO "movement_notes" VALUES(3,'reverse-grip smith incline press','upper chest emphasis','2026-09-20T15:14:08');
INSERT INTO "movement_notes" VALUES(5,'hammer strength row','logged as total both sides (45 per side = 90)','2026-09-20T15:14:08');
INSERT INTO "movement_notes" VALUES(6,'straight bar pulldown','attachment matters','2026-09-20T15:14:08');
INSERT INTO "movement_notes" VALUES(7,'straight bar pulldown','stack jumps 10kg: 47, 57, 67, 77, 87, 97, 107, 117, 127','2026-09-20T15:14:08');
INSERT INTO "movement_notes" VALUES(8,'cable lat raise','stack micro-increments .625, all cable stacks share this','2026-09-22T09:19:36');
INSERT INTO "movement_notes" VALUES(9,'machine lat raise','2.5kg increments','2026-09-22T09:39:04');
INSERT INTO "movement_notes" VALUES(10,'smith jm press','bench 2 incline','2026-09-22T10:21:15');
INSERT INTO "movement_notes" VALUES(11,'overhead cable extension','cable just under height 8','2026-09-22T10:27:37');
INSERT INTO "movement_notes" VALUES(12,'seated leg curl','stack steps: 50 57 63 70 77 84 90 97 (6-7 increments)','2026-09-23T08:39:43');
INSERT INTO "movement_notes" VALUES(13,'adductor machine','width setting 7','2026-09-23T08:49:04');
INSERT INTO "movement_notes" VALUES(14,'adductor machine','stack increments 3.75','2026-09-23T08:50:46');
INSERT INTO "movement_notes" VALUES(15,'crunch machine','single loading horn, starter unknown, logged weight is plates only; seat height middle (unnumbered)','2026-09-23T09:01:31');
INSERT INTO "movement_notes" VALUES(16,'cable reverse curl','bilateral','2026-09-23T09:39:08');
INSERT INTO "movement_notes" VALUES(17,'cable wrist curl','unilateral, log weaker side with L/R when sides diverge','2026-09-23T09:39:08');
INSERT INTO "movement_notes" VALUES(18,'reverse-grip smith incline press','incline 2','2026-09-24T09:36:23');
INSERT INTO "movement_notes" VALUES(19,'incline dumbbell curl','incline 4','2026-09-24T09:58:14');
INSERT INTO "movement_notes" VALUES(20,'machine preacher curl','stack 5,10,15,20,25,32,39,46,53,60,67 plus 2 unmarked micros at top','2026-09-24T10:07:12');
INSERT INTO "movement_notes" VALUES(21,'machine preacher curl','top 2 micros guessed 1.75 each','2026-09-24T10:08:31');
INSERT INTO "movement_notes" VALUES(22,'ezbar skullcrusher','ez bar guessed 7.5, totals include bar','2026-09-24T10:13:38');
INSERT INTO "movement_notes" VALUES(23,'rear delt cable fly','height under 6','2026-09-24T10:24:48');
CREATE TABLE priority (
  muscle TEXT PRIMARY KEY,
  tier TEXT NOT NULL,
  since TEXT NOT NULL,
  until TEXT
);
CREATE TABLE progression (
  id INTEGER PRIMARY KEY,
  workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
  exercise TEXT NOT NULL,
  verdict TEXT NOT NULL,
  next_target TEXT NOT NULL,
  direction TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  created TEXT NOT NULL,
  UNIQUE (workout_id, exercise)
);
INSERT INTO "progression" VALUES(1,4,'incline barbell bench press','baseline','75x6','flat','','2026-09-22T17:11:12');
INSERT INTO "progression" VALUES(2,4,'cable lat raise','baseline','11.25x8','flat','','2026-09-22T17:11:12');
INSERT INTO "progression" VALUES(3,4,'hammer strength row','baseline','90x8','flat','','2026-09-22T17:11:12');
INSERT INTO "progression" VALUES(4,4,'machine lat raise','baseline','60x9','flat','','2026-09-22T17:13:42');
INSERT INTO "progression" VALUES(5,4,'pec deck','baseline','85x8','flat','','2026-09-22T17:13:42');
INSERT INTO "progression" VALUES(6,4,'straight bar pulldown','baseline','77x8','flat','','2026-09-22T17:13:42');
INSERT INTO "progression" VALUES(7,4,'ezbar curl','baseline','35x6','flat','','2026-09-22T17:11:12');
INSERT INTO "progression" VALUES(8,4,'bayesian curl','baseline','11.25x8','flat','','2026-09-22T17:11:12');
INSERT INTO "progression" VALUES(9,4,'smith jm press','baseline','30x8','flat','','2026-09-22T17:13:42');
INSERT INTO "progression" VALUES(10,4,'overhead cable extension','baseline','25x12','up','','2026-09-22T17:13:42');
INSERT INTO "progression" VALUES(11,4,'face pull','baseline','38.75x10','flat','','2026-09-22T17:11:12');
INSERT INTO "progression" VALUES(12,5,'hack squat','baseline','87x8','flat','','2026-09-23T09:35:01');
INSERT INTO "progression" VALUES(13,5,'leg extension','baseline','89x10','flat','','2026-09-23T09:35:01');
INSERT INTO "progression" VALUES(14,5,'leg press','baseline','115x10','flat','','2026-09-23T09:35:01');
INSERT INTO "progression" VALUES(15,5,'seated leg curl','baseline','63x8','flat','','2026-09-23T09:35:02');
INSERT INTO "progression" VALUES(16,5,'adductor machine','baseline','41.25x12','flat','','2026-09-23T09:35:02');
INSERT INTO "progression" VALUES(17,5,'crunch machine','baseline','35x10','flat','','2026-09-23T09:35:02');
INSERT INTO "progression" VALUES(18,5,'cable crunch','baseline','28.75x11','flat','','2026-09-23T09:35:02');
INSERT INTO "progression" VALUES(19,5,'cable wrist curl','baseline','11.25x15','flat','','2026-09-23T09:35:02');
INSERT INTO "progression" VALUES(20,5,'cable reverse curl','baseline','16.25x11','flat','','2026-09-23T09:35:02');
INSERT INTO "progression" VALUES(21,6,'straight bar pulldown','hit','87x8','up','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(22,6,'machine lat raise','hit','62.5x10','up','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(23,6,'reverse-grip smith incline press','baseline','20x10','flat','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(24,6,'cable lat raise','hit','11.875x10','up','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(25,6,'hammer strength row','hit','95x10','up','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(26,6,'incline dumbbell curl','baseline','12.5x12','flat','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(27,6,'machine preacher curl','baseline','46x11','flat','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(28,6,'ezbar skullcrusher','baseline','37.5x11','flat','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(29,6,'cable pushdown','baseline','28.75x12','flat','','2026-09-24T10:29:20');
INSERT INTO "progression" VALUES(30,6,'rear delt cable fly','baseline','8.75x11','flat','','2026-09-24T10:29:20');
CREATE TABLE rules (
  id INTEGER PRIMARY KEY,
  subject TEXT NOT NULL,
  text TEXT NOT NULL,
  start_date TEXT NOT NULL,
  expiry TEXT,
  status TEXT NOT NULL DEFAULT 'active',
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
CREATE TABLE set_muscles (
  set_id INTEGER NOT NULL REFERENCES sets(id) ON DELETE CASCADE,
  muscle TEXT NOT NULL,
  PRIMARY KEY (set_id, muscle)
);
INSERT INTO "set_muscles" VALUES(1,'chest');
INSERT INTO "set_muscles" VALUES(1,'front delts');
INSERT INTO "set_muscles" VALUES(2,'chest');
INSERT INTO "set_muscles" VALUES(2,'front delts');
INSERT INTO "set_muscles" VALUES(3,'chest');
INSERT INTO "set_muscles" VALUES(3,'front delts');
INSERT INTO "set_muscles" VALUES(4,'side delts');
INSERT INTO "set_muscles" VALUES(5,'side delts');
INSERT INTO "set_muscles" VALUES(6,'back');
INSERT INTO "set_muscles" VALUES(7,'back');
INSERT INTO "set_muscles" VALUES(8,'side delts');
INSERT INTO "set_muscles" VALUES(9,'side delts');
INSERT INTO "set_muscles" VALUES(10,'chest');
INSERT INTO "set_muscles" VALUES(11,'chest');
INSERT INTO "set_muscles" VALUES(12,'back');
INSERT INTO "set_muscles" VALUES(13,'back');
INSERT INTO "set_muscles" VALUES(14,'biceps');
INSERT INTO "set_muscles" VALUES(15,'biceps');
INSERT INTO "set_muscles" VALUES(16,'biceps');
INSERT INTO "set_muscles" VALUES(17,'biceps');
INSERT INTO "set_muscles" VALUES(18,'triceps');
INSERT INTO "set_muscles" VALUES(19,'triceps');
INSERT INTO "set_muscles" VALUES(20,'triceps');
INSERT INTO "set_muscles" VALUES(21,'triceps');
INSERT INTO "set_muscles" VALUES(22,'rear delts');
INSERT INTO "set_muscles" VALUES(23,'rear delts');
INSERT INTO "set_muscles" VALUES(24,'quads');
INSERT INTO "set_muscles" VALUES(25,'quads');
INSERT INTO "set_muscles" VALUES(26,'quads');
INSERT INTO "set_muscles" VALUES(27,'quads');
INSERT INTO "set_muscles" VALUES(28,'quads');
INSERT INTO "set_muscles" VALUES(29,'quads');
INSERT INTO "set_muscles" VALUES(29,'glutes');
INSERT INTO "set_muscles" VALUES(30,'quads');
INSERT INTO "set_muscles" VALUES(30,'glutes');
INSERT INTO "set_muscles" VALUES(31,'hamstrings');
INSERT INTO "set_muscles" VALUES(32,'hamstrings');
INSERT INTO "set_muscles" VALUES(33,'hamstrings');
INSERT INTO "set_muscles" VALUES(34,'adductors');
INSERT INTO "set_muscles" VALUES(35,'adductors');
INSERT INTO "set_muscles" VALUES(36,'abs');
INSERT INTO "set_muscles" VALUES(37,'abs');
INSERT INTO "set_muscles" VALUES(38,'abs');
INSERT INTO "set_muscles" VALUES(39,'abs');
INSERT INTO "set_muscles" VALUES(40,'forearms');
INSERT INTO "set_muscles" VALUES(41,'forearms');
INSERT INTO "set_muscles" VALUES(42,'forearms');
INSERT INTO "set_muscles" VALUES(43,'forearms');
INSERT INTO "set_muscles" VALUES(44,'forearms');
INSERT INTO "set_muscles" VALUES(45,'back');
INSERT INTO "set_muscles" VALUES(46,'back');
INSERT INTO "set_muscles" VALUES(47,'back');
INSERT INTO "set_muscles" VALUES(48,'side delts');
INSERT INTO "set_muscles" VALUES(49,'side delts');
INSERT INTO "set_muscles" VALUES(50,'chest');
INSERT INTO "set_muscles" VALUES(51,'chest');
INSERT INTO "set_muscles" VALUES(52,'chest');
INSERT INTO "set_muscles" VALUES(53,'side delts');
INSERT INTO "set_muscles" VALUES(54,'side delts');
INSERT INTO "set_muscles" VALUES(55,'back');
INSERT INTO "set_muscles" VALUES(56,'back');
INSERT INTO "set_muscles" VALUES(57,'biceps');
INSERT INTO "set_muscles" VALUES(58,'biceps');
INSERT INTO "set_muscles" VALUES(59,'biceps');
INSERT INTO "set_muscles" VALUES(60,'biceps');
INSERT INTO "set_muscles" VALUES(61,'triceps');
INSERT INTO "set_muscles" VALUES(62,'triceps');
INSERT INTO "set_muscles" VALUES(63,'triceps');
INSERT INTO "set_muscles" VALUES(64,'triceps');
INSERT INTO "set_muscles" VALUES(65,'rear delts');
INSERT INTO "set_muscles" VALUES(66,'rear delts');
CREATE TABLE sets (
  id INTEGER PRIMARY KEY,
  workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
  exercise TEXT NOT NULL,
  weight REAL NOT NULL,
  reps INTEGER NOT NULL,
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
CREATE TABLE splits (
  id INTEGER PRIMARY KEY,
  variant TEXT NOT NULL,
  day TEXT NOT NULL,
  slot INTEGER NOT NULL,
  movements TEXT NOT NULL,
  sets INTEGER NOT NULL,
  UNIQUE (variant, day, slot)
);
INSERT INTO "splits" VALUES(95,'active','U1',1,'incline barbell bench press',3);
INSERT INTO "splits" VALUES(96,'active','U1',2,'cable lat raise',2);
INSERT INTO "splits" VALUES(97,'active','U1',3,'hammer strength row',2);
INSERT INTO "splits" VALUES(98,'active','U1',4,'machine lat raise',2);
INSERT INTO "splits" VALUES(99,'active','U1',5,'pec deck',2);
INSERT INTO "splits" VALUES(100,'active','U1',6,'straight bar pulldown',2);
INSERT INTO "splits" VALUES(101,'active','U1',7,'ezbar curl',2);
INSERT INTO "splits" VALUES(102,'active','U1',8,'bayesian curl',2);
INSERT INTO "splits" VALUES(103,'active','U1',9,'smith jm press',2);
INSERT INTO "splits" VALUES(104,'active','U1',10,'overhead cable extension',2);
INSERT INTO "splits" VALUES(105,'active','U1',11,'face pull',2);
INSERT INTO "splits" VALUES(106,'active','L1',1,'hack squat',2);
INSERT INTO "splits" VALUES(107,'active','L1',2,'leg extension',3);
INSERT INTO "splits" VALUES(108,'active','L1',3,'leg press',2);
INSERT INTO "splits" VALUES(109,'active','L1',4,'seated leg curl',3);
INSERT INTO "splits" VALUES(110,'active','L1',5,'adductor machine',2);
INSERT INTO "splits" VALUES(111,'active','L1',6,'crunch machine',2);
INSERT INTO "splits" VALUES(112,'active','L1',7,'cable crunch',2);
INSERT INTO "splits" VALUES(113,'active','L1',8,'cable wrist curl',3);
INSERT INTO "splits" VALUES(114,'active','L1',9,'cable reverse curl',2);
INSERT INTO "splits" VALUES(115,'active','U2',1,'straight bar pulldown',3);
INSERT INTO "splits" VALUES(116,'active','U2',2,'machine lat raise',2);
INSERT INTO "splits" VALUES(117,'active','U2',3,'reverse-grip smith incline press',3);
INSERT INTO "splits" VALUES(118,'active','U2',4,'cable lat raise',2);
INSERT INTO "splits" VALUES(119,'active','U2',5,'hammer strength row',2);
INSERT INTO "splits" VALUES(120,'active','U2',6,'incline dumbbell curl',2);
INSERT INTO "splits" VALUES(121,'active','U2',7,'machine preacher curl',2);
INSERT INTO "splits" VALUES(122,'active','U2',8,'ezbar skullcrusher',2);
INSERT INTO "splits" VALUES(123,'active','U2',9,'cable pushdown',2);
INSERT INTO "splits" VALUES(124,'active','U2',10,'rear delt cable fly',2);
INSERT INTO "splits" VALUES(125,'active','U3',1,'hammer strength press',2);
INSERT INTO "splits" VALUES(126,'active','U3',2,'dumbbell lat raise',2);
INSERT INTO "splits" VALUES(127,'active','U3',3,'cable pullover',2);
INSERT INTO "splits" VALUES(128,'active','U3',4,'cable lat raise',2);
INSERT INTO "splits" VALUES(129,'active','U3',5,'pec deck',2);
INSERT INTO "splits" VALUES(130,'active','U3',6,'hammer strength row',2);
INSERT INTO "splits" VALUES(131,'active','U3',7,'ezbar curl',2);
INSERT INTO "splits" VALUES(132,'active','U3',8,'bayesian curl',2);
INSERT INTO "splits" VALUES(133,'active','U3',9,'smith jm press',2);
INSERT INTO "splits" VALUES(134,'active','U3',10,'overhead cable extension',2);
INSERT INTO "splits" VALUES(135,'active','U3',11,'face pull',2);
INSERT INTO "splits" VALUES(136,'active','L2',1,'rdl',3);
INSERT INTO "splits" VALUES(137,'active','L2',2,'leg press',3);
INSERT INTO "splits" VALUES(138,'active','L2',3,'hack squat',2);
INSERT INTO "splits" VALUES(139,'active','L2',4,'leg extension',2);
INSERT INTO "splits" VALUES(140,'active','L2',5,'seated leg curl',3);
INSERT INTO "splits" VALUES(141,'active','L2',6,'adductor machine',3);
INSERT INTO "splits" VALUES(142,'active','L2',7,'crunch machine',2);
INSERT INTO "splits" VALUES(143,'active','L2',8,'cable crunch',2);
INSERT INTO "splits" VALUES(144,'active','L2',9,'cable wrist extension',3);
INSERT INTO "splits" VALUES(145,'active','U4',1,'hammer strength row',2);
INSERT INTO "splits" VALUES(146,'active','U4',2,'machine lat raise',2);
INSERT INTO "splits" VALUES(147,'active','U4',3,'reverse-grip smith incline press',3);
INSERT INTO "splits" VALUES(148,'active','U4',4,'dumbbell lat raise',2);
INSERT INTO "splits" VALUES(149,'active','U4',5,'hammer strength press',2);
INSERT INTO "splits" VALUES(150,'active','U4',6,'straight bar pulldown',2);
INSERT INTO "splits" VALUES(151,'active','U4',7,'incline dumbbell curl',2);
INSERT INTO "splits" VALUES(152,'active','U4',8,'machine preacher curl',2);
INSERT INTO "splits" VALUES(153,'active','U4',9,'ezbar skullcrusher',2);
INSERT INTO "splits" VALUES(154,'active','U4',10,'unilateral cable pushdown',2);
INSERT INTO "splits" VALUES(155,'active','U4',11,'rear delt cable fly',2);
INSERT INTO "splits" VALUES(156,'baseline','U1',1,'incline barbell bench press',3);
INSERT INTO "splits" VALUES(157,'baseline','U1',2,'cable lat raise',2);
INSERT INTO "splits" VALUES(158,'baseline','U1',3,'hammer strength row',2);
INSERT INTO "splits" VALUES(159,'baseline','U1',4,'machine lat raise',2);
INSERT INTO "splits" VALUES(160,'baseline','U1',5,'pec deck',2);
INSERT INTO "splits" VALUES(161,'baseline','U1',6,'straight bar pulldown',2);
INSERT INTO "splits" VALUES(162,'baseline','U1',7,'ezbar curl',2);
INSERT INTO "splits" VALUES(163,'baseline','U1',8,'bayesian curl',2);
INSERT INTO "splits" VALUES(164,'baseline','U1',9,'smith jm press',2);
INSERT INTO "splits" VALUES(165,'baseline','U1',10,'overhead cable extension',2);
INSERT INTO "splits" VALUES(166,'baseline','U1',11,'face pull',2);
INSERT INTO "splits" VALUES(167,'baseline','L1',1,'hack squat',2);
INSERT INTO "splits" VALUES(168,'baseline','L1',2,'leg extension',3);
INSERT INTO "splits" VALUES(169,'baseline','L1',3,'leg press',2);
INSERT INTO "splits" VALUES(170,'baseline','L1',4,'seated leg curl',3);
INSERT INTO "splits" VALUES(171,'baseline','L1',5,'adductor machine',2);
INSERT INTO "splits" VALUES(172,'baseline','L1',6,'crunch machine',2);
INSERT INTO "splits" VALUES(173,'baseline','L1',7,'hanging leg raise',2);
INSERT INTO "splits" VALUES(174,'baseline','L1',8,'cable wrist curl',2);
INSERT INTO "splits" VALUES(175,'baseline','L1',9,'cable reverse curl',2);
INSERT INTO "splits" VALUES(176,'baseline','U2',1,'straight bar pulldown',3);
INSERT INTO "splits" VALUES(177,'baseline','U2',2,'machine lat raise',2);
INSERT INTO "splits" VALUES(178,'baseline','U2',3,'reverse-grip smith incline press',3);
INSERT INTO "splits" VALUES(179,'baseline','U2',4,'cable lat raise',2);
INSERT INTO "splits" VALUES(180,'baseline','U2',5,'hammer strength row',2);
INSERT INTO "splits" VALUES(181,'baseline','U2',6,'incline dumbbell curl',2);
INSERT INTO "splits" VALUES(182,'baseline','U2',7,'machine preacher curl',2);
INSERT INTO "splits" VALUES(183,'baseline','U2',8,'ezbar skullcrusher',2);
INSERT INTO "splits" VALUES(184,'baseline','U2',9,'cable pushdown',2);
INSERT INTO "splits" VALUES(185,'baseline','U2',10,'rear delt cable fly',2);
INSERT INTO "splits" VALUES(186,'baseline','U3',1,'hammer strength press',2);
INSERT INTO "splits" VALUES(187,'baseline','U3',2,'dumbbell lat raise',2);
INSERT INTO "splits" VALUES(188,'baseline','U3',3,'cable pullover',2);
INSERT INTO "splits" VALUES(189,'baseline','U3',4,'cable lat raise',2);
INSERT INTO "splits" VALUES(190,'baseline','U3',5,'pec deck',2);
INSERT INTO "splits" VALUES(191,'baseline','U3',6,'hammer strength row',2);
INSERT INTO "splits" VALUES(192,'baseline','U3',7,'ezbar curl',2);
INSERT INTO "splits" VALUES(193,'baseline','U3',8,'bayesian curl',2);
INSERT INTO "splits" VALUES(194,'baseline','U3',9,'overhead cable extension',2);
INSERT INTO "splits" VALUES(195,'baseline','U3',10,'unilateral cable pushdown',2);
INSERT INTO "splits" VALUES(196,'baseline','U3',11,'face pull',2);
INSERT INTO "splits" VALUES(197,'baseline','L2',1,'rdl',3);
INSERT INTO "splits" VALUES(198,'baseline','L2',2,'leg press',3);
INSERT INTO "splits" VALUES(199,'baseline','L2',3,'hack squat',2);
INSERT INTO "splits" VALUES(200,'baseline','L2',4,'leg extension',2);
INSERT INTO "splits" VALUES(201,'baseline','L2',5,'seated leg curl',3);
INSERT INTO "splits" VALUES(202,'baseline','L2',6,'adductor machine',3);
INSERT INTO "splits" VALUES(203,'baseline','L2',7,'crunch machine',2);
INSERT INTO "splits" VALUES(204,'baseline','L2',8,'hanging leg raise',2);
INSERT INTO "splits" VALUES(205,'baseline','L2',9,'cable wrist extension',2);
INSERT INTO "splits" VALUES(206,'baseline','U4',1,'hammer strength row',2);
INSERT INTO "splits" VALUES(207,'baseline','U4',2,'machine lat raise',2);
INSERT INTO "splits" VALUES(208,'baseline','U4',3,'reverse-grip smith incline press',3);
INSERT INTO "splits" VALUES(209,'baseline','U4',4,'dumbbell lat raise',2);
INSERT INTO "splits" VALUES(210,'baseline','U4',5,'hammer strength press',2);
INSERT INTO "splits" VALUES(211,'baseline','U4',6,'straight bar pulldown',2);
INSERT INTO "splits" VALUES(212,'baseline','U4',7,'incline dumbbell curl',2);
INSERT INTO "splits" VALUES(213,'baseline','U4',8,'machine preacher curl',2);
INSERT INTO "splits" VALUES(214,'baseline','U4',9,'smith jm press',2);
INSERT INTO "splits" VALUES(215,'baseline','U4',10,'ezbar skullcrusher',2);
INSERT INTO "splits" VALUES(216,'baseline','U4',11,'rear delt cable fly',2);
CREATE TABLE workouts (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  notes TEXT NOT NULL DEFAULT ''
);
INSERT INTO "workouts" VALUES(2,'2026-09-20','rest','split transition friction, fewer rest days since last leg day than usual');
INSERT INTO "workouts" VALUES(3,'2026-09-21','rest','');
INSERT INTO "workouts" VALUES(4,'2026-09-22','done','U1 baseline. Came in slightly sore, 2d since last bench vs usual 3. JM first time to above Adam''s apple, fantastic. Bicep pump squeezed at bottom on JM and overhead.');
INSERT INTO "workouts" VALUES(5,'2026-09-23','done','L1 baseline. Cable crunch best ab feeling yet.');
INSERT INTO "workouts" VALUES(6,'2026-09-24','done','U2. Reverse-grip first time, wrists awkward then clicked. Hurry at end.');
CREATE INDEX idx_sets_workout ON sets(workout_id);
CREATE INDEX idx_sets_exercise ON sets(exercise);
CREATE INDEX idx_bw_date ON bodyweight(date);
CREATE UNIQUE INDEX idx_deload_active ON deload_state(scope, subject) WHERE cleared_on IS NULL;
COMMIT;
