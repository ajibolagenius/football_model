import os
import requests
import pandas as pd
import json
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import time

# --- CONFIGURATION ---
# Database Connection: Matches the setup we did with Homebrew
DB_CONNECTION = "postgresql://postgres@localhost:5432/football_prediction_db"

# API-Football Config
# ⚠️ REPLACE THIS WITH YOUR KEY
API_KEY = "1689abe0cbmsh6559fb4fa7f60acp1ba35fjsnf735e986b3e1" 

# The Host header must match what RapidAPI expects (from your snippet)
API_HOST = "api-football-v1.p.rapidapi.com"
BASE_URL = "https://api-football-v1.p.rapidapi.com/v3"

LEAGUE_ID = 39  # 39 is Premier League
SEASON = 2025   # We can change this to 2024 if needed

# --- 1. DATABASE CONNECTION ---
def get_db_engine():
    return create_engine(DB_CONNECTION)

# --- 2. API FETCHER ---
def fetch_api_fixtures(date_from, date_to):
    """
    Fetches match results for the whole league within a date range.
    We use 'fixtures' endpoint instead of 'headtohead' so we get EVERY match, not just specific pairs.
    """
    url = f"{BASE_URL}/fixtures"
    
    querystring = {
        "league": str(LEAGUE_ID),
        "season": str(SEASON),
        "from": date_from,
        "to": date_to
    }
    
    headers = {
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": API_HOST
    }

    print(f"📡 Fetching matches from {date_from} to {date_to}...")
    try:
        response = requests.get(url, headers=headers, params=querystring)
        
        # Check for specific API errors (like bad key)
        if response.status_code == 403:
            print("❌ Error 403: Forbidden. Check your API Key.")
            return []
            
        response.raise_for_status()
        data = response.json()
        
        # RapidAPI sometimes returns 200 OK but with an internal error message
        if data.get('errors'):
            print(f"❌ API Internal Error: {data['errors']}")
            return []
            
        results = data.get('response', [])
        print(f"✅ Found {len(results)} matches.")
        return results
        
    except Exception as e:
        print(f"❌ Network/Parsing Error: {e}")
        return []

# --- 3. WEB SCRAPER (THE ADVANCED DATA) ---
def scrape_understat_xg(league="EPL", season="2025"):
    """
    Scrapes Expected Goals (xG) from Understat.
    This provides the 'Alpha' (predictive edge) that basic stats don't have.
    """
    base_url = f"https://understat.com/league/{league}/{season}"
    print(f"🕵️  Scraping xG data from {base_url}...")
    
    try:
        response = requests.get(base_url)
        if response.status_code != 200:
            print(f"⚠️ Understat unreachable (Status: {response.status_code})")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Understat stores data in a JSON script tag
        scripts = soup.find_all('script')
        strings = [script.string for script in scripts if script.string and 'datesData' in script.string]
        
        if not strings:
            print("⚠️  Could not find data on Understat.")
            return []

        # Extract JSON string safely
        json_data = strings[0].split("('")[1].split("')")[0]
        decoded_data = json.loads(json_data.encode('utf8').decode('unicode_escape'))
        
        print(f"✅ Scraped xG data for {len(decoded_data)} matches.")
        return decoded_data
    except Exception as e:
        print(f"❌ Scraping Error: {e}")
        return []

# --- 4. DATA STORAGE ENGINE ---
def process_and_store(api_data, scraped_data):
    """
    Merges official API data with scraped xG data and saves to PostgreSQL.
    """
    engine = get_db_engine()
    
    # Create a lookup map for scraped data: Key = "HomeTeam - AwayTeam"
    scraped_map = {}
    for match in scraped_data:
        # Understat titles are usually "Man Utd", "Arsenal", etc.
        key = f"{match['h']['title']} - {match['a']['title']}"
        scraped_map[key] = match

    with engine.connect() as conn:
        for fixture in api_data:
            # --- Extract Data ---
            fix = fixture['fixture']
            teams = fixture['teams']
            goals = fixture['goals']
            
            # Skip matches that haven't started (unless we want to store schedule)
            if fix['status']['short'] not in ['FT', 'AET', 'PEN']:
                continue

            match_date = fix['date'].split('T')[0]
            
            # --- 1. Insert Teams ---
            # We use ON CONFLICT DO NOTHING to avoid duplicates
            for side in ['home', 'away']:
                t_id = teams[side]['id']
                t_name = teams[side]['name']
                conn.execute(text("""
                    INSERT INTO teams (team_id, name) VALUES (:id, :name)
                    ON CONFLICT (team_id) DO NOTHING
                """), {'id': t_id, 'name': t_name})

            # --- 2. Generate Match ID & Link xG ---
            # API names: "Manchester United" vs "Newcastle"
            # Scraper names: "Manchester United" vs "Newcastle United" (Names might vary slightly)
            # This logic tries to find the matching scraped data
            
            home_name = teams['home']['name']
            away_name = teams['away']['name']
            
            # Try exact match first
            scrape_key = f"{home_name} - {away_name}"
            xg_stats = scraped_map.get(scrape_key)
            
            # If not found, try a simple fuzzy fallback (checking if one string is inside the other)
            if not xg_stats:
                for k, v in scraped_map.items():
                    if home_name in k and away_name in k:
                        xg_stats = v
                        break
            
            home_xg = float(xg_stats['xG']['h']) if xg_stats else None
            away_xg = float(xg_stats['xG']['a']) if xg_stats else None

            # --- 3. Insert Match ---
            # Unique ID: Date + TeamIDs (e.g., 2025-10-24-33-34)
            match_uid = f"{match_date}-{teams['home']['id']}-{teams['away']['id']}"

            conn.execute(text("""
                INSERT INTO matches (match_id, date, season, home_team_id, away_team_id, home_goals, away_goals, status)
                VALUES (:mid, :date, :season, :hid, :aid, :hg, :ag, :status)
                ON CONFLICT (match_id) DO UPDATE SET 
                    home_goals = EXCLUDED.home_goals,
                    away_goals = EXCLUDED.away_goals,
                    status = EXCLUDED.status
            """), {
                'mid': match_uid,
                'date': match_date,
                'season': str(SEASON),
                'hid': teams['home']['id'],
                'aid': teams['away']['id'],
                'hg': goals['home'],
                'ag': goals['away'],
                'status': fix['status']['short']
            })

            # --- 4. Insert Stats (xG) ---
            if home_xg is not None:
                # We update the stats if they exist
                conn.execute(text("""
                    INSERT INTO match_stats (match_id, home_xg, away_xg)
                    VALUES (:mid, :hxg, :axg)
                    ON CONFLICT (match_id) DO UPDATE SET
                        home_xg = EXCLUDED.home_xg,
                        away_xg = EXCLUDED.away_xg
                """), {
                    'mid': match_uid,
                    'hxg': home_xg,
                    'axg': away_xg
                })

            conn.commit()
            print(f"💾 Saved: {home_name} {goals['home']}-{goals['away']} {away_name} | xG: {home_xg}-{away_xg}")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # Fetch data for the whole 2025 season so far
    # You can adjust these dates
    start_date = "2025-08-11" 
    end_date = "2026-05-20"
    
    print("🚀 Starting Data Pipeline...")
    
    # 1. Fetch Official Data
    api_matches = fetch_api_fixtures(start_date, end_date)
    
    # 2. Scrape Advanced Data
    scraped_matches = scrape_understat_xg(league="EPL", season=str(SEASON))
    
    # 3. Merge & Save
    if api_matches:
        process_and_store(api_matches, scraped_matches)
        print("\n✨ Pipeline Complete. Data is in Postgres.")
    else:
        print("\n⚠️ No API data found. Check your API Key and Dates.")