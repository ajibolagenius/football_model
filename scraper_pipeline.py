import requests
import json
import time
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
import config
from utils import fetch_url, logger

DB_CONNECTION = config.DB_CONNECTION
SEASONS = ["2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"]

# --- MANUAL MAPPING (The Fix) ---
# Key: Understat Slug (from URL)
# Value: Your Database Name (Standard API-Football Names)
NAME_MAP = {
    "Arsenal": "Arsenal",
    "Aston_Villa": "Aston Villa",
    "Bournemouth": "Bournemouth",
    "Brentford": "Brentford",
    "Brighton": "Brighton",
    "Burnley": "Burnley",
    "Chelsea": "Chelsea",
    "Crystal_Palace": "Crystal Palace",
    "Everton": "Everton",
    "Fulham": "Fulham",
    "Ipswich": "Ipswich",
    "Leeds": "Leeds",
    "Leicester": "Leicester",
    "Liverpool": "Liverpool",
    "Luton": "Luton Town",
    "Manchester_City": "Manchester City",
    "Manchester_United": "Manchester United",
    "Newcastle_United": "Newcastle",
    "Norwich": "Norwich",
    "Nottingham_Forest": "Nottingham Forest",
    "Sheffield_United": "Sheffield United",
    "Southampton": "Southampton",
    "Tottenham": "Tottenham", 
    "Watford": "Watford",
    "West_Bromwich_Albion": "West Brom",
    "West_Ham": "West Ham",
    "Wolverhampton_Wanderers": "Wolves",
    # La Liga
    "Real_Madrid": "Real Madrid",
    "Barcelona": "Barcelona",
    "Atletico_Madrid": "Atletico Madrid",
    "Sevilla": "Sevilla",
    # Bundesliga
    "Bayern_Munich": "Bayern Munich",
    "Borussia_Dortmund": "Dortmund",
    "Bayer_Leverkusen": "Bayer Leverkusen", 
    "RB_Leipzig": "RB Leipzig",
}

LEAGUES = ["EPL", "La_Liga", "Bundesliga"]

def get_db_engine():
    return create_engine(DB_CONNECTION)

def get_understat_slugs(league, season):
    """Fetches Understat team slugs for a season."""
    url = f"https://understat.com/league/{league}/{season}"
    try:
        response = fetch_url(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'teamsData' in script.string:
                json_string = script.string.split("('")[1].split("')")[0]
                data = json.loads(json_string.encode('utf8').decode('unicode_escape'))
                # Return list of 'title' (e.g. 'Manchester_United')
                return [t['title'].replace(' ', '_') for t in data.values()]
    except Exception as e:
        logger.error(f"❌ Error fetching team list: {e}")
    return []

def scrape_team_tactics(team_slug, season):
    url = f"https://understat.com/team/{team_slug}/{season}"
    logger.info(f"   🕵️‍♀️ Parsing {team_slug} ({season})...")
    try:
        response = fetch_url(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'datesData' in script.string:
                json_string = script.string.split("('")[1].split("')")[0]
                return json.loads(json_string.encode('utf8').decode('unicode_escape'))
    except:
        return []
    return []

def update_database_tactics():
    engine = get_db_engine()
    
    # 1. Get List of actual DB names to fuzzy match if needed
    with engine.connect() as conn:
        db_teams = [r[0] for r in conn.execute(text("SELECT name FROM teams")).fetchall()]

    for league in LEAGUES:
        for season in SEASONS:
            logger.info(f"\n📅 League {league} - Season {season}...")
            slugs = get_understat_slugs(league, season)
        
        for slug in slugs:
            # Determine DB Name
            db_name = NAME_MAP.get(slug)
            
            # Fallback: Try exact match (replacing underscore)
            if not db_name:
                clean_slug = slug.replace('_', ' ')
                if clean_slug in db_teams:
                    db_name = clean_slug
                else:
                    # Try finding "Tottenham" in "Tottenham Hotspur"
                    for t in db_teams:
                        if clean_slug in t or t in clean_slug:
                            db_name = t
                            break
            
            if not db_name:
                logger.warning(f"   ⚠️ Could not map '{slug}' to Database. Skipping.")
                continue

            # Scrape
            matches = scrape_team_tactics(slug, season)
            updates = 0
            
            with engine.connect() as conn:
                for m in matches:
                    try:
                        # Extract Data
                        if m.get('ppda') and m['ppda'].get('def', 0) != 0:
                            ppda = m['ppda']['att'] / m['ppda']['def']
                        else:
                            ppda = None
                        deep = m.get('deep', 0)
                        date = m['datetime'].split(' ')[0]
                        
                        # SQL Update
                        # We use LIKE for the team name to be more forgiving
                        if m['side'] == 'h':
                            sql = """
                            UPDATE match_stats SET home_ppda = :ppda, home_deep = :deep
                            FROM matches, teams
                            WHERE match_stats.match_id = matches.match_id
                            AND matches.home_team_id = teams.team_id
                            AND matches.date = :date
                            AND teams.name = :db_name
                            """
                        else:
                            sql = """
                            UPDATE match_stats SET away_ppda = :ppda, away_deep = :deep
                            FROM matches, teams
                            WHERE match_stats.match_id = matches.match_id
                            AND matches.away_team_id = teams.team_id
                            AND matches.date = :date
                            AND teams.name = :db_name
                            """
                        
                        result = conn.execute(text(sql), {
                            'ppda': ppda, 'deep': deep, 'date': date, 'db_name': db_name
                        })
                        if result.rowcount > 0:
                            updates += 1
                            
                    except Exception:
                        continue
                conn.commit()
            logger.info(f"      ✅ Updated {updates} matches for {db_name}")
            time.sleep(0.5)

    logger.info("\n🎉 Tactical Data Sync Complete!")

if __name__ == "__main__":
    update_database_tactics()