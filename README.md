# ⚽ The Culture AI Oracle V5

**An AI-powered football analytics platform featuring a sleek Streamlit dashboard, advanced xG & tactical metrics, and machine learning models to forecast match outcomes and identify value bets.**

The **Culture AI Oracle** is an end-to-end data science project that scrapes football match data, engineers advanced features (Elo, Rolling xG, PPDA, Deep Completions), and uses XGBoost classifiers to predict game results. It visualizes these insights through a modern, glassmorphism-styled interface designed for strategic betting analysis.

---

## 🚀 Features

### 🏟️ Interactive Dashboard
- **Modern Glassmorphism UI**: A sleek, dark-themed interface with glass cards, neon accents, and responsive design.
- **Multi-League Support**: Analyze matches from **EPL**, **La Liga**, and **Bundesliga**.
- **Real-time Predictions**: Instant win probabilities for Home vs Away teams.
- **Live Odds Integration**: Automatically fetches live betting odds from **The Odds API** to identify value bets.
- **Kelly Criterion Calculator**: Built-in betting calculator that suggests optimal stake sizes.

### 🧠 Machine Learning Core (V5)
- **XGBoost Classifier**: Trained on historical match data, Elo ratings, and advanced tactical metrics.
- **Tactical Features**:
    - **PPDA (Passes Per Defensive Action)**: Measures pressing intensity.
    - **Deep Completions**: Measures ability to penetrate the danger zone.
    - **Rest Days**: Accounts for fatigue.
- **Feature Engineering**:
    - **Elo Ratings**: Dynamic rating system updating after every match.
    - **Rolling xG (Expected Goals)**: Tracks team performance trends.
    - **xG Chain & xG Buildup**: Advanced player contribution metrics.

### 📊 Advanced Analytics
- **Player-Level Analytics**: "Top Players" tab showing goals, assists, xG, xA, and advanced metrics (xGChain, xGBuildup).
- **Live League Standings**: Up-to-date league tables filtered by season.
- **Tactical Radar Charts**: Visual comparison of team playing styles.
- **Rolling xG Trends**: Line charts visualizing offensive and defensive performance.

---

## 🛠️ Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/) (Python-based web framework), `streamlit-extras`
- **Visualization**: [Plotly](https://plotly.com/) (Interactive charts), HTML/CSS (Custom styling)
- **Machine Learning**: [XGBoost](https://xgboost.readthedocs.io/), [Scikit-Learn](https://scikit-learn.org/)
- **Data Processing**: [Pandas](https://pandas.pydata.org/), [SQLAlchemy](https://www.sqlalchemy.org/)
- **Database**: [PostgreSQL](https://www.postgresql.org/) (Supabase Cloud supported)
- **Data Sources**: 
    - **RapidAPI (API-Football)**: Primary match data.
    - **Football-Data.org**: Reliable fallback for match data.
    - **Understat**: Advanced xG and tactical data (Scraping).
    - **The Odds API**: Live betting odds.
- **Automation**: `schedule`, `tenacity` for robust ETL pipelines.

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.9+
- PostgreSQL installed (Local) or Supabase Account (Cloud)

### 1. Clone the Repository
```bash
git clone https://github.com/ajibolagenius/football-predictive-model.git
cd football-predictive-model
```

### 2. Set Up Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configuration
Create a `.env` file in the root directory (use `env.example` as a template):
```env
# Database (Local or Supabase)
DB_CONNECTION=postgresql://postgres@localhost:5432/football_prediction_db

# API Keys
ODDS_API_KEY=your_odds_api_key
RAPIDAPI_KEY=your_rapidapi_key
FOOTBALL_DATA_ORG_KEY=your_football_data_org_key
```

### 5. Database Setup
Initialize the database (applies all schemas automatically):
```bash
python3 scripts/init_db.py
```

### 6. Data Pipeline (ETL)
Populate the database with match, tactical, and player data:
```bash
# 1. Fetch Matches (API + Fallbacks) & Scrape Tactical Data
python3 scripts/etl_pipeline.py

# 2. Scrape Player Data
python3 scripts/scraper_players.py
```

---

## 🖥️ Usage

### Run the Dashboard
```bash
streamlit run dashboard.py
```
The app will open in your browser at `http://localhost:8501`.

### Automated Scheduler
To keep data fresh, run the scheduler in the background:
```bash
python3 scripts/scheduler.py
```
This will run the scrapers daily at 02:00 AM.

---

## ☁️ Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions on deploying to **Render**, **Heroku**, or **Google Cloud Run**.

---

## 📂 Project Structure

```
├── dashboard.py           # Main Streamlit application
├── config.py              # Configuration loader
├── utils.py               # Shared utilities (logging, requests)
├── scripts/               # ETL and Scraper scripts
│   ├── etl_pipeline.py    # Main ETL (API + Fallbacks)
│   ├── scraper_players.py # Scrapes player stats
│   ├── scheduler.py       # Automated job scheduler
│   └── init_db.py         # Database initialization utility
├── sql/                   # Database schemas (v1 to v5)
├── src/                   # (Optional) Core logic modules
├── requirements.txt       # Python dependencies
└── README.md              # Project documentation
```

---

## 🔮 Future Improvements

-   **Advanced Metrics**: Expected Threat (xT), Passing Networks.
-   **User Accounts**: Save betting history and preferences.
-   **Backtesting Framework**: Automated validation of betting strategies.

---

*(c) 2025 DON_GENIUS*