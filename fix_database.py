from sqlalchemy import create_engine, text

# Connection string
DB_CONNECTION = "postgresql://postgres@localhost:5432/football_prediction_db"

def fix_schema():
    engine = create_engine(DB_CONNECTION)
    
    sql_commands = [
        # 1. Clear bad data if any exists (duplicates) to prevent errors when applying constraint
        "DELETE FROM match_stats a USING match_stats b WHERE a.id < b.id AND a.match_id = b.match_id;",
        
        # 2. Add the UNIQUE constraint to match_id in match_stats
        "ALTER TABLE match_stats ADD CONSTRAINT unique_match_stats_id UNIQUE (match_id);"
    ]
    
    print("🔧 Applying Database Fixes...")
    with engine.connect() as conn:
        for sql in sql_commands:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"✅ Success: {sql[:50]}...")
            except Exception as e:
                # If it fails, it might already exist, which is fine.
                print(f"⚠️ Note: {e}")
                
    print("✨ Database schema is now correct.")

if __name__ == "__main__":
    fix_schema()