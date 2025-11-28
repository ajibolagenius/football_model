import pandas as pd
from sqlalchemy import create_engine

DB_CONNECTION = "postgresql://postgres@localhost:5432/football_prediction_db"

def get_db_engine():
    return create_engine(DB_CONNECTION)

def calculate_elo_ratings(df):
    """Calculates Elo ratings match-by-match."""
    current_elo = {}
    K_FACTOR = 20
    
    home_elos = []
    away_elos = []
    
    for index, row in df.iterrows():
        h_id = row['home_team_id']
        a_id = row['away_team_id']
        
        h_rating = current_elo.get(h_id, 1500)
        a_rating = current_elo.get(a_id, 1500)
        
        home_elos.append(h_rating)
        away_elos.append(a_rating)
        
        # Outcome
        if row['home_goals'] > row['away_goals']: actual = 1.0
        elif row['home_goals'] == row['away_goals']: actual = 0.5
        else: actual = 0.0
        
        expected_h = 1 / (1 + 10 ** ((a_rating - h_rating) / 400))
        
        new_h = h_rating + K_FACTOR * (actual - expected_h)
        new_a = a_rating + K_FACTOR * ((1 - actual) - (1 - expected_h))
        
        current_elo[h_id] = new_h
        current_elo[a_id] = new_a
        
    df['home_elo'] = home_elos
    df['away_elo'] = away_elos
    df['elo_diff'] = df['home_elo'] - df['away_elo']
    return df

def calculate_rest_days(df):
    """Calculates days since last match for both teams."""
    print("💤 Calculating Rest Days (Fatigue)...")
    df['date'] = pd.to_datetime(df['date'])
    
    # We need a long format (date, team_id) to sort and diff
    home_matches = df[['date', 'home_team_id']].rename(columns={'home_team_id': 'team_id'})
    away_matches = df[['date', 'away_team_id']].rename(columns={'away_team_id': 'team_id'})
    all_matches = pd.concat([home_matches, away_matches]).sort_values(['team_id', 'date'])
    
    # Calculate difference in days between matches
    all_matches['days_since_last'] = all_matches.groupby('team_id')['date'].diff().dt.days
    
    # Fill NaN (first match) with 7 days rest default
    all_matches['days_since_last'] = all_matches['days_since_last'].fillna(7)
    
    # Merge back to main DF
    # We need to do this carefully for Home and Away columns
    
    # 1. Merge for Home Team
    df = df.merge(all_matches, left_on=['date', 'home_team_id'], right_on=['date', 'team_id'], how='left')
    df.rename(columns={'days_since_last': 'home_rest_days'}, inplace=True)
    df.drop('team_id', axis=1, inplace=True)
    
    # 2. Merge for Away Team
    df = df.merge(all_matches, left_on=['date', 'away_team_id'], right_on=['date', 'team_id'], how='left')
    df.rename(columns={'days_since_last': 'away_rest_days'}, inplace=True)
    df.drop('team_id', axis=1, inplace=True)
    
    return df

def process_features_v2():
    engine = get_db_engine()
    print("📥 Loading raw match data...")
    
    # We fetch ALL columns we need
    query = """
    SELECT 
        m.match_id, m.date, m.home_team_id, m.away_team_id,
        m.home_goals, m.away_goals,
        s.home_xg, s.away_xg
    FROM matches m
    JOIN match_stats s ON m.match_id = s.match_id
    ORDER BY m.date ASC;
    """
    df = pd.read_sql(query, engine)
    
    # 1. Add Elo
    df = calculate_elo_ratings(df)
    
    # 2. Add Rest Days (NEW!)
    df = calculate_rest_days(df)

    # 3. Rolling Averages
    print("🔄 Calculating Rolling Stats...")
    
    # Points logic
    df['home_points'] = df.apply(lambda x: 3 if x['home_goals'] > x['away_goals'] else (1 if x['home_goals'] == x['away_goals'] else 0), axis=1)
    df['away_points'] = df.apply(lambda x: 3 if x['away_goals'] > x['home_goals'] else (1 if x['home_goals'] == x['away_goals'] else 0), axis=1)

    # Split to rolling
    home_df = df[['date', 'match_id', 'home_team_id', 'home_goals', 'home_xg', 'home_points']].copy()
    home_df.columns = ['date', 'match_id', 'team_id', 'goals', 'xg', 'points']
    home_df['is_home'] = 1

    away_df = df[['date', 'match_id', 'away_team_id', 'away_goals', 'away_xg', 'away_points']].copy()
    away_df.columns = ['date', 'match_id', 'team_id', 'goals', 'xg', 'points']
    away_df['is_home'] = 0

    team_stats = pd.concat([home_df, away_df]).sort_values(['team_id', 'date'])

    for col in ['goals', 'xg', 'points']:
        team_stats[f'avg_{col}_last_5'] = (
            team_stats.groupby('team_id')[col]
            .transform(lambda x: x.rolling(window=5, min_periods=3).mean().shift(1))
        )

    # Re-merge
    h_feats = team_stats[team_stats['is_home'] == 1][['match_id', 'avg_goals_last_5', 'avg_xg_last_5', 'avg_points_last_5']]
    h_feats.columns = ['match_id', 'home_goals_last_5', 'home_xg_last_5', 'home_points_last_5']
    
    a_feats = team_stats[team_stats['is_home'] == 0][['match_id', 'avg_goals_last_5', 'avg_xg_last_5', 'avg_points_last_5']]
    a_feats.columns = ['match_id', 'away_goals_last_5', 'away_xg_last_5', 'away_points_last_5']
    
    final_df = df.merge(h_feats, on='match_id').merge(a_feats, on='match_id')
    final_df.dropna(inplace=True)
    
    # 0 = Away, 1 = Draw, 2 = Home
    def get_res(row):
        if row['home_goals'] > row['away_goals']: return 2
        elif row['home_goals'] == row['away_goals']: return 1
        else: return 0
    final_df['match_result'] = final_df.apply(get_res, axis=1)

    print(f"📊 Features V2 Ready: {len(final_df)} matches.")
    final_df.to_sql('model_features_v2', engine, if_exists='replace', index=False)
    print("✨ Saved to table 'model_features_v2'")

if __name__ == "__main__":
    process_features_v2()