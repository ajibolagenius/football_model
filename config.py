import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = "postgresql://postgres.xyrqkttjzuuykbwwaafk:SupabaseOracle@aws-1-eu-central-1.pooler.supabase.com:6543/postgres"

DB_CONNECTION = os.getenv("DATABASE_URL", SUPABASE_URL)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "") 
RAPIDAPI_HOST = "api-football-v1.p.rapidapi.com"