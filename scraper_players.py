import requests
import json
import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text

DB_CONNECTION = "postgresql://postgres@localhost:5432/football_prediction_db"

def get_db_engine():
    return create_engine(DB_CONNECTION)

def scrape_players(season="2024"):
    print(f"🕵️‍♀️ Scraping Players for {season}...")
    url = f"https://understat.com/league/EPL/{season}"
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        scripts = soup.find_all('script')
        
        for script in scripts:
            if script.string and 'playersData' in script.string:
                # Extract JSON
                json_string = script.string.split("('")[1].split("')")[0]
                data = json.loads(json_string.encode('utf8').decode('unicode_escape'))
                return data
    except Exception as e:
        print(f"❌ Error: {e}")
    return []

def sync_players_db():
    engine = get_db_engine()
    players_data = scrape_players("2024") # Current Season
    
    if not players_data:
        print("❌ No player data found.")
        return

    print(f"📥 Found {len(players_data)} players. Syncing to DB...")
    
    # Pre-fetch teams to map names to IDs
    try:
        with engine.connect() as conn:
            teams = pd.read_sql("SELECT team_id, name FROM teams", conn)
    except Exception as e:
        print(f"❌ DB Error (Is Schema Applied?): {e}")
        return
    
    # Create a map: "Manchester United" -> ID
    team_map = dict(zip(teams['name'], teams['team_id']))
    
    updates = 0
    new_players = 0
    
    with engine.connect() as conn:
        for p in players_data:
            try:
                # 1. Find Team ID
                team_name = p['team_title']
                team_id = team_map.get(team_name)
                
                # Fuzzy match fallback
                if not team_id:
                    for name, tid in team_map.items():
                        if team_name in name or name in team_name:
                            team_id = tid
                            break
                
                if not team_id:
                    # print(f"   ⚠️ Team not found: {team_name}")
                    continue

                # 2. Upsert Player
                pid = int(p['id'])
                name = p['player_name']
                
                # Check exist
                res = conn.execute(text("SELECT player_id FROM players WHERE understat_id = :uid"), {'uid': pid}).fetchone()
                
                if res:
                    db_player_id = res[0]
                else:
                    # Insert
                    res = conn.execute(text("""
                        INSERT INTO players (name, team_id, understat_id) 
                        VALUES (:name, :tid, :uid) 
                        RETURNING player_id
                    """), {'name': name, 'tid': team_id, 'uid': pid}).fetchone()
                    db_player_id = res[0]
                    new_players += 1
                
                # 3. Upsert Stats
                goals = int(p['goals'])
                assists = int(p['assists'])
                xg = float(p['xG'])
                xa = float(p['xA'])
                shots = int(p['shots'])
                key_passes = int(p['key_passes'])
                yellow = int(p['yellow_cards'])
                red = int(p['red_cards'])
                mins = int(p['time'])
                npg = float(p['npg'])
                npxg = float(p['npxG'])
                xg_chain = float(p['xGChain'])
                xg_buildup = float(p['xGBuildup'])
                
                # Upsert Stats
                sql = """
                INSERT INTO player_season_stats 
                (player_id, season, goals, assists, xg, xa, shots, key_passes, yellow_cards, red_cards, minutes, npg, npxg, xg_chain, xg_buildup)
                VALUES (:pid, '2024', :g, :a, :xg, :xa, :s, :kp, :y, :r, :m, :npg, :npxg, :xgc, :xgb)
                ON CONFLICT (player_id, season) 
                DO UPDATE SET 
                    goals = EXCLUDED.goals,
                    assists = EXCLUDED.assists,
                    xg = EXCLUDED.xg,
                    xa = EXCLUDED.xa,
                    minutes = EXCLUDED.minutes
                """
                
                conn.execute(text(sql), {
                    'pid': db_player_id,
                    'g': goals, 'a': assists, 'xg': xg, 'xa': xa,
                    's': shots, 'kp': key_passes, 'y': yellow, 'r': red,
                    'm': mins, 'npg': npg, 'npxg': npxg, 'xgc': xg_chain, 'xgb': xg_buildup
                })
                updates += 1
                
            except Exception as e:
                # print(f"Error processing {p['player_name']}: {e}")
                continue
        
        conn.commit()
        
    print(f"✅ Sync Complete. New Players: {new_players}, Stats Updated: {updates}")

if __name__ == "__main__":
    sync_players_db()
