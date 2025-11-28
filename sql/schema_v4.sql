ALTER TABLE player_season_stats
ADD COLUMN IF NOT EXISTS xg_chain FLOAT;

ALTER TABLE player_season_stats
ADD COLUMN IF NOT EXISTS xg_buildup FLOAT;