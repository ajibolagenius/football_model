from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import xgboost as xgb
import pandas as pd
import os
from sqlalchemy import create_engine
import sys

# Add parent directory to path to access config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from config import DB_CONNECTION
except ImportError:
    # Fallback if running locally in isolation
    DB_CONNECTION = os.getenv("DATABASE_URL", "postgresql://postgres@localhost:5432/football_prediction_db")

app = FastAPI(title="Football Oracle Brain")

# Load Model Once on Startup
model = xgb.XGBClassifier()
MODEL_PATH = "../football_v5.json" # Path relative to this folder

if os.path.exists(MODEL_PATH):
    model.load_model(MODEL_PATH)
    print("🧠 Model Loaded Successfully")
else:
    print("⚠️ Warning: Model file not found.")

# Define Request Structure
class MatchRequest(BaseModel):
    home_team_id: int
    away_team_id: int
    # Optional: Allow passing manual stats for "What-If" scenarios
    home_rest: float = 7.0
    away_rest: float = 7.0

@app.get("/")
def health_check():
    return {"status": "online", "model_loaded": os.path.exists(MODEL_PATH)}

@app.post("/predict/match_id")
def predict_by_id(match_id: str):
    """
    Predicts a match based on features already in the DB (model_features_v5).
    Best for upcoming scheduled games.
    """
    engine = create_engine(DB_CONNECTION)
    
    # Fetch features from DB
    query = f"SELECT * FROM model_features_v5 WHERE match_id = '{match_id}'"
    try:
        df = pd.read_sql(query, engine)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    if df.empty:
        raise HTTPException(status_code=404, detail="Match features not found. Run feature engineering.")

    # Define features exactly as trained
    features = [
        'elo_diff', 'home_rest', 'away_rest',
        'home_ppda_5', 'away_ppda_5',
        'home_deep_5', 'away_deep_5',
        'home_xg_5', 'away_xg_5'
    ]
    
    # Predict
    try:
        probs = model.predict_proba(df[features])[0]
        return {
            "match_id": match_id,
            "prob_away": float(probs[0]),
            "prob_draw": float(probs[1]),
            "prob_home": float(probs[2]),
            "verdict": "Home Win" if probs[2] > 0.5 else "Not Clear"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

# Run with: uvicorn ml_api.main:app --reload