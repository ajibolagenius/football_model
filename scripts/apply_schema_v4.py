from sqlalchemy import create_engine, text
import sys
import os

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config

DB_CONNECTION = config.DB_CONNECTION

def apply_schema():
    engine = create_engine(DB_CONNECTION)
    print("Applying Schema V4 (Advanced Metrics)...")
    
    # Path to SQL file
    sql_path = os.path.join(os.path.dirname(__file__), '..', 'sql', 'schema_v4.sql')
    
    with open(sql_path, "r") as f:
        sql = f.read()
        
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
        
    print("✅ Schema V4 applied successfully!")

if __name__ == "__main__":
    apply_schema()
