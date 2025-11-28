import time
from scraper_pipeline import scrape_understat_full, store_scraped_data

# We want 7 years of history to train a robust model
SEASONS = ["2019", "2020", "2021", "2022", "2023", "2024", "2025"]
LEAGUE = "EPL"

def run_bulk_import():
    print(f"🚀 Starting Bulk Import for {LEAGUE} ({len(SEASONS)} seasons)...")
    
    total_matches = 0
    
    for season in SEASONS:
        print(f"\n📅 Processing Season: {season}/{int(season)+1}...")
        
        # 1. Scrape
        data = scrape_understat_full(LEAGUE, season)
        
        if data:
            # 2. Store
            store_scraped_data(data)
            total_matches += len(data)
            print(f"✅ Season {season} saved.")
        else:
            print(f"⚠️ Skipped Season {season} (No data).")
            
        # Be polite to the server (Anti-ban protection)
        print("💤 Sleeping for 3 seconds...")
        time.sleep(3)

    print("\n" + "="*40)
    print(f"🎉 BULK IMPORT COMPLETE")
    print(f"📚 Total Matches in DB: ~{total_matches}")
    print("="*40)
    print("👉 Now run: python3 feature_engineering.py")

if __name__ == "__main__":
    run_bulk_import()