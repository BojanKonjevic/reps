BEGIN TRANSACTION;
CREATE TABLE bodyweight (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  kg REAL NOT NULL,
  note TEXT NOT NULL DEFAULT ''
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
CREATE TABLE workouts (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  notes TEXT NOT NULL DEFAULT ''
);
INSERT INTO "workouts" VALUES(1,'2026-09-19','done','Upper A Baseline Upper A. Shoulder press first time in a year. First session pushing higher reps on isolations. Reverse curl new.');
CREATE INDEX idx_sets_workout ON sets(workout_id);
CREATE INDEX idx_sets_exercise ON sets(exercise);
CREATE INDEX idx_bw_date ON bodyweight(date);
COMMIT;
