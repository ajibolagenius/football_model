from sqlalchemy import create_engine, text

DB_CONNECTION = "postgresql://postgres@localhost:5432/football_prediction_db"

def apply_schema():
    engine = create_engine(DB_CONNECTION)
    print("Applying Schema V2...")
    with open("schema_v2.sql", "r") as f:
        sql = f.read()
        
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    print("✅ Schema V2 applied successfully!")

if __name__ == "__main__":
    apply_schema()
