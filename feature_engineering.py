import pandas as pd
from sqlalchemy import create_engine, text

# --- CONFIGURATION ---
DB_CONNECTION = "postgresql://postgres@localhost:5432/football_prediction_db"

def get_db_engine():
    return create_engine(DB_CONNECTION)

# --- ELO ENGINE ---
def calculate_elo_ratings(df):
    """
    Iterates through matches chronologically to calculate Elo ratings.
    """
    print("♟️  Calculating Elo Ratings for historical context...")
    
    # Initial Elo for every team
    current_elo = {} # {team_id: 1500}
    
    # Constants
    K_FACTOR = 20 # How much the rating changes per game
    
    # We need to store the PRE-MATCH Elo for the features
    home_elos = []
    away_elos = []
    
    for index, row in df.iterrows():
        h_id = row['home_team_id']
        a_id = row['away_team_id']
        
        # Get current ratings (default to 1500 if new team)
        h_rating = current_elo.get(h_id, 1500)
        a_rating = current_elo.get(a_id, 1500)
        
        # Store these PRE-MATCH ratings (This is what the model sees)
        home_elos.append(h_rating)
        away_elos.append(a_rating)
        
        # --- Calculate Result & Update ---
        # Did Home win? (1.0), Draw (0.5), or Lose (0.0)
        if row['home_goals'] > row['away_goals']:
            actual_score = 1.0
        elif row['home_goals'] == row['away_goals']:
            actual_score = 0.5
        else:
            actual_score = 0.0
            
        # Expected Score (The Math part)
        # expected_a = 1 / (1 + 10 ^ ((Rb - Ra) / 400))
        expected_home = 1 / (1 + 10 ** ((a_rating - h_rating) / 400))
        
        # New Ratings
        new_h = h_rating + K_FACTOR * (actual_score - expected_home)
        new_a = a_rating + K_FACTOR * ((1 - actual_score) - (1 - expected_home))
        
        # Save for next match
        current_elo[h_id] = new_h
        current_elo[a_id] = new_a

    # Add columns to DF
    df['home_elo'] = home_elos
    df['away_elo'] = away_elos
    df['elo_diff'] = df['home_elo'] - df['away_elo'] # Positive means Home is favorite
    
    return df

def process_features():
    engine = get_db_engine()
    
    print("📥 Loading raw match data...")
    query = """
    SELECT 
        m.match_id, m.date, m.home_team_id, m.away_team_id,
        m.home_goals, m.away_goals,
        s.home_xg, s.away_xg,
        CASE 
            WHEN m.home_goals > m.away_goals THEN 3 
            WHEN m.home_goals = m.away_goals THEN 1 
            ELSE 0 
        END as home_points,
        CASE 
            WHEN m.away_goals > m.home_goals THEN 3 
            WHEN m.home_goals = m.away_goals THEN 1 
            ELSE 0 
        END as away_points
    FROM matches m
    JOIN match_stats s ON m.match_id = s.match_id
    ORDER BY m.date ASC;
    """
    df = pd.read_sql(query, engine)
    
    # --- 1. APPLY ELO RATINGS ---
    # We must do this BEFORE the rolling averages
    df = calculate_elo_ratings(df)

    # --- 2. CALCULATE ROLLING AVERAGES ---
    print("🔄 Calculating Rolling Averages (Last 5 Games)...")
    
    # Split into Home and Away dataframes to group by team
    home_df = df[['date', 'match_id', 'home_team_id', 'home_goals', 'home_xg', 'home_points']].copy()
    home_df.columns = ['date', 'match_id', 'team_id', 'goals', 'xg', 'points']
    home_df['is_home'] = 1

    away_df = df[['date', 'match_id', 'away_team_id', 'away_goals', 'away_xg', 'away_points']].copy()
    away_df.columns = ['date', 'match_id', 'team_id', 'goals', 'xg', 'points']
    away_df['is_home'] = 0

    team_stats = pd.concat([home_df, away_df]).sort_values(['team_id', 'date'])

    rolling_cols = ['goals', 'xg', 'points']
    for col in rolling_cols:
        team_stats[f'avg_{col}_last_5'] = (
            team_stats.groupby('team_id')[col]
            .transform(lambda x: x.rolling(window=5, min_periods=3).mean().shift(1))
        )

    # Re-merge
    home_features = team_stats[team_stats['is_home'] == 1][['match_id', 'avg_goals_last_5', 'avg_xg_last_5', 'avg_points_last_5']]
    away_features = team_stats[team_stats['is_home'] == 0][['match_id', 'avg_goals_last_5', 'avg_xg_last_5', 'avg_points_last_5']]
    
    home_features.columns = ['match_id', 'home_goals_last_5', 'home_xg_last_5', 'home_points_last_5']
    away_features.columns = ['match_id', 'away_goals_last_5', 'away_xg_last_5', 'away_points_last_5']

    final_df = df.merge(home_features, on='match_id').merge(away_features, on='match_id')

    # Drop NaNs
    final_df.dropna(inplace=True)
    
    # Target
    final_df['target_home_win'] = (final_df['home_goals'] > final_df['away_goals']).astype(int)

    print(f"📊 Final Dataset: {len(final_df)} matches.")
    final_df.to_sql('model_features', engine, if_exists='replace', index=False)
    print("✨ Feature Engineering (with Elo) Complete!")

if __name__ == "__main__":
    process_features()