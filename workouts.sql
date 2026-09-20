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
INSERT INTO "lift_muscle_map" VALUES('flat barbell bench press','chest,front delt',0);
INSERT INTO "lift_muscle_map" VALUES('incline barbell bench press','chest,front delt',0);
INSERT INTO "lift_muscle_map" VALUES('reverse-grip smith incline press','chest',0);
INSERT INTO "lift_muscle_map" VALUES('hammer strength press','chest',0);
INSERT INTO "lift_muscle_map" VALUES('pec deck','chest',0);
INSERT INTO "lift_muscle_map" VALUES('hammer strength row','back',0);
INSERT INTO "lift_muscle_map" VALUES('straight bar pulldown','back',0);
INSERT INTO "lift_muscle_map" VALUES('cable pullover','back',0);
INSERT INTO "lift_muscle_map" VALUES('face pull','rear delt',0);
INSERT INTO "lift_muscle_map" VALUES('cable rear delt fly','rear delt',0);
INSERT INTO "lift_muscle_map" VALUES('cable lat raise','side delt',0);
INSERT INTO "lift_muscle_map" VALUES('machine lat raise','side delt',0);
INSERT INTO "lift_muscle_map" VALUES('hack squat','quads',0);
INSERT INTO "lift_muscle_map" VALUES('leg press','quads,glutes',0);
INSERT INTO "lift_muscle_map" VALUES('rdl','hamstrings,glutes',0);
INSERT INTO "lift_muscle_map" VALUES('leg extension','quads',0);
INSERT INTO "lift_muscle_map" VALUES('seated leg curl','hamstrings',0);
INSERT INTO "lift_muscle_map" VALUES('lying leg curl','hamstrings',0);
INSERT INTO "lift_muscle_map" VALUES('adductor machine','adductors',0);
INSERT INTO "lift_muscle_map" VALUES('crunch machine','abs',0);
INSERT INTO "lift_muscle_map" VALUES('bayesian curl','biceps',0);
INSERT INTO "lift_muscle_map" VALUES('preacher curl','biceps',0);
INSERT INTO "lift_muscle_map" VALUES('ezbar curl','biceps',0);
INSERT INTO "lift_muscle_map" VALUES('incline dumbbell curl','biceps',0);
INSERT INTO "lift_muscle_map" VALUES('rope hammer curl','biceps,forearms',0);
INSERT INTO "lift_muscle_map" VALUES('cable reverse curl','forearms',0);
INSERT INTO "lift_muscle_map" VALUES('cable pushdown','triceps',0);
INSERT INTO "lift_muscle_map" VALUES('unilateral cable pushdown','triceps',0);
INSERT INTO "lift_muscle_map" VALUES('ezbar skullcrusher','triceps',0);
INSERT INTO "lift_muscle_map" VALUES('cable wrist curl','forearms',0);
INSERT INTO "lift_muscle_map" VALUES('cable wrist extension','forearms',0);
INSERT INTO "lift_muscle_map" VALUES('machine shoulder press','front delt',0);
CREATE TABLE meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
INSERT INTO "meta" VALUES('last_compacted','never');
INSERT INTO "meta" VALUES('rotation','["Upper A", "Lower A", "Upper B", "rest", "Upper C", "Lower B", "rest"]');
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
INSERT INTO "movement_notes" VALUES(4,'machine shoulder press','neutral grip, slight lean for upper chest','2026-09-20T15:14:08');
INSERT INTO "movement_notes" VALUES(5,'hammer strength row','logged as total both sides (45 per side = 90)','2026-09-20T15:14:08');
INSERT INTO "movement_notes" VALUES(6,'straight bar pulldown','attachment matters, logged under this name, not lat pulldown','2026-09-20T15:14:08');
INSERT INTO "movement_notes" VALUES(7,'straight bar pulldown','stack jumps 10kg: 47, 57, 67, 77, 87, 97, 107, 117, 127','2026-09-20T15:14:08');
INSERT INTO "movement_notes" VALUES(8,'face pull','max height','2026-09-20T15:14:08');
INSERT INTO "movement_notes" VALUES(9,'bayesian curl','cable height below 8','2026-09-20T15:14:08');
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
INSERT INTO "progression" VALUES(1,1,'incline barbell bench press','baseline','80x6','flat','','2026-09-20T15:10:13');
INSERT INTO "progression" VALUES(2,1,'hammer strength row','baseline','90x9','flat','','2026-09-20T15:10:13');
INSERT INTO "progression" VALUES(3,1,'pec deck','baseline','80x13','flat','','2026-09-20T15:10:13');
INSERT INTO "progression" VALUES(4,1,'straight bar pulldown','baseline','87x7','flat','','2026-09-20T15:10:13');
INSERT INTO "progression" VALUES(5,1,'machine shoulder press','baseline','40x9','flat','returning','2026-09-20T15:58:07');
INSERT INTO "progression" VALUES(6,1,'cable lat raise','baseline','11.25x13','flat','','2026-09-20T15:10:13');
INSERT INTO "progression" VALUES(7,1,'bayesian curl','baseline','13.75x10','flat','','2026-09-20T15:10:13');
INSERT INTO "progression" VALUES(8,1,'preacher curl','baseline','46x8','flat','','2026-09-20T15:10:13');
INSERT INTO "progression" VALUES(9,1,'cable pushdown','baseline','31.25x12','flat','','2026-09-20T15:10:13');
INSERT INTO "progression" VALUES(10,1,'cable reverse curl','baseline','11.25x13','flat','new','2026-09-20T15:58:08');
INSERT INTO "progression" VALUES(11,1,'face pull','baseline','38.75x12','flat','','2026-09-20T15:10:13');
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
CREATE TABLE set_muscles (
  set_id INTEGER NOT NULL REFERENCES sets(id) ON DELETE CASCADE,
  muscle TEXT NOT NULL,
  PRIMARY KEY (set_id, muscle)
);
INSERT INTO "set_muscles" VALUES(1,'chest');
INSERT INTO "set_muscles" VALUES(1,'front delt');
INSERT INTO "set_muscles" VALUES(2,'chest');
INSERT INTO "set_muscles" VALUES(2,'front delt');
INSERT INTO "set_muscles" VALUES(3,'chest');
INSERT INTO "set_muscles" VALUES(3,'front delt');
INSERT INTO "set_muscles" VALUES(4,'back');
INSERT INTO "set_muscles" VALUES(5,'back');
INSERT INTO "set_muscles" VALUES(6,'chest');
INSERT INTO "set_muscles" VALUES(7,'chest');
INSERT INTO "set_muscles" VALUES(8,'back');
INSERT INTO "set_muscles" VALUES(9,'back');
INSERT INTO "set_muscles" VALUES(10,'front delt');
INSERT INTO "set_muscles" VALUES(11,'front delt');
INSERT INTO "set_muscles" VALUES(12,'side delt');
INSERT INTO "set_muscles" VALUES(13,'side delt');
INSERT INTO "set_muscles" VALUES(14,'biceps');
INSERT INTO "set_muscles" VALUES(15,'biceps');
INSERT INTO "set_muscles" VALUES(16,'biceps');
INSERT INTO "set_muscles" VALUES(17,'biceps');
INSERT INTO "set_muscles" VALUES(18,'triceps');
INSERT INTO "set_muscles" VALUES(19,'triceps');
INSERT INTO "set_muscles" VALUES(20,'forearms');
INSERT INTO "set_muscles" VALUES(21,'forearms');
INSERT INTO "set_muscles" VALUES(22,'rear delt');
INSERT INTO "set_muscles" VALUES(23,'rear delt');
CREATE TABLE sets (
  id INTEGER PRIMARY KEY,
  workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
  exercise TEXT NOT NULL,
  weight REAL NOT NULL,
  reps INTEGER NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  created TEXT NOT NULL
);
INSERT INTO "sets" VALUES(1,1,'incline barbell bench press',80.0,6,'','2026-09-19T08:29:28');
INSERT INTO "sets" VALUES(2,1,'incline barbell bench press',75.0,8,'','2026-09-19T08:33:24');
INSERT INTO "sets" VALUES(3,1,'incline barbell bench press',75.0,6,'','2026-09-19T08:37:45');
INSERT INTO "sets" VALUES(4,1,'hammer strength row',90.0,9,'','2026-09-19T08:44:43');
INSERT INTO "sets" VALUES(5,1,'hammer strength row',90.0,8,'','2026-09-19T08:47:48');
INSERT INTO "sets" VALUES(6,1,'pec deck',80.0,13,'felt nice','2026-09-19T08:52:07');
INSERT INTO "sets" VALUES(7,1,'pec deck',80.0,11,'','2026-09-19T08:56:20');
INSERT INTO "sets" VALUES(8,1,'straight bar pulldown',87.0,7,'','2026-09-19T09:00:20');
INSERT INTO "sets" VALUES(9,1,'straight bar pulldown',87.0,7,'','2026-09-19T09:04:15');
INSERT INTO "sets" VALUES(10,1,'machine shoulder press',35.0,12,'','2026-09-19T09:10:39');
INSERT INTO "sets" VALUES(11,1,'machine shoulder press',40.0,9,'','2026-09-19T09:13:51');
INSERT INTO "sets" VALUES(12,1,'cable lat raise',11.25,13,'','2026-09-19T09:20:49');
INSERT INTO "sets" VALUES(13,1,'cable lat raise',11.25,10,'','2026-09-19T09:23:32');
INSERT INTO "sets" VALUES(14,1,'bayesian curl',13.75,10,'','2026-09-19T09:28:27');
INSERT INTO "sets" VALUES(15,1,'bayesian curl',13.75,9,'','2026-09-19T09:31:17');
INSERT INTO "sets" VALUES(16,1,'preacher curl',46.0,8,'insane pump after bayesian','2026-09-19T09:34:11');
INSERT INTO "sets" VALUES(17,1,'preacher curl',46.0,8,'','2026-09-19T09:36:43');
INSERT INTO "sets" VALUES(18,1,'cable pushdown',31.25,12,'','2026-09-19T09:40:55');
INSERT INTO "sets" VALUES(19,1,'cable pushdown',31.25,11,'','2026-09-19T09:44:38');
INSERT INTO "sets" VALUES(20,1,'cable reverse curl',11.25,13,'felt amazing','2026-09-19T09:48:40');
INSERT INTO "sets" VALUES(21,1,'cable reverse curl',11.25,11,'','2026-09-19T09:51:16');
INSERT INTO "sets" VALUES(22,1,'face pull',38.75,12,'','2026-09-19T09:54:49');
INSERT INTO "sets" VALUES(23,1,'face pull',38.75,9,'','2026-09-19T09:58:04');
CREATE TABLE splits (
  id INTEGER PRIMARY KEY,
  variant TEXT NOT NULL,
  day TEXT NOT NULL,
  slot INTEGER NOT NULL,
  movements TEXT NOT NULL,
  sets INTEGER NOT NULL,
  UNIQUE (variant, day, slot)
);
INSERT INTO "splits" VALUES(1,'baseline','Upper A',1,'incline barbell bench press',3);
INSERT INTO "splits" VALUES(2,'baseline','Upper A',2,'hammer strength row',2);
INSERT INTO "splits" VALUES(3,'baseline','Upper A',3,'pec deck',2);
INSERT INTO "splits" VALUES(4,'baseline','Upper A',4,'straight bar pulldown',2);
INSERT INTO "splits" VALUES(5,'baseline','Upper A',5,'machine shoulder press',2);
INSERT INTO "splits" VALUES(6,'baseline','Upper A',6,'cable lat raise',2);
INSERT INTO "splits" VALUES(7,'baseline','Upper A',7,'bayesian curl',2);
INSERT INTO "splits" VALUES(8,'baseline','Upper A',8,'preacher curl',2);
INSERT INTO "splits" VALUES(9,'baseline','Upper A',9,'cable pushdown',2);
INSERT INTO "splits" VALUES(10,'baseline','Upper A',10,'cable reverse curl',2);
INSERT INTO "splits" VALUES(11,'baseline','Upper A',11,'face pull / cable rear delt fly',2);
INSERT INTO "splits" VALUES(12,'baseline','Lower A',1,'hack squat',2);
INSERT INTO "splits" VALUES(13,'baseline','Lower A',2,'leg extension',3);
INSERT INTO "splits" VALUES(14,'baseline','Lower A',3,'leg press',2);
INSERT INTO "splits" VALUES(15,'baseline','Lower A',4,'seated leg curl',3);
INSERT INTO "splits" VALUES(16,'baseline','Lower A',5,'adductor machine',2);
INSERT INTO "splits" VALUES(17,'baseline','Lower A',6,'crunch machine',3);
INSERT INTO "splits" VALUES(18,'baseline','Lower A',7,'machine lat raise',2);
INSERT INTO "splits" VALUES(19,'baseline','Lower A',8,'cable wrist curl',2);
INSERT INTO "splits" VALUES(20,'baseline','Upper B',1,'straight bar pulldown',3);
INSERT INTO "splits" VALUES(21,'baseline','Upper B',2,'reverse-grip smith incline press',3);
INSERT INTO "splits" VALUES(22,'baseline','Upper B',3,'hammer strength row',2);
INSERT INTO "splits" VALUES(23,'baseline','Upper B',4,'machine shoulder press',2);
INSERT INTO "splits" VALUES(24,'baseline','Upper B',5,'cable lat raise',2);
INSERT INTO "splits" VALUES(25,'baseline','Upper B',6,'ezbar curl',2);
INSERT INTO "splits" VALUES(26,'baseline','Upper B',7,'ezbar skullcrusher',2);
INSERT INTO "splits" VALUES(27,'baseline','Upper B',8,'unilateral cable pushdown',3);
INSERT INTO "splits" VALUES(28,'baseline','Upper B',9,'face pull / cable rear delt fly',2);
INSERT INTO "splits" VALUES(29,'baseline','Upper C',1,'hammer strength press',2);
INSERT INTO "splits" VALUES(30,'baseline','Upper C',2,'hammer strength row',2);
INSERT INTO "splits" VALUES(31,'baseline','Upper C',3,'pec deck',3);
INSERT INTO "splits" VALUES(32,'baseline','Upper C',4,'cable pullover',2);
INSERT INTO "splits" VALUES(33,'baseline','Upper C',5,'bayesian curl',2);
INSERT INTO "splits" VALUES(34,'baseline','Upper C',6,'preacher curl',2);
INSERT INTO "splits" VALUES(35,'baseline','Upper C',7,'cable pushdown',2);
INSERT INTO "splits" VALUES(36,'baseline','Upper C',8,'machine lat raise',2);
INSERT INTO "splits" VALUES(37,'baseline','Upper C',9,'cable wrist extension',2);
INSERT INTO "splits" VALUES(38,'baseline','Upper C',10,'face pull',2);
INSERT INTO "splits" VALUES(39,'baseline','Lower B',1,'rdl',3);
INSERT INTO "splits" VALUES(40,'baseline','Lower B',2,'leg press',3);
INSERT INTO "splits" VALUES(41,'baseline','Lower B',3,'hack squat',2);
INSERT INTO "splits" VALUES(42,'baseline','Lower B',4,'leg extension',2);
INSERT INTO "splits" VALUES(43,'baseline','Lower B',5,'seated leg curl',2);
INSERT INTO "splits" VALUES(44,'baseline','Lower B',6,'adductor machine',2);
INSERT INTO "splits" VALUES(45,'baseline','Lower B',7,'crunch machine',3);
INSERT INTO "splits" VALUES(46,'baseline','Lower B',8,'cable lat raise',2);
INSERT INTO "splits" VALUES(47,'baseline','Lower B',9,'cable wrist curl',2);
INSERT INTO "splits" VALUES(48,'active','Upper A',1,'incline barbell bench press',3);
INSERT INTO "splits" VALUES(49,'active','Upper A',2,'hammer strength row',2);
INSERT INTO "splits" VALUES(50,'active','Upper A',3,'pec deck',2);
INSERT INTO "splits" VALUES(51,'active','Upper A',4,'straight bar pulldown',2);
INSERT INTO "splits" VALUES(52,'active','Upper A',5,'machine shoulder press',2);
INSERT INTO "splits" VALUES(53,'active','Upper A',6,'cable lat raise',2);
INSERT INTO "splits" VALUES(54,'active','Upper A',7,'bayesian curl',2);
INSERT INTO "splits" VALUES(55,'active','Upper A',8,'preacher curl',2);
INSERT INTO "splits" VALUES(56,'active','Upper A',9,'cable pushdown',2);
INSERT INTO "splits" VALUES(57,'active','Upper A',10,'cable reverse curl',2);
INSERT INTO "splits" VALUES(58,'active','Upper A',11,'face pull / cable rear delt fly',2);
INSERT INTO "splits" VALUES(59,'active','Lower A',1,'hack squat',2);
INSERT INTO "splits" VALUES(60,'active','Lower A',2,'leg extension',3);
INSERT INTO "splits" VALUES(61,'active','Lower A',3,'leg press',2);
INSERT INTO "splits" VALUES(62,'active','Lower A',4,'seated leg curl',3);
INSERT INTO "splits" VALUES(63,'active','Lower A',5,'adductor machine',2);
INSERT INTO "splits" VALUES(64,'active','Lower A',6,'crunch machine',3);
INSERT INTO "splits" VALUES(65,'active','Lower A',7,'machine lat raise',2);
INSERT INTO "splits" VALUES(66,'active','Lower A',8,'cable wrist curl',2);
INSERT INTO "splits" VALUES(67,'active','Upper B',1,'straight bar pulldown',3);
INSERT INTO "splits" VALUES(68,'active','Upper B',2,'reverse-grip smith incline press',3);
INSERT INTO "splits" VALUES(69,'active','Upper B',3,'hammer strength row',2);
INSERT INTO "splits" VALUES(70,'active','Upper B',4,'machine shoulder press',2);
INSERT INTO "splits" VALUES(71,'active','Upper B',5,'cable lat raise',2);
INSERT INTO "splits" VALUES(72,'active','Upper B',6,'ezbar curl',2);
INSERT INTO "splits" VALUES(73,'active','Upper B',7,'ezbar skullcrusher',2);
INSERT INTO "splits" VALUES(74,'active','Upper B',8,'unilateral cable pushdown',3);
INSERT INTO "splits" VALUES(75,'active','Upper B',9,'face pull / cable rear delt fly',2);
INSERT INTO "splits" VALUES(76,'active','Upper C',1,'hammer strength press',2);
INSERT INTO "splits" VALUES(77,'active','Upper C',2,'hammer strength row',2);
INSERT INTO "splits" VALUES(78,'active','Upper C',3,'pec deck',3);
INSERT INTO "splits" VALUES(79,'active','Upper C',4,'cable pullover',2);
INSERT INTO "splits" VALUES(80,'active','Upper C',5,'bayesian curl',2);
INSERT INTO "splits" VALUES(81,'active','Upper C',6,'preacher curl',2);
INSERT INTO "splits" VALUES(82,'active','Upper C',7,'cable pushdown',2);
INSERT INTO "splits" VALUES(83,'active','Upper C',8,'machine lat raise',2);
INSERT INTO "splits" VALUES(84,'active','Upper C',9,'cable wrist extension',2);
INSERT INTO "splits" VALUES(85,'active','Upper C',10,'face pull',2);
INSERT INTO "splits" VALUES(86,'active','Lower B',1,'rdl',3);
INSERT INTO "splits" VALUES(87,'active','Lower B',2,'leg press',3);
INSERT INTO "splits" VALUES(88,'active','Lower B',3,'hack squat',2);
INSERT INTO "splits" VALUES(89,'active','Lower B',4,'leg extension',2);
INSERT INTO "splits" VALUES(90,'active','Lower B',5,'seated leg curl',2);
INSERT INTO "splits" VALUES(91,'active','Lower B',6,'adductor machine',2);
INSERT INTO "splits" VALUES(92,'active','Lower B',7,'crunch machine',3);
INSERT INTO "splits" VALUES(93,'active','Lower B',8,'cable lat raise',2);
INSERT INTO "splits" VALUES(94,'active','Lower B',9,'cable wrist curl',2);
CREATE TABLE workouts (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  notes TEXT NOT NULL DEFAULT ''
);
INSERT INTO "workouts" VALUES(1,'2026-09-19','done','Upper A Baseline Upper A. Shoulder press first time in a year. First session pushing higher reps on isolations. Reverse curl new.');
INSERT INTO "workouts" VALUES(2,'2026-09-20','rest','split transition friction, fewer rest days since last leg day than usual');
CREATE INDEX idx_sets_workout ON sets(workout_id);
CREATE INDEX idx_sets_exercise ON sets(exercise);
CREATE INDEX idx_bw_date ON bodyweight(date);
CREATE UNIQUE INDEX idx_deload_active ON deload_state(scope, subject) WHERE cleared_on IS NULL;
COMMIT;
