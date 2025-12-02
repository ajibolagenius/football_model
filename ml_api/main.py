from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import xgboost as xgb
import pandas as pd
import os
import sys
from sqlalchemy import create_engine

# --- PATH CONFIGURATION (The Fix) ---
# Get the absolute path of the folder where THIS script lives (ml_api)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Go up one level to the project root
ROOT_DIR = os.path.dirname(CURRENT_DIR)
# Construct the absolute path to the model
MODEL_PATH = os.path.join(ROOT_DIR, "football_v5.json")

# Add root to sys.path so we can import config.py
sys.path.append(ROOT_DIR)

try:
    from config import DB_CONNECTION
except ImportError:
    # Fallback if config is missing
    DB_CONNECTION = os.getenv("DATABASE_URL")

app = FastAPI(title="Football Oracle Brain")

# Load Model
model = xgb.XGBClassifier()

if os.path.exists(MODEL_PATH):
    try:
        model.load_model(MODEL_PATH)
        print(f"✅ BRAIN ONLINE: Model loaded from {MODEL_PATH}")
    except Exception as e:
        print(f"❌ MODEL CORRUPT: {e}")
else:
    print(f"⚠️ MODEL MISSING: Looked in {MODEL_PATH}")
    print("   -> Did you train the model? Run 'python3 scripts/train_model_v5.py' first.")

class PredictionRequest(BaseModel):
    match_id: str

@app.get("/")
def health():
    return {"status": "active", "model_loaded": os.path.exists(MODEL_PATH)}

@app.post("/predict")
def predict_match(req: PredictionRequest):
    engine = create_engine(DB_CONNECTION)
    
    query = f"SELECT * FROM model_features_v5 WHERE match_id = '{req.match_id}'"
    try:
        df = pd.read_sql(query, engine)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")
    
    if df.empty:
        raise HTTPException(status_code=404, detail="Features not found. Run feature engineering.")

    features = [
        'elo_diff', 'home_rest', 'away_rest',
        'home_ppda_5', 'away_ppda_5',
        'home_deep_5', 'away_deep_5',
        'home_xg_5', 'away_xg_5'
    ]
    
    # Ensure correct column order and data types
    try:
        df_input = df[features].astype(float)
        probs = model.predict_proba(df_input)[0]
        return {
            "match_id": req.match_id,
            "home_win": float(probs[2]),
            "draw": float(probs[1]),
            "away_win": float(probs[0])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction Error: {str(e)}")