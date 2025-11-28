-- Add league column to matches and teams
ALTER TABLE matches
ADD COLUMN IF NOT EXISTS league VARCHAR(50) DEFAULT 'EPL';

ALTER TABLE teams
ADD COLUMN IF NOT EXISTS league VARCHAR(50) DEFAULT 'EPL';

-- Index for faster filtering
CREATE INDEX IF NOT EXISTS idx_matches_league ON matches (league);

CREATE INDEX IF NOT EXISTS idx_teams_league ON teams (league);