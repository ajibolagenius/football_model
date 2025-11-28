from sqlalchemy import create_engine, inspect

DB_CONNECTION = "postgresql://postgres@localhost:5432/football_prediction_db"
engine = create_engine(DB_CONNECTION)
inspector = inspect(engine)
print(inspector.get_table_names())
