-- Scripts: every code submission a player makes, keyed by username and level
CREATE TABLE IF NOT EXISTS scripts (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username  TEXT    NOT NULL,
    level_id  INTEGER NOT NULL,
    code      TEXT    NOT NULL,
    saved_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Progress: one row per (user, level) tracking attempts, completions, and best time
CREATE TABLE IF NOT EXISTS progress (
    username      TEXT    NOT NULL,
    level_id      INTEGER NOT NULL,
    attempts      INTEGER NOT NULL DEFAULT 0,
    completed     INTEGER NOT NULL DEFAULT 0,  -- 1 = completed at least once
    best_time     REAL,                        -- seconds, NULL until first completion
    completed_at  TEXT,                        -- ISO-8601 timestamp of first completion
    PRIMARY KEY (username, level_id)
);
