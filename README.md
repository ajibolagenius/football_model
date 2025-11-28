# Football Predictive Model - Data Pipeline

## 1. Get Your API Key

- Go to [RapidAPI - API-Football](https://rapidapi.com/api-sports/api/api-football).

- Sign up (it's free).

- Subscribe to the Basic (Free) plan.

- Copy your `X-RapidAPI-Key`.

- Paste it into line 16 of `etl_pipeline.py`.

## 2. Prepare the Database

Ensure PostgreSQL is running on your Mac:

```bash
brew services start postgresql@14
```

Create the database and run the schema:

```bash
createdb football_prediction_db
psql -d football_prediction_db -f schema.sql
```

## 3. Run the Pipeline

```bash
python3 etl_pipeline.py
```

## Note on Name Matching

One of the biggest challenges in sports data is that the API might call a team "Manchester United" while the scraping site calls it "Man Utd".

- Current Solution: The script uses exact string matching.

- Future Upgrade: We will implement a fuzzywuzzy matching logic to handle these discrepancies automatically.