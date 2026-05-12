-- Analytics queries for Automated Farmer progress data

-- How many times has each user attempted each level?
SELECT
    username,
    level_id,
    attempts,
    completed,
    best_time
FROM progress
ORDER BY username, level_id;

-- Leaderboard: fastest completion time per level (completed users only)
SELECT
    level_id,
    username,
    best_time,
    completed_at
FROM progress
WHERE completed = 1
ORDER BY level_id, best_time ASC;

-- How many unique levels has each user completed?
SELECT
    username,
    COUNT(*) AS levels_completed,
    SUM(attempts) AS total_attempts
FROM progress
WHERE completed = 1
GROUP BY username
ORDER BY levels_completed DESC, total_attempts ASC;

-- Average attempts needed to complete each level (difficulty metric)
SELECT
    level_id,
    ROUND(AVG(attempts), 1) AS avg_attempts,
    COUNT(*) AS total_completions,
    ROUND(MIN(best_time), 2) AS fastest_time,
    ROUND(AVG(best_time), 2) AS avg_time
FROM progress
WHERE completed = 1
GROUP BY level_id
ORDER BY level_id;

-- Most recent script submitted per user per level
SELECT
    s.username,
    s.level_id,
    s.code,
    s.saved_at
FROM scripts s
INNER JOIN (
    SELECT username, level_id, MAX(saved_at) AS latest
    FROM scripts
    GROUP BY username, level_id
) latest ON s.username = latest.username
        AND s.level_id = latest.level_id
        AND s.saved_at = latest.latest
ORDER BY s.username, s.level_id;

-- Users who have never completed a level (stuck players)
SELECT DISTINCT username
FROM progress
WHERE completed = 0
  AND username NOT IN (
      SELECT DISTINCT username FROM progress WHERE completed = 1
  )
ORDER BY username;

-- Total number of scripts submitted per day (activity over time)
SELECT
    DATE(saved_at) AS day,
    COUNT(*) AS scripts_submitted,
    COUNT(DISTINCT username) AS active_users
FROM scripts
GROUP BY DATE(saved_at)
ORDER BY day DESC;
