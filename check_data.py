import pandas as pd
from sqlalchemy import create_engine

DB_CONNECTION = "postgresql://postgres@localhost:5432/football_prediction_db"

def check_tactical_data():
    engine = create_engine(DB_CONNECTION)
    
    print("🔍 Checking Database Health...")
    
    # Check how many rows have non-null PPDA
    query = """
    SELECT 
        COUNT(*) as total_matches,
        COUNT(home_ppda) as matches_with_ppda,
        COUNT(home_deep) as matches_with_deep
    FROM match_stats
    """
    df = pd.read_sql(query, engine)
    
    total = df.iloc[0]['total_matches']
    filled = df.iloc[0]['matches_with_ppda']
    
    print(f"📊 Total Matches: {total}")
    print(f"✅ With Tactics:  {filled}")
    print(f"❌ Missing Data:  {total - filled}")
    
    if filled == 0:
        print("\n🚨 CRITICAL FAILURE: No tactical data found!")
        print("The scraper is running but not saving. This is likely a Name Mismatch.")
        
        # Show us the team names so we can map them
        print("\n📋 Your Database Team Names:")
        teams = pd.read_sql("SELECT name FROM teams ORDER BY name", engine)
        print(teams['name'].tolist())

if __name__ == "__main__":
    check_tactical_data()