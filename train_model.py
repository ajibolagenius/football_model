import pandas as pd
from sqlalchemy import create_engine
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, precision_score
from sklearn.model_selection import TimeSeriesSplit
import numpy as np

# --- CONFIGURATION ---
DB_CONNECTION = "postgresql://postgres@localhost:5432/football_prediction_db"

def get_db_engine():
    return create_engine(DB_CONNECTION)

def train_football_model():
    engine = get_db_engine()
    
    print("📥 Loading feature data from Database...")
    df = pd.read_sql("SELECT * FROM model_features ORDER BY date ASC", engine)
    
    # 1. Define Features (X) and Target (y)
    # We remove ID columns and the actual result columns (goals) because those are the answers!
    features = [
        'home_goals_last_5', 'away_goals_last_5',
        'home_xg_last_5', 'away_xg_last_5',
        'home_points_last_5', 'away_points_last_5'
    ]
    target = 'target_home_win' # 1 if Home Wins, 0 if Draw/Away Win
    
    X = df[features]
    y = df[target]
    
    print(f"📊 Dataset Shape: {X.shape}")
    
    # 2. Time-Series Split
    # We train on the first 80% of matches, test on the remaining 20% (the "future")
    split_index = int(len(df) * 0.8)
    
    X_train = X.iloc[:split_index]
    y_train = y.iloc[:split_index]
    
    X_test = X.iloc[split_index:]
    y_test = y.iloc[split_index:]
    
    print(f"🧠 Training on {len(X_train)} matches. Testing on {len(X_test)} matches...")

    # 3. Train the Random Forest
    model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=5)
    model.fit(X_train, y_train)
    
    # 4. Predict
    predictions = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1] # Probability of Home Win
    
    # 5. Evaluate
    acc = accuracy_score(y_test, predictions)
    prec = precision_score(y_test, predictions)
    
    print("\n" + "="*30)
    print(f"🏆 MODEL RESULTS")
    print("="*30)
    print(f"✅ Accuracy:  {acc:.2%}")
    print(f"🎯 Precision: {prec:.2%} (When we predict Home Win, how often are we right?)")
    print("-" * 30)
    
    # 6. Feature Importance (What matters most?)
    importances = model.feature_importances_
    feature_imp = pd.DataFrame({'Feature': features, 'Importance': importances})
    feature_imp = feature_imp.sort_values('Importance', ascending=False)
    
    print("\n🧐 What did the model learn? (Feature Importance):")
    print(feature_imp)
    
    # 7. Show some specific predictions
    print("\n🔮 Sample Predictions vs Reality (Last 5 games):")
    results = df.iloc[split_index:].copy()
    results['Model_Prob_HomeWin'] = probs
    results['Model_Prediction'] = predictions
    
    # Join with team names for readability (Optional fetch, or just show IDs)
    print(results[['date', 'home_team_id', 'away_team_id', 'target_home_win', 'Model_Prediction', 'Model_Prob_HomeWin']].tail())

if __name__ == "__main__":
    train_football_model()