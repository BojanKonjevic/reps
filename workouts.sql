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
INSERT INTO "lift_muscle_map" VALUES('incline barbell bench press','chest',0);
INSERT INTO "lift_muscle_map" VALUES('pec deck','chest',0);
INSERT INTO "lift_muscle_map" VALUES('hammer strength row','back',0);
CREATE TABLE schema_version (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT INTO "schema_version" VALUES(1,'2026-09-18 11:54:17');
INSERT INTO "schema_version" VALUES(2,'2026-09-18 11:54:17');
INSERT INTO "schema_version" VALUES(3,'2026-09-18 11:54:17');
CREATE TABLE set_muscles (
  set_id INTEGER NOT NULL REFERENCES sets(id) ON DELETE CASCADE,
  muscle TEXT NOT NULL,
  PRIMARY KEY (set_id, muscle)
);
INSERT INTO "set_muscles" VALUES(1,'chest');
INSERT INTO "set_muscles" VALUES(2,'chest');
INSERT INTO "set_muscles" VALUES(3,'chest');
INSERT INTO "set_muscles" VALUES(4,'chest');
INSERT INTO "set_muscles" VALUES(5,'back');
CREATE TABLE sets (
  id INTEGER PRIMARY KEY,
  workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
  exercise TEXT NOT NULL,
  weight REAL NOT NULL,
  reps INTEGER NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  created TEXT NOT NULL
, muscles TEXT NOT NULL DEFAULT '');
INSERT INTO "sets" VALUES(1,1,'incline barbell bench press',80.0,8,'','2026-09-18T13:55:42','');
INSERT INTO "sets" VALUES(2,1,'incline barbell bench press',80.0,8,'','2026-09-18T13:55:50','');
INSERT INTO "sets" VALUES(3,1,'incline barbell bench press',80.0,6,'','2026-09-18T13:56:00','');
INSERT INTO "sets" VALUES(4,1,'pec deck',50.0,10,'','2026-09-18T13:56:26','');
INSERT INTO "sets" VALUES(5,1,'hammer strength row',70.0,8,'','2026-09-18T13:56:45','');
CREATE TABLE workouts (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  notes TEXT NOT NULL DEFAULT ''
);
INSERT INTO "workouts" VALUES(1,'2026-09-18','done','Upper A - normal session felt good, shoulder fine');
CREATE INDEX idx_sets_workout ON sets(workout_id);
CREATE INDEX idx_sets_exercise ON sets(exercise);
CREATE INDEX idx_bw_date ON bodyweight(date);
COMMIT;
