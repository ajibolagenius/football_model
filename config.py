import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database Connection
DB_CONNECTION = os.getenv("DB_CONNECTION", "postgresql://postgres@localhost:5432/football_prediction_db")

# API Keys
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# Other Settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MODEL_VERSION = "V5"
ELO_K_FACTOR = 20
MODEL_FILE = "football_v5.json"
FEATURE_IMPORTANCE_FILE = "feature_importance.json"
