-- MLB Doubleheader Detection & Repair Queries
-- Doubleheaders appear as duplicate player records: same player + date + teams, different odds hash


-- 1. Find all doubleheader dates and how many players are affected
SELECT game_date, odds_home_team_id, odds_away_team_id, COUNT(DISTINCT normalized_name) AS players_affected
FROM mlb_batter_props
WHERE (game_date, normalized_name, odds_home_team_id, odds_away_team_id) IN (
    SELECT game_date, normalized_name, odds_home_team_id, odds_away_team_id
    FROM mlb_batter_props
    GROUP BY game_date, normalized_name, odds_home_team_id, odds_away_team_id
    HAVING COUNT(*) > 1
)
GROUP BY game_date, odds_home_team_id, odds_away_team_id
ORDER BY game_date;


-- 2. Inspect all duplicate batter prop records for a specific date/matchup
SELECT id, normalized_name, game_date, odds_event_id, espn_event_id,
       actual_batter_hits, actual_batter_home_runs, actual_batter_rbi
FROM mlb_batter_props
WHERE game_date = '2024-07-20'
  AND (odds_home_team_id = 441 OR odds_away_team_id = 441)  -- replace with team ID
ORDER BY normalized_name, id;


-- 3. Null out actuals for all doubleheader batter records (run before re-importing)
UPDATE mlb_batter_props
SET actual_batter_hits = NULL,
    actual_batter_home_runs = NULL,
    actual_batter_rbi = NULL,
    actual_batter_runs_scored = NULL,
    actual_batter_at_bats = NULL,
    actual_batter_walks = NULL,
    actual_batter_strikeouts = NULL,
    espn_event_id = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE (game_date, normalized_name, odds_home_team_id, odds_away_team_id) IN (
    SELECT game_date, normalized_name, odds_home_team_id, odds_away_team_id
    FROM mlb_batter_props
    GROUP BY game_date, normalized_name, odds_home_team_id, odds_away_team_id
    HAVING COUNT(*) > 1
);


-- 4. Same as #3 but for pitcher props
UPDATE mlb_pitcher_props
SET actual_pitcher_strikeouts = NULL,
    actual_pitcher_earned_runs = NULL,
    actual_pitcher_hits_allowed = NULL,
    actual_pitcher_walks = NULL,
    actual_pitcher_innings_pitched = NULL,
    espn_event_id = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE (game_date, normalized_name, odds_home_team_id, odds_away_team_id) IN (
    SELECT game_date, normalized_name, odds_home_team_id, odds_away_team_id
    FROM mlb_pitcher_props
    GROUP BY game_date, normalized_name, odds_home_team_id, odds_away_team_id
    HAVING COUNT(*) > 1
);


-- 5. Check pitcher doubleheader dates
SELECT game_date, odds_home_team_id, odds_away_team_id, COUNT(DISTINCT normalized_name) AS pitchers_affected
FROM mlb_pitcher_props
WHERE (game_date, normalized_name, odds_home_team_id, odds_away_team_id) IN (
    SELECT game_date, normalized_name, odds_home_team_id, odds_away_team_id
    FROM mlb_pitcher_props
    GROUP BY game_date, normalized_name, odds_home_team_id, odds_away_team_id
    HAVING COUNT(*) > 1
)
GROUP BY game_date, odds_home_team_id, odds_away_team_id
ORDER BY game_date;
