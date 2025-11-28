-- 4. PLAYERS
CREATE TABLE IF NOT EXISTS players (
    player_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    team_id INT REFERENCES teams (team_id),
    understat_id INT UNIQUE
);

-- 5. PLAYER SEASON STATS
CREATE TABLE IF NOT EXISTS player_season_stats (
    id SERIAL PRIMARY KEY,
    player_id INT REFERENCES players (player_id),
    season VARCHAR(10),
    goals INT,
    assists INT,
    xg FLOAT,
    xa FLOAT,
    shots INT,
    key_passes INT,
    yellow_cards INT,
    red_cards INT,
    minutes INT,
    npg FLOAT, -- Non-penalty goals
    npxg FLOAT, -- Non-penalty xG
    xg_chain FLOAT,
    xg_buildup FLOAT,
    UNIQUE (player_id, season)
);

-- Index
CREATE INDEX idx_player_stats_season ON player_season_stats (season);