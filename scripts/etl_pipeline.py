import requests
import pandas as pd
import json
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import time
import sys
import os

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
from utils import fetch_url, logger

# --- CONFIGURATION ---
DB_CONNECTION = config.DB_CONNECTION
API_KEY = config.RAPIDAPI_KEY
API_HOST = "api-football-v1.p.rapidapi.com"
BASE_URL = "https://api-football-v1.p.rapidapi.com/v3"
FD_API_KEY = config.FOOTBALL_DATA_ORG_KEY

LEAGUES = {
    "EPL": 39,
    "La_Liga": 140,
    "Bundesliga": 78
}

FD_LEAGUES = {
    "EPL": 2021,
    "La_Liga": 2014,
    "Bundesliga": 2002
}

SEASON = 2025

# --- 1. DATABASE CONNECTION ---
def get_db_engine():
    return create_engine(DB_CONNECTION)

# --- 2a. RAPID API FETCHER ---
def fetch_api_fixtures(league_id, date_from, date_to):
    # ... (Existing code)
    url = f"{BASE_URL}/fixtures"
    querystring = {"league": str(league_id), "season": str(SEASON), "from": date_from, "to": date_to}
    headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": API_HOST}
    logger.info(f"📡 Fetching matches from RapidAPI ({league_id})...")
    try:
        response = fetch_url(url, headers=headers, params=querystring)
        data = response.json()
        if data.get('errors'):
            logger.error(f"❌ RapidAPI Error: {data['errors']}")
            return []
        return data.get('response', [])
    except Exception as e:
        logger.error(f"❌ RapidAPI Exception: {e}")
        return []

# --- 2b. FOOTBALL-DATA.ORG FETCHER ---
def fetch_football_data_org(league_name):
    if not FD_API_KEY:
        logger.warning("⚠️ No FOOTBALL_DATA_ORG_KEY found. Skipping.")
        return []
        
    fd_id = FD_LEAGUES.get(league_name)
    if not fd_id: return []
    
    url = f"https://api.football-data.org/v4/competitions/{fd_id}/matches"
    headers = {"X-Auth-Token": FD_API_KEY}
    querystring = {"season": str(SEASON)}
    
    logger.info(f"📡 Fetching matches from Football-Data.org ({league_name})...")
    try:
        response = fetch_url(url, headers=headers, params=querystring)
        data = response.json()
        if 'matches' not in data:
            logger.error(f"❌ FD Error: {data}")
            return []
            
        matches = data['matches']
        logger.info(f"✅ Found {len(matches)} matches from FD.")
        
        # ADAPTER: Convert to RapidAPI format
        adapted = []
        for m in matches:
            if m['status'] != 'FINISHED': continue
            
            # Map Status
            status_short = 'FT'
            
            # Map Date
            date = m['utcDate']
            
            # Map Teams (Use FD IDs + 200000 to avoid collision with RapidAPI)
            h_id = m['homeTeam']['id'] + 200000
            a_id = m['awayTeam']['id'] + 200000
            
            adapted.append({
                'fixture': {
                    'date': date,
                    'status': {'short': status_short}
                },
                'teams': {
                    'home': {'id': h_id, 'name': m['homeTeam']['name']},
                    'away': {'id': a_id, 'name': m['awayTeam']['name']}
                },
                'goals': {
                    'home': m['score']['fullTime']['home'],
                    'away': m['score']['fullTime']['away']
                }
            })
        return adapted
    except Exception as e:
        logger.error(f"❌ FD Exception: {e}")
        return []

# --- 3. WEB SCRAPER ---
# ... (Existing scrape_understat_xg code) ...

# --- 4. DATA STORAGE ENGINE ---
# ... (Existing process_and_store code) ...

if __name__ == "__main__":
    start_date = "2025-08-11" 
    end_date = "2026-05-20"
    
    logger.info("🚀 Starting Data Pipeline...")
    
    for league_name, league_id in LEAGUES.items():
        logger.info(f"\n🌍 Processing {league_name}...")
        
        # 1. Try RapidAPI
        matches = fetch_api_fixtures(league_id, start_date, end_date)
        
        # 2. Try Football-Data.org if RapidAPI failed
        if not matches:
            logger.warning("⚠️ RapidAPI failed/empty. Trying Football-Data.org...")
            matches = fetch_football_data_org(league_name)
            
        # 3. Scrape Understat (Always needed for xG)
        scraped_matches = scrape_understat_xg(league=league_name, season=str(SEASON))
        
        # 4. Process (matches can be from RapidAPI or FD Adapter)
        # If matches is still empty, process_and_store will use Understat Fallback
        if matches or scraped_matches:
            process_and_store(matches, scraped_matches, league_name)
        else:
            logger.warning(f"⚠️ No data found for {league_name} (API, FD, or Scraper).")

# --- 3. WEB SCRAPER ---
def scrape_understat_xg(league="EPL", season="2025"):
    base_url = f"https://understat.com/league/{league}/{season}"
    logger.info(f"🕵️  Scraping xG data from {base_url}...")
    
    try:
        response = fetch_url(base_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        scripts = soup.find_all('script')
        strings = [script.string for script in scripts if script.string and 'datesData' in script.string]
        
        if not strings:
            logger.warning("⚠️  Could not find data on Understat.")
            return []

        json_data = strings[0].split("('")[1].split("')")[0]
        decoded_data = json.loads(json_data.encode('utf8').decode('unicode_escape'))
        
        logger.info(f"✅ Scraped xG data for {len(decoded_data)} matches.")
        return decoded_data
    except Exception as e:
        logger.error(f"❌ Scraping Error: {e}")
        return []

# --- 4. DATA STORAGE ENGINE ---
def process_and_store(api_data, scraped_data, league_name):
    engine = get_db_engine()
    
    # 1. Prepare Data Source
    # If API data exists, use it. If not, fallback to Understat (scraped_data).
    use_fallback = False
    if not api_data and scraped_data:
        logger.warning(f"⚠️ Using Understat as FALLBACK for {league_name} matches.")
        use_fallback = True
        # Convert scraped_data to a format similar to api_data for iteration, 
        # OR just iterate scraped_data directly.
        # Let's iterate scraped_data directly in the fallback block.
    
    scraped_map = {}
    for match in scraped_data:
        key = f"{match['h']['title']} - {match['a']['title']}"
        scraped_map[key] = match

    with engine.connect() as conn:
        # --- FALLBACK MODE (Understat Only) ---
        if use_fallback:
            for match in scraped_data:
                if not match['isResult']: continue # Skip unplayed
                
                match_date = match['datetime'].split(' ')[0]
                h_name = match['h']['title']
                a_name = match['a']['title']
                h_goals = int(match['goals']['h'])
                a_goals = int(match['goals']['a'])
                h_xg = float(match['xG']['h'])
                a_xg = float(match['xG']['a'])
                
                # Generate/Find Team IDs
                # We use a simple hash or offset for fallback IDs to avoid collision with API IDs (usually < 10000)
                # But ideally we check if name exists.
                
                def get_or_create_team(name, league):
                    # Check DB
                    res = conn.execute(text("SELECT team_id FROM teams WHERE name = :name"), {"name": name}).fetchone()
                    if res: return res[0]
                    
                    # Create new ID (Understat ID + 500000 is risky if we don't have it here)
                    # Let's use a hash of the name to be deterministic? Or just a random high number?
                    # Let's use a deterministic hash modulo 100000 + 500000
                    import zlib
                    new_id = (zlib.crc32(name.encode()) % 100000) + 500000
                    
                    conn.execute(text("""
                        INSERT INTO teams (team_id, name, league) VALUES (:id, :name, :league)
                        ON CONFLICT (team_id) DO NOTHING
                    """), {'id': new_id, 'name': name, 'league': league})
                    return new_id

                h_id = get_or_create_team(h_name, league_name)
                a_id = get_or_create_team(a_name, league_name)
                
                match_uid = f"{match_date}-{h_id}-{a_id}"
                
                # Insert Match
                conn.execute(text("""
                    INSERT INTO matches (match_id, date, season, home_team_id, away_team_id, home_goals, away_goals, status, league)
                    VALUES (:mid, :date, :season, :hid, :aid, :hg, :ag, :status, :league)
                    ON CONFLICT (match_id) DO UPDATE SET 
                        home_goals = EXCLUDED.home_goals,
                        away_goals = EXCLUDED.away_goals,
                        status = EXCLUDED.status,
                        league = EXCLUDED.league
                """), {
                    'mid': match_uid,
                    'date': match_date,
                    'season': str(SEASON),
                    'hid': h_id,
                    'aid': a_id,
                    'hg': h_goals,
                    'ag': a_goals,
                    'status': 'FT',
                    'league': league_name
                })
                
                # Insert Stats
                conn.execute(text("""
                    INSERT INTO match_stats (match_id, home_xg, away_xg)
                    VALUES (:mid, :hxg, :axg)
                    ON CONFLICT (match_id) DO UPDATE SET
                        home_xg = EXCLUDED.home_xg,
                        away_xg = EXCLUDED.away_xg
                """), {
                    'mid': match_uid,
                    'hxg': h_xg,
                    'axg': a_xg
                })
                conn.commit()
            return # Done with fallback

        # --- NORMAL MODE (API Data) ---
        for fixture in api_data:
            fix = fixture['fixture']
            teams = fixture['teams']
            goals = fixture['goals']
            
            if fix['status']['short'] not in ['FT', 'AET', 'PEN']:
                continue

            match_date = fix['date'].split('T')[0]
            
            # Insert Teams
            for side in ['home', 'away']:
                t_id = teams[side]['id']
                t_name = teams[side]['name']
                conn.execute(text("""
                    INSERT INTO teams (team_id, name, league) VALUES (:id, :name, :league)
                    ON CONFLICT (team_id) DO UPDATE SET league = EXCLUDED.league
                """), {'id': t_id, 'name': t_name, 'league': league_name})

            # Match Mapping
            home_name = teams['home']['name']
            away_name = teams['away']['name']
            
            scrape_key = f"{home_name} - {away_name}"
            xg_stats = scraped_map.get(scrape_key)
            
            if not xg_stats:
                for k, v in scraped_map.items():
                    if home_name in k and away_name in k:
                        xg_stats = v
                        break
            
            home_xg = float(xg_stats['xG']['h']) if xg_stats else None
            away_xg = float(xg_stats['xG']['a']) if xg_stats else None

            match_uid = f"{match_date}-{teams['home']['id']}-{teams['away']['id']}"

            conn.execute(text("""
                INSERT INTO matches (match_id, date, season, home_team_id, away_team_id, home_goals, away_goals, status, league)
                VALUES (:mid, :date, :season, :hid, :aid, :hg, :ag, :status, :league)
                ON CONFLICT (match_id) DO UPDATE SET 
                    home_goals = EXCLUDED.home_goals,
                    away_goals = EXCLUDED.away_goals,
                    status = EXCLUDED.status,
                    league = EXCLUDED.league
            """), {
                'mid': match_uid,
                'date': match_date,
                'season': str(SEASON),
                'hid': teams['home']['id'],
                'aid': teams['away']['id'],
                'hg': goals['home'],
                'ag': goals['away'],
                'status': fix['status']['short'],
                'league': league_name
            })

            if home_xg is not None:
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

if __name__ == "__main__":
    start_date = "2025-08-11" 
    end_date = "2026-05-20"
    
    logger.info("🚀 Starting Data Pipeline...")
    
    for league_name, league_id in LEAGUES.items():
        logger.info(f"\n🌍 Processing {league_name}...")
        
        api_matches = fetch_api_fixtures(league_id, start_date, end_date)
        scraped_matches = scrape_understat_xg(league=league_name, season=str(SEASON))
        
        # Pass both. Logic inside handles fallback.
        if api_matches or scraped_matches:
            process_and_store(api_matches, scraped_matches, league_name)
        else:
            logger.warning(f"⚠️ No data found for {league_name} (API or Scraper).")
