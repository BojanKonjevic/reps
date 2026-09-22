BEGIN TRANSACTION;
CREATE TABLE bodyweight (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  kg REAL NOT NULL,
  note TEXT NOT NULL DEFAULT ''
);
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
INSERT INTO "progression" VALUES(1,4,'incline barbell bench press','baseline','75','flat','','2026-09-22T10:41:27');
INSERT INTO "progression" VALUES(2,4,'cable lat raise','baseline','11.25','flat','','2026-09-22T10:41:27');
INSERT INTO "progression" VALUES(3,4,'hammer strength row','baseline','90','flat','','2026-09-22T10:41:27');
INSERT INTO "progression" VALUES(4,4,'machine lat raise','baseline','60','flat','','2026-09-22T10:41:27');
INSERT INTO "progression" VALUES(5,4,'pec deck','baseline','85','flat','','2026-09-22T10:41:27');
INSERT INTO "progression" VALUES(6,4,'straight bar pulldown','baseline','77','flat','','2026-09-22T10:41:27');
INSERT INTO "progression" VALUES(7,4,'ezbar curl','baseline','35','flat','','2026-09-22T10:41:27');
INSERT INTO "progression" VALUES(8,4,'bayesian curl','baseline','11.25','flat','','2026-09-22T10:41:27');
INSERT INTO "progression" VALUES(9,4,'smith jm press','baseline','30','flat','','2026-09-22T10:41:27');
INSERT INTO "progression" VALUES(10,4,'overhead cable extension','baseline','25','up','','2026-09-22T10:41:27');
INSERT INTO "progression" VALUES(11,4,'face pull','baseline','38.75','flat','','2026-09-22T10:41:27');
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
CREATE INDEX idx_sets_workout ON sets(workout_id);
CREATE INDEX idx_sets_exercise ON sets(exercise);
CREATE INDEX idx_bw_date ON bodyweight(date);
CREATE UNIQUE INDEX idx_deload_active ON deload_state(scope, subject) WHERE cleared_on IS NULL;
COMMIT;
