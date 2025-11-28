import pandas as pd
import xgboost as xgb
from sqlalchemy import create_engine
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import LabelEncoder

DB_CONNECTION = "postgresql://postgres@localhost:5432/football_prediction_db"

def train_advanced_model():
    engine = create_engine(DB_CONNECTION)
    
    print("📥 Loading Data...")
    df = pd.read_sql("SELECT * FROM model_features ORDER BY date ASC", engine)

    # --- 1. DEFINE TARGET (3-Class) ---
    # 0 = Away Win, 1 = Draw, 2 = Home Win
    def get_result(row):
        if row['home_goals'] > row['away_goals']: return 2
        elif row['home_goals'] == row['away_goals']: return 1
        else: return 0
        
    df['match_result'] = df.apply(get_result, axis=1)

    # --- 2. FEATURES ---
    features = [
        'elo_diff', 'home_elo', 'away_elo',
        'home_xg_last_5', 'away_xg_last_5',
        'home_points_last_5', 'away_points_last_5'
    ]
    
    X = df[features]
    y = df['match_result']

    # --- 3. TIME SPLIT ---
    split = int(len(df) * 0.85)
    X_train, y_train = X.iloc[:split], y.iloc[:split]
    X_test, y_test = X.iloc[split:], y.iloc[split:]

    print(f"🧠 Training XGBoost on {len(X_train)} matches...")

    # --- 4. XGBOOST MODEL ---
    model = xgb.XGBClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=4,
        objective='multi:softprob', # Multi-class probability
        num_class=3,
        random_state=42
    )
    
    model.fit(X_train, y_train)

    # --- 5. EVALUATE ---
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    
    print("\n" + "="*30)
    print(f"🏆 XGBOOST RESULTS (3-Way)")
    print("="*30)
    print(f"✅ Overall Accuracy: {acc:.2%}")
    print("\nDetailed Report:")
    print(classification_report(y_test, preds, target_names=['Away', 'Draw', 'Home']))
    
    # Save model for the dashboard to use later
    model.save_model("football_model.json")
    print("💾 Model saved to 'football_model.json'")

if __name__ == "__main__":
    train_advanced_model()