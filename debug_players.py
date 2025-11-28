from sqlalchemy import create_engine, text
import pandas as pd

DB_CONNECTION = "postgresql://postgres@localhost:5432/football_prediction_db"
engine = create_engine(DB_CONNECTION)

with engine.connect() as conn:
    print("--- Checking player_season_stats ---")
    try:
        res = conn.execute(text("SELECT season, count(*) FROM player_season_stats GROUP BY season")).fetchall()
        print(res)
    except Exception as e:
        print(f"Error reading stats: {e}")
    
    print("\n--- Checking players ---")
    try:
        res = conn.execute(text("SELECT count(*) FROM players")).fetchall()
        print(res)
    except Exception as e:
        print(f"Error reading players: {e}")
    
    print("\n--- Checking Join ---")
    try:
        query = """
        SELECT count(*)
        FROM player_season_stats s
        JOIN players p ON s.player_id = p.player_id
        JOIN teams t ON p.team_id = t.team_id
        WHERE s.season = '2025'
        """
        res = conn.execute(text(query)).fetchall()
        print(res)
    except Exception as e:
        print(f"Error joining: {e}")
