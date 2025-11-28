import pandas as pd
import xgboost as xgb
import numpy as np
from sqlalchemy import create_engine
import matplotlib.pyplot as plt

DB_CONNECTION = "postgresql://postgres@localhost:5432/football_prediction_db"

def run_backtest():
    engine = create_engine(DB_CONNECTION)
    
    # 1. Load Data
    print("📥 Loading Data for Backtest...")
    # We need odds to simulate profit. 
    # Since our scraper didn't get odds for every historical match, 
    # we will SIMULATE odds based on Elo just for this test.
    # In production, you MUST use real odds from the database.
    
    df = pd.read_sql("SELECT * FROM model_features_v2 ORDER BY date ASC", engine)
    
    # 2. Load Model
    model = xgb.XGBClassifier()
    model.load_model("football_xgb.json")
    
    # 3. Prepare Test Set (The 'Future')
    split = int(len(df) * 0.80)
    test_df = df.iloc[split:].copy()
    
    features = [
        'elo_diff', 'home_elo', 'away_elo',
        'home_rest_days', 'away_rest_days',
        'home_xg_last_5', 'away_xg_last_5',
        'home_points_last_5', 'away_points_last_5'
    ]
    
    print(f"🎰 Simulating bets on {len(test_df)} matches...")
    
    # Predict Probabilities
    probs = model.predict_proba(test_df[features])
    test_df['prob_away'] = probs[:, 0]
    test_df['prob_draw'] = probs[:, 1]
    test_df['prob_home'] = probs[:, 2]
    
    # --- SIMULATION LOOP ---
    bankroll = 1000
    history = [bankroll]
    bets_placed = 0
    wins = 0
    
    for index, row in test_df.iterrows():
        # SIMULATING BOOKMAKER ODDS (Fair Odds + 5% Margin)
        # In real life, replace these lines with: odds = row['home_odds']
        # This is just to test the logic if you don't have historical odds data
        fair_prob = 1 / (1 + 10 ** ((row['away_elo'] - row['home_elo']) / 400))
        implied_home_odds = (1 / fair_prob)
        bookie_home_odds = round(implied_home_odds * 0.95, 2) # Bookie takes margin
        
        # STRATEGY: Bet on Home if Model Confidence > Implied Probability + 5% edge
        model_conf = row['prob_home']
        implied_prob = 1 / bookie_home_odds
        
        if model_conf > (implied_prob + 0.05):
            # We place a bet!
            stake = 50 # Flat bet $50
            bets_placed += 1
            
            bankroll -= stake
            
            # Did we win? (Result == 2 means Home Win)
            if row['match_result'] == 2:
                winnings = stake * bookie_home_odds
                bankroll += winnings
                wins += 1
                
        history.append(bankroll)
        
    print("\n" + "="*30)
    print("💰 BACKTEST RESULTS")
    print("="*30)
    print(f"Final Bankroll: ${bankroll:.2f}")
    print(f"Total Return:   {((bankroll - 1000)/1000)*100:.2f}%")
    print(f"Bets Placed:    {bets_placed}")
    print(f"Win Rate:       {(wins/bets_placed)*100 if bets_placed > 0 else 0:.2f}%")
    print("="*30)
    
    if bankroll > 1000:
        print("✅ The Strategy is PROFITABLE!")
    else:
        print("❌ The Strategy Lost Money.")

if __name__ == "__main__":
    run_backtest()