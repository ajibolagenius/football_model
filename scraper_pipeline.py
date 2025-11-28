import requests
import json
import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text

# --- CONFIGURATION ---
DB_CONNECTION = "postgresql://postgres@localhost:5432/football_prediction_db"
LEAGUE = "EPL"
SEASON = "2025" # Understat usually uses the start year (e.g., 2024 for 24/25 season)

def get_db_engine():
    return create_engine(DB_CONNECTION)

def scrape_understat_full(league, season):
    """
    Scrapes Match Results AND xG from Understat.
    Used as a fallback when the Official API is down or pending approval.
    """
    base_url = f"https://understat.com/league/{league}/{season}"
    print(f"🕵️  Scraping full match data from {base_url}...")
    
    try:
        response = requests.get(base_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        scripts = soup.find_all('script')
        strings = [script.string for script in scripts if script.string and 'datesData' in script.string]
        
        if not strings:
            print("❌ Error: Could not find data.")
            return []

        # Extract JSON
        json_data = strings[0].split("('")[1].split("')")[0]
        decoded_data = json.loads(json_data.encode('utf8').decode('unicode_escape'))
        
        print(f"✅ Successfully scraped {len(decoded_data)} matches.")
        return decoded_data
    except Exception as e:
        print(f"❌ Scraping Error: {e}")
        return []

def store_scraped_data(scraped_data):
    engine = get_db_engine()
    
    with engine.connect() as conn:
        print("💾 Saving data to database...")
        for match in scraped_data:
            # Understat Data Structure:
            # {'id': '22284', 'h': {'title': 'Burnley', 'id': '92'}, 'a': {'title': 'Man City', 'id': '88'}, 'goals': {'h': '0', 'a': '3'}, 'xG': {'h': '0.31', 'a': '2.35'}, 'datetime': '2023-08-11 19:00:00', ...}
            
            # 1. Skip if match hasn't happened yet (isResult is false)
            if not match.get('isResult'):
                continue

            match_date = match['datetime'].split(' ')[0]
            
            # 2. Insert Teams (Using Understat IDs)
            home_team = match['h']
            away_team = match['a']
            
            for t in [home_team, away_team]:
                conn.execute(text("""
                    INSERT INTO teams (team_id, name, understat_id) 
                    VALUES (:id, :name, :uid)
                    ON CONFLICT (team_id) DO NOTHING
                """), {'id': int(t['id']), 'name': t['title'], 'uid': t['id']})

            # 3. Insert Match
            # We create a custom ID: Date + HomeID + AwayID
            match_uid = f"{match_date}-{home_team['id']}-{away_team['id']}"
            
            conn.execute(text("""
                INSERT INTO matches (match_id, date, season, home_team_id, away_team_id, home_goals, away_goals, status)
                VALUES (:mid, :date, :season, :hid, :aid, :hg, :ag, 'FT')
                ON CONFLICT (match_id) DO UPDATE SET 
                    home_goals = EXCLUDED.home_goals,
                    away_goals = EXCLUDED.away_goals
            """), {
                'mid': match_uid,
                'date': match_date,
                'season': SEASON,
                'hid': int(home_team['id']),
                'aid': int(away_team['id']),
                'hg': int(match['goals']['h']),
                'ag': int(match['goals']['a'])
            })

            # 4. Insert xG Stats
            conn.execute(text("""
                INSERT INTO match_stats (match_id, home_xg, away_xg)
                VALUES (:mid, :hxg, :axg)
                ON CONFLICT (match_id) DO UPDATE SET
                    home_xg = EXCLUDED.home_xg,
                    away_xg = EXCLUDED.away_xg
            """), {
                'mid': match_uid,
                'hxg': float(match['xG']['h']),
                'axg': float(match['xG']['a'])
            })
            
            conn.commit()
            
    print("✨ Database population complete via Scraper!")

if __name__ == "__main__":
    # If today is Nov 2025, the season is "2025" (The 2025/2026 season)
    # If the season hasn't started or just started, try "2024" for the previous full season data.
    data = scrape_understat_full(LEAGUE, SEASON)
    if data:
        store_scraped_data(data)