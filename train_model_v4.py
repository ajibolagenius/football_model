import pandas as pd
import xgboost as xgb
import sys
import numpy as np
from sqlalchemy import create_engine
from sklearn.metrics import accuracy_score, classification_report

DB_CONNECTION = "postgresql://postgres@localhost:5432/football_prediction_db"

def train_v4():
    engine = create_engine(DB_CONNECTION)
    print("📥 Loading V4 Data...")
    
    try:
        df = pd.read_sql("SELECT * FROM model_features_v4 ORDER BY date ASC", engine)
    except Exception as e:
        print("❌ Error: Could not read table 'model_features_v4'. Run feature engineering first.")
        sys.exit(1)
        
    if df.empty:
        print("❌ Error: The 'model_features_v4' table is empty!")
        sys.exit(1)

    # --- DATA CLEANING (THE FIX) ---
    # Force all tactical columns to be numeric, turning errors into NaNs
    tactical_cols = [
        'home_ppda_5', 'away_ppda_5', 
        'home_deep_5', 'away_deep_5', 
        'home_xg_5', 'away_xg_5',
        'home_rest', 'away_rest'
    ]
    
    print("🧹 Cleaning data types...")
    for col in tactical_cols:
        # Force to numeric
        df[col] = pd.to_numeric(df[col], errors='coerce')
        # Fill any resulting NaNs with the column average
        df[col] = df[col].fillna(df[col].mean())

    print(f"   -> Loaded {len(df)} training samples.")
    
    features = [
        'elo_diff', 
        'home_rest', 'away_rest',
        'home_ppda_5', 'away_ppda_5',
        'home_deep_5', 'away_deep_5',
        'home_xg_5', 'away_xg_5'
    ]
    
    target = 'match_result'
    
    split = int(len(df) * 0.85)
    X_train = df[features].iloc[:split]
    y_train = df[target].iloc[:split]
    X_test = df[features].iloc[split:]
    y_test = df[target].iloc[split:]
    
    print(f"🧠 Training with TACTICS on {len(X_train)} matches...")
    
    model = xgb.XGBClassifier(
        n_estimators=300,
        learning_rate=0.03,
        max_depth=4,
        objective='multi:softprob',
        num_class=3,
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    
    print("\n" + "="*30)
    print(f"🏆 MODEL V4 RESULTS")
    print("="*30)
    print(f"✅ Accuracy: {acc:.2%}")
    print(classification_report(y_test, preds, target_names=['Away', 'Draw', 'Home']))
    
    print("\n🧐 Tactical Importance:")
    fi = pd.DataFrame({'Feature': features, 'Importance': model.feature_importances_}).sort_values('Importance', ascending=False)
    print(fi)
    
    model.save_model("football_v4.json")

if __name__ == "__main__":
    train_v4()