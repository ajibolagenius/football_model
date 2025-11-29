import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

def get_env(key, default=None):
    """Get environment variable with fallback to Streamlit Secrets."""
    # 1. Try os.getenv (Local .env or System Env)
    val = os.getenv(key)
    if val:
        return val
    
    # 2. Try Streamlit Secrets (Cloud)
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except:
        pass
    
    return default

# Database Connection
DB_CONNECTION = get_env("DB_CONNECTION", "postgresql://postgres@localhost:5432/football_prediction_db")

# API Keys
ODDS_API_KEY = get_env("ODDS_API_KEY")
RAPIDAPI_KEY = get_env("RAPIDAPI_KEY")
FOOTBALL_DATA_ORG_KEY = get_env("FOOTBALL_DATA_ORG_KEY")

# Other Settings
LOG_LEVEL = get_env("LOG_LEVEL", "INFO")
MODEL_VERSION = "V5"
ELO_K_FACTOR = 20
MODEL_FILE = "football_v5.json"
FEATURE_IMPORTANCE_FILE = "feature_importance.json"
