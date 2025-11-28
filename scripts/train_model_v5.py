import pandas as pd
import xgboost as xgb
import sys
import os
from sqlalchemy import create_engine
from sklearn.metrics import accuracy_score, classification_report

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

DB_CONNECTION = config.DB_CONNECTION

def train_v5():
    engine = create_engine(DB_CONNECTION)
    print("📥 Loading V5 Data...")
    
    try:
        df = pd.read_sql("SELECT * FROM model_features_v5 ORDER BY date ASC", engine)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
        
    if df.empty:
        print("❌ Error: Table is empty!")
        sys.exit(1)

    # Clean
    cols = [
        'home_ppda_5', 'away_ppda_5', 'home_deep_5', 'away_deep_5', 'home_xg_5', 'away_xg_5',
        'home_squad_xg_chain', 'home_squad_xg_buildup', 'away_squad_xg_chain', 'away_squad_xg_buildup'
    ]
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    features = [
        'elo_diff', 
        'home_ppda_5', 'away_ppda_5',
        'home_deep_5', 'away_deep_5',
        'home_xg_5', 'away_xg_5',
        'home_squad_xg_chain', 'home_squad_xg_buildup', # NEW
        'away_squad_xg_chain', 'away_squad_xg_buildup'  # NEW
    ]
    
    target = 'match_result'
    
    split = int(len(df) * 0.85)
    X_train = df[features].iloc[:split]
    y_train = df[target].iloc[:split]
    X_test = df[features].iloc[split:]
    y_test = df[target].iloc[split:]
    
    print(f"🧠 Training V5 on {len(X_train)} matches...")
    
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
    print(f"🏆 MODEL V5 RESULTS")
    print("="*30)
    print(f"✅ Accuracy: {acc:.2%}")
    print(classification_report(y_test, preds, target_names=['Away', 'Draw', 'Home']))
    
    print("\n🧐 Feature Importance:")
    fi = pd.DataFrame({'Feature': features, 'Importance': model.feature_importances_}).sort_values('Importance', ascending=False)
    print(fi)
    
    # Save Feature Importance
    fi.to_json(config.FEATURE_IMPORTANCE_FILE, orient='records')
    print(f"💾 Feature importance saved to {config.FEATURE_IMPORTANCE_FILE}")
    
    model.save_model(config.MODEL_FILE)
    print(f"💾 Model saved to {config.MODEL_FILE}")

if __name__ == "__main__":
    train_v5()
