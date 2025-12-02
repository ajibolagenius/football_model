import os

SUPABASE_URL = "postgresql://postgres:SupabaseOracle@db.xyrqkttjzuuykbwwaafk.supabase.co:5432/postgres"

DB_CONNECTION = os.getenv("DATABASE_URL", SUPABASE_URL)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")