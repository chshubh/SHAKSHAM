-- SHAKSHAM schema (SQLite). Applied automatically on startup; safe to re-run.

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    text_size TEXT DEFAULT 'normal',          -- normal | large | xlarge
    high_contrast INTEGER DEFAULT 0,
    reduce_motion INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assessments (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    data_json TEXT NOT NULL,
    safety_block INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    data_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workout_plans (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    assessment_id INTEGER,
    name TEXT NOT NULL,
    goal TEXT,
    duration_minutes INTEGER NOT NULL,
    explanation_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(assessment_id) REFERENCES assessments(id)
);

CREATE TABLE IF NOT EXISTS workout_exercises (
    id INTEGER PRIMARY KEY,
    plan_id INTEGER NOT NULL,
    exercise_slug TEXT NOT NULL,
    position_order INTEGER NOT NULL,
    role TEXT,
    sets INTEGER DEFAULT 2,
    reps INTEGER DEFAULT 0,
    duration_seconds INTEGER DEFAULT 60,
    rest_seconds INTEGER DEFAULT 20,
    why TEXT,
    FOREIGN KEY(plan_id) REFERENCES workout_plans(id)
);

CREATE TABLE IF NOT EXISTS workout_sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    plan_id INTEGER,
    duration_seconds INTEGER DEFAULT 0,
    completed INTEGER DEFAULT 0,
    feedback TEXT,                             -- hardest rating reported: easy|moderate|difficult|pain
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(plan_id) REFERENCES workout_plans(id)
);

CREATE TABLE IF NOT EXISTS exercise_feedback (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    plan_id INTEGER,
    session_id INTEGER,
    exercise_slug TEXT NOT NULL,
    rating TEXT NOT NULL,                      -- easy|moderate|difficult|pain
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_achievements (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    achievement_id INTEGER NOT NULL,
    earned_at TEXT NOT NULL,
    UNIQUE(user_id, achievement_id),
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(achievement_id) REFERENCES achievements(id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON workout_sessions(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_user ON exercise_feedback(user_id, created_at);
