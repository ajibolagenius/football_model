import pandas as pd
import xgboost as xgb
import numpy as np
from sqlalchemy import create_engine
from sklearn.metrics import accuracy_score, classification_report

DB_CONNECTION = "postgresql://postgres@localhost:5432/football_prediction_db"

def train_xgb():
    engine = create_engine(DB_CONNECTION)
    print("📥 Loading V2 Features...")
    df = pd.read_sql("SELECT * FROM model_features_v2 ORDER BY date ASC", engine)
    
    # NEW FEATURES INCLUDED
    features = [
        'elo_diff', 'home_elo', 'away_elo',
        'home_rest_days', 'away_rest_days', # The Fatigue Factor
        'home_xg_last_5', 'away_xg_last_5',
        'home_points_last_5', 'away_points_last_5'
    ]
    target = 'match_result' # 0=Away, 1=Draw, 2=Home
    
    # Time Split (80% train, 20% test)
    split = int(len(df) * 0.80)
    X_train = df[features].iloc[:split]
    y_train = df[target].iloc[:split]
    X_test = df[features].iloc[split:]
    y_test = df[target].iloc[split:]
    
    print(f"🧠 Training XGBoost on {len(X_train)} matches...")
    
    # XGBoost Classifier
    model = xgb.XGBClassifier(
        n_estimators=500,        # More trees
        learning_rate=0.01,      # Slower learning = better generalization
        max_depth=4,             # Prevent overfitting
        objective='multi:softprob',
        num_class=3,
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)
    
    acc = accuracy_score(y_test, preds)
    
    print("\n" + "="*30)
    print(f"🏆 XGBOOST RESULTS")
    print("="*30)
    print(f"✅ Accuracy: {acc:.2%}")
    print("\n" + classification_report(y_test, preds, target_names=['Away', 'Draw', 'Home']))
    
    # Feature Importance
    print("\n🧐 What matters most?")
    importances = model.feature_importances_
    fi = pd.DataFrame({'Feature': features, 'Importance': importances}).sort_values('Importance', ascending=False)
    print(fi)
    
    # Save Model
    model.save_model("football_xgb.json")
    print("\n💾 Model saved as 'football_xgb.json'")

if __name__ == "__main__":
    train_xgb()