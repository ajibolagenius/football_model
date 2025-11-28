-- Run this in your database tool or via command line: psql -d football_prediction_db -f schema.sql

-- 1. TEAMS
-- Stores static info about teams to avoid repetition
CREATE TABLE IF NOT EXISTS teams (
    team_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(10), -- e.g., 'MUN' for Man Utd
    understat_id VARCHAR(50) -- Links our API data to scraped data
);

-- 2. MATCHES
-- The core table linking teams, dates, and results
CREATE TABLE IF NOT EXISTS matches (
    match_id VARCHAR(50) PRIMARY KEY, -- We will use a composite ID like '2024-10-24-LIV-ARS'
    date DATE NOT NULL,
    season VARCHAR(10), -- e.g., '2023/2024'
    home_team_id INT REFERENCES teams(team_id),
    away_team_id INT REFERENCES teams(team_id),
    home_goals INT,
    away_goals INT,
    status VARCHAR(20) -- 'FINISHED', 'SCHEDULED'
);

-- 3. MATCH_STATS (The "Alpha" features)
-- Stores the deep data we need for the model
CREATE TABLE IF NOT EXISTS match_stats (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(50) REFERENCES matches(match_id),
    
    -- Basic Stats (from API)
    home_possession INT,
    away_possession INT,
    home_shots_on_target INT,
    away_shots_on_target INT,
    home_corners INT,
    away_corners INT,
    
    -- Advanced Stats (from Scraping Understat)
    home_xg FLOAT,
    away_xg FLOAT,
    
    -- Betting Data (Target Variable)
    home_odds DECIMAL(5,2),
    draw_odds DECIMAL(5,2),
    away_odds DECIMAL(5,2)
);

-- Index for faster queries later
CREATE INDEX idx_matches_date ON matches(date);
CREATE INDEX idx_matches_teams ON matches(home_team_id, away_team_id);