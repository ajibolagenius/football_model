import requests
import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
import sys
import os

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
from utils import fetch_url, logger

DB_CONNECTION = config.DB_CONNECTION
LEAGUES = ["EPL", "La_Liga", "Bundesliga"]

def get_db_engine():
    return create_engine(DB_CONNECTION)

def scrape_players(league="EPL", season="2025"):
    logger.info(f"🕵️‍♀️ Scraping Players for {league} {season}...")
    url = f"https://understat.com/league/{league}/{season}"
    try:
        response = fetch_url(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'playersData' in script.string:
                json_string = script.string.split("('")[1].split("')")[0]
                import json
                data = json.loads(json_string.encode('utf8').decode('unicode_escape'))
                return data
    except Exception as e:
        logger.error(f"❌ Error scraping players: {e}")
    return []

def sync_players_db():
    engine = get_db_engine()
    
    for league in LEAGUES:
        players_data = scrape_players(league, "2025") # Current Season
        
        if not players_data:
            logger.error(f"❌ No player data found for {league}.")
            continue

        logger.info(f"📥 Found {len(players_data)} players in {league}. Syncing to DB...")
        
        # Pre-fetch teams to map names to IDs
        try:
            teams_df = pd.read_sql("SELECT team_id, name FROM teams", engine)
            # Create a mapping dictionary: Name -> ID
            # Normalize names (e.g. lower case) for better matching if needed
            team_map = dict(zip(teams_df['name'], teams_df['team_id']))
        except Exception as e:
            logger.error(f"❌ Error fetching teams: {e}")
            return

        with engine.connect() as conn:
            for p in players_data:
                try:
                    with conn.begin_nested():
                        # 1. Map Team Name to Team ID
                        team_name = p['team_title']
                        team_id = team_map.get(team_name)
                        
                        # Fallback mapping if exact match fails
                        if not team_id:
                            # Try simple replacements
                            if team_name == "Manchester United": team_id = team_map.get("Manchester United")
                            elif team_name == "Newcastle United": team_id = team_map.get("Newcastle")
                            elif team_name == "Wolverhampton Wanderers": team_id = team_map.get("Wolves")
                            elif team_name == "West Ham": team_id = team_map.get("West Ham")
                            elif team_name == "Tottenham": team_id = team_map.get("Tottenham")
                            elif team_name == "Brighton": team_id = team_map.get("Brighton")
                            # Add more mappings as needed
                        
                        if not team_id:
                            # logger.warning(f"⚠️ Could not map team '{team_name}' for player '{p['player_name']}'. Skipping.")
                            continue

                        # 2. Insert Player
                        conn.execute(text("""
                            INSERT INTO players (player_id, name, team_id, position)
                            VALUES (:pid, :name, :tid, :pos)
                            ON CONFLICT (player_id) DO UPDATE SET
                                team_id = EXCLUDED.team_id,
                                position = EXCLUDED.position
                        """), {
                            'pid': p['id'],
                            'name': p['player_name'],
                            'tid': team_id,
                            'pos': p['position']
                        })

                        # 3. Insert Season Stats
                        conn.execute(text("""
                            INSERT INTO player_season_stats (player_id, season, goals, assists, xg, xa, yellow_cards, red_cards, minutes_played, xg_chain, xg_buildup)
                            VALUES (:pid, :season, :g, :a, :xg, :xa, :yc, :rc, :mins, :xgc, :xgb)
                            ON CONFLICT (player_id, season) DO UPDATE SET
                                goals = EXCLUDED.goals,
                                assists = EXCLUDED.assists,
                                xg = EXCLUDED.xg,
                                xa = EXCLUDED.xa,
                                yellow_cards = EXCLUDED.yellow_cards,
                                red_cards = EXCLUDED.red_cards,
                                minutes_played = EXCLUDED.minutes_played,
                                xg_chain = EXCLUDED.xg_chain,
                                xg_buildup = EXCLUDED.xg_buildup
                        """), {
                            'pid': p['id'],
                            'season': '2025',
                            'g': p['goals'],
                            'a': p['assists'],
                            'xg': p['xG'],
                            'xa': p['xA'],
                            'yc': p['yellow_cards'],
                            'rc': p['red_cards'],
                            'mins': p['time'],
                            'xgc': p.get('xGChain', 0),
                            'xgb': p.get('xGBuildup', 0)
                        })
                    
                except Exception as e:
                    logger.error(f"❌ Error inserting player {p['player_name']}: {e}")
                    continue
            
            conn.commit()
    
    logger.info("✅ Player Data Sync Complete!")

if __name__ == "__main__":
    print("🚀 Starting Player Scraper...")
    sync_players_db()
