import requests
from bs4 import BeautifulSoup
import json

def inspect_league():
    url = "https://understat.com/league/EPL/2025" # Use 2024 to ensure data exists
    print(f"🕵️ Inspecting {url}...")
    
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and 'datesData' in script.string:
            print("✅ Found 'datesData'!")
            json_string = script.string.split("('")[1].split("')")[0]
            data = json.loads(json_string.encode('utf8').decode('unicode_escape'))
            
            if len(data) > 0:
                match = data[0]
                print(f"Sample Match: {json.dumps(match, indent=2)}")
                return match['id']
    return None

def inspect_match(match_id):
    url = f"https://understat.com/match/{match_id}"
    print(f"🕵️ Inspecting Match {url}...")
    
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    scripts = soup.find_all('script')
    found = []
    for script in scripts:
        if script.string:
            if 'rosterData' in script.string: found.append('rosterData')
            if 'matchPlayerStats' in script.string: found.append('matchPlayerStats')
            if 'shotsData' in script.string: found.append('shotsData')
            
    print(f"Found Data: {found}")

if __name__ == "__main__":
    mid = inspect_league()
    if mid:
        inspect_match(mid)
