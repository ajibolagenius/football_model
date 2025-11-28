from sqlalchemy import create_engine, text
import config

DB_CONNECTION = config.DB_CONNECTION

def apply_schema():
    engine = create_engine(DB_CONNECTION)
    print("Applying Schema V3 (Leagues)...")
    with open("schema_v3.sql", "r") as f:
        sql = f.read()
        
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    print("✅ Schema V3 applied successfully!")

if __name__ == "__main__":
    apply_schema()
