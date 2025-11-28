import pandas as pd
import numpy as np
from sqlalchemy import create_engine

DB_CONNECTION = "postgresql://postgres@localhost:5432/football_prediction_db"

def process_features_v4():
    engine = create_engine(DB_CONNECTION)
    print("📥 Loading V4 Data (with Tactics)...")
    
    query = """
    SELECT m.match_id, m.date, m.home_team_id, m.away_team_id, 
           m.home_goals, m.away_goals, 
           s.home_xg, s.away_xg,
           s.home_ppda, s.away_ppda,
           s.home_deep, s.away_deep
    FROM matches m 
    JOIN match_stats s ON m.match_id = s.match_id
    ORDER BY m.date ASC;
    """
    df = pd.read_sql(query, engine)
    print(f"   -> Loaded {len(df)} raw matches.")
    
    # --- 1. Rest Days ---
    df['date'] = pd.to_datetime(df['date'])
    home = df[['date', 'home_team_id']].rename(columns={'home_team_id': 'team_id'})
    away = df[['date', 'away_team_id']].rename(columns={'away_team_id': 'team_id'})
    all_matches = pd.concat([home, away]).sort_values(['team_id', 'date'])
    all_matches['rest'] = all_matches.groupby('team_id')['date'].diff().dt.days.fillna(7)
    
    df = df.merge(all_matches, left_on=['date', 'home_team_id'], right_on=['date', 'team_id'], how='left').rename(columns={'rest': 'home_rest'}).drop('team_id', axis=1)
    df = df.merge(all_matches, left_on=['date', 'away_team_id'], right_on=['date', 'team_id'], how='left').rename(columns={'rest': 'away_rest'}).drop('team_id', axis=1)

    # --- 2. Elo Calculation ---
    current_elo = {}
    h_elos, a_elos = [], []
    for idx, row in df.iterrows():
        hid, aid = row['home_team_id'], row['away_team_id']
        hr = current_elo.get(hid, 1500)
        ar = current_elo.get(aid, 1500)
        h_elos.append(hr)
        a_elos.append(ar)
        
        if row['home_goals'] > row['away_goals']: act = 1
        elif row['home_goals'] == row['away_goals']: act = 0.5
        else: act = 0
        exp = 1 / (1 + 10**((ar - hr)/400))
        current_elo[hid] = hr + 20 * (act - exp)
        current_elo[aid] = ar + 20 * ((1-act) - (1-exp))
        
    df['home_elo'] = h_elos
    df['away_elo'] = a_elos
    df['elo_diff'] = df['home_elo'] - df['away_elo']

    # --- 3. TACTICAL ROLLING AVERAGES ---
    print("🔄 Calculating Rolling Tactical Form...")
    
    # We fill missing raw tactical stats with league averages BEFORE rolling
    # This prevents the rolling window from becoming NaN
    avg_ppda = df[['home_ppda', 'away_ppda']].mean().mean()
    avg_deep = df[['home_deep', 'away_deep']].mean().mean()
    avg_xg = df[['home_xg', 'away_xg']].mean().mean()
    
    df['home_ppda'] = df['home_ppda'].fillna(avg_ppda)
    df['away_ppda'] = df['away_ppda'].fillna(avg_ppda)
    df['home_deep'] = df['home_deep'].fillna(avg_deep)
    df['away_deep'] = df['away_deep'].fillna(avg_deep)
    df['home_xg'] = df['home_xg'].fillna(avg_xg)
    df['away_xg'] = df['away_xg'].fillna(avg_xg)

    h_stats = df[['date', 'match_id', 'home_team_id', 'home_ppda', 'home_deep', 'home_xg']].rename(columns={'home_team_id':'team', 'home_ppda':'ppda', 'home_deep':'deep', 'home_xg':'xg'})
    a_stats = df[['date', 'match_id', 'away_team_id', 'away_ppda', 'away_deep', 'away_xg']].rename(columns={'away_team_id':'team', 'away_ppda':'ppda', 'away_deep':'deep', 'away_xg':'xg'})
    
    all_stats = pd.concat([h_stats, a_stats]).sort_values(['team', 'date'])
    
    for col in ['ppda', 'deep', 'xg']:
        all_stats[f'avg_{col}_5'] = all_stats.groupby('team')[col].transform(lambda x: x.rolling(5, min_periods=1).mean().shift(1))
        
    cols_to_keep = ['match_id', 'team', 'avg_ppda_5', 'avg_deep_5', 'avg_xg_5']
    
    df = df.merge(all_stats[cols_to_keep], left_on=['match_id', 'home_team_id'], right_on=['match_id', 'team'], how='left').rename(columns={'avg_ppda_5': 'home_ppda_5', 'avg_deep_5': 'home_deep_5', 'avg_xg_5': 'home_xg_5'}).drop('team', axis=1)
    
    df = df.merge(all_stats[cols_to_keep], left_on=['match_id', 'away_team_id'], right_on=['match_id', 'team'], how='left').rename(columns={'avg_ppda_5': 'away_ppda_5', 'avg_deep_5': 'away_deep_5', 'avg_xg_5': 'away_xg_5'}).drop('team', axis=1)
    
    # FILL REMAINING NANS (For the first game of season)
    # If no history, assume average form
    for col in ['home_ppda_5', 'away_ppda_5', 'home_deep_5', 'away_deep_5', 'home_xg_5', 'away_xg_5']:
        df[col] = df[col].fillna(df[col].mean())

    def get_res(row):
        if row['home_goals'] > row['away_goals']: return 2
        elif row['home_goals'] == row['away_goals']: return 1
        else: return 0
    df['match_result'] = df.apply(get_res, axis=1)
    
    # Only drop if truly critical info is missing
    df.dropna(subset=['match_result'], inplace=True)
    
    print(f"📊 V4 Features Ready: {len(df)} matches.")
    df.to_sql('model_features_v4', engine, if_exists='replace', index=False)
    print("✨ Saved to 'model_features_v4'")

if __name__ == "__main__":
    process_features_v4()