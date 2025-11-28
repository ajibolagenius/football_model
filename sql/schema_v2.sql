CREATE TABLE IF NOT EXISTS players (
    player_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100),
    team_id INT REFERENCES teams (team_id),
    position VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS player_season_stats (
    player_id VARCHAR(50) REFERENCES players (player_id),
    season VARCHAR(10),
    goals INT,
    assists INT,
    xg FLOAT,
    xa FLOAT,
    yellow_cards INT,
    red_cards INT,
    minutes_played INT,
    PRIMARY KEY (player_id, season)
);