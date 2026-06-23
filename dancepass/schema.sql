-- Baila Caliente: class management for Baila Caliente Dance Studios.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS students (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name    TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    email         TEXT,
    phone         TEXT,
    notes         TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- A pass_type is a sellable product: a punch card (e.g. 10 classes)
-- or a membership (unlimited within a date range, in days).
CREATE TABLE IF NOT EXISTS pass_types (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    kind          TEXT NOT NULL CHECK (kind IN ('punch', 'membership')),
    -- punch: number of classes included; membership: ignored (NULL)
    punches       INTEGER,
    -- membership: validity in days from purchase; punch: optional expiry
    valid_days    INTEGER,
    price_cents   INTEGER NOT NULL DEFAULT 0,
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- A class_session is a scheduled instance of a class students can attend.
CREATE TABLE IF NOT EXISTS class_sessions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,                 -- e.g. "Salsa On1 Beginner"
    style         TEXT NOT NULL DEFAULT 'Salsa', -- Salsa, Bachata, etc.
    level         TEXT,                          -- Beginner, Intermediate, Advanced
    instructor    TEXT,
    starts_at     TEXT NOT NULL,                 -- ISO 8601 local datetime
    duration_min  INTEGER NOT NULL DEFAULT 60,
    capacity      INTEGER,                       -- NULL = unlimited
    location      TEXT,
    notes         TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- A sale: a student bought a pass. This creates a usable pass instance.
CREATE TABLE IF NOT EXISTS passes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    pass_type_id    INTEGER NOT NULL REFERENCES pass_types(id),
    purchased_at    TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at      TEXT,                        -- NULL = never
    punches_total   INTEGER,                     -- snapshot at purchase
    punches_used    INTEGER NOT NULL DEFAULT 0,
    price_cents     INTEGER NOT NULL DEFAULT 0,
    note            TEXT
);

CREATE INDEX IF NOT EXISTS idx_passes_student ON passes(student_id);

-- Attendance: a student attended a specific class_session, optionally
-- consuming a punch from a specific pass.
CREATE TABLE IF NOT EXISTS attendance (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    session_id      INTEGER NOT NULL REFERENCES class_sessions(id) ON DELETE CASCADE,
    pass_id         INTEGER REFERENCES passes(id),
    checked_in_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(student_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_attendance_session ON attendance(session_id);
CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id);
