# ⚽ The Culture Football AI Oracle

**An AI-powered football analytics platform featuring a sleek Streamlit dashboard, advanced xG metrics, and machine learning models to forecast match outcomes and identify value bets.**

The **Culture Football AI Oracle** is an end-to-end data science project that scrapes football match data, engineers advanced features (Elo, Rolling xG), and uses Random Forest classifiers to predict game results. It visualizes these insights through a modern, glassmorphism-styled interface designed for strategic betting analysis.

---

## 🚀 Features

### 🏟️ Interactive Dashboard
- **Modern Glassmorphism UI**: A sleek, dark-themed interface with glass cards, neon accents, and responsive design.
- **Real-time Predictions**: Instant win probabilities for Home vs Away teams.
- **Kelly Criterion Calculator**: Built-in betting calculator that suggests optimal stake sizes based on model confidence and bookmaker odds.
- **Head-to-Head Analysis**: Historical matchup data between selected teams.

### 🧠 Machine Learning Core
- **Random Forest Classifier**: Trained on historical match data, Elo ratings, and recent form.
- **Feature Engineering**:
    - **Elo Ratings**: Dynamic rating system updating after every match.
    - **Rolling xG (Expected Goals)**: Tracks team performance trends over the last 5-10 games.
    - **Form Points**: Recent match results (W/D/L) converted to numerical form.
- **Model Explainability**: Visualizes feature importance to show *why* a prediction was made.

### 📊 Advanced Analytics
- **Rolling xG Trends**: Line charts visualizing offensive and defensive performance over time.
- **Finishing Efficiency**: Comparison of Actual Goals vs Expected Goals to identify clinical or wasteful teams.
- **Recent Form**: Detailed match history with xG and results.

---

## 🛠️ Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/) (Python-based web framework)
- **Visualization**: [Plotly](https://plotly.com/) (Interactive charts), HTML/CSS (Custom styling)
- **Machine Learning**: [Scikit-Learn](https://scikit-learn.org/) (Random Forest)
- **Data Processing**: [Pandas](https://pandas.pydata.org/), [SQLAlchemy](https://www.sqlalchemy.org/)
- **Database**: [PostgreSQL](https://www.postgresql.org/)
- **Data Sources**: API-Football (RapidAPI), Understat (Scraping)

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.8+
- PostgreSQL installed and running

### 1. Clone the Repository
```bash
git clone [https://github.com/yourusername/football-ai-oracle.git
cd football-ai-oracle
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

### 4. Database Setup
Create a PostgreSQL database and run the schema script:
```bash
createdb football_prediction_db
psql -d football_prediction_db -f schema.sql
```

### 5. Data Pipeline (ETL)
You need to populate the database with match data.
1.  Get an API Key from [API-Football (RapidAPI)](https://rapidapi.com/api-sports/api/api-football).
2.  Update `etl_pipeline.py` with your API Key.
3.  Run the pipeline:
```bash
python3 etl_pipeline.py
```

---

## 🖥️ Usage

Run the Streamlit dashboard locally:
```bash
streamlit run dashboard.py
```
The app will open in your browser at `http://localhost:8501`.

1.  **Select Teams**: Choose Home and Away teams from the sidebar.
2.  **View Prediction**: See the AI's win probability and recommended bet.
3.  **Analyze**: Check the charts for Elo history, xG trends, and Head-to-Head records.
4.  **Bet Smart**: Use the Kelly Calculator to manage your bankroll.

---

## 📂 Project Structure

```
├── dashboard.py           # Main Streamlit application
├── etl_pipeline.py        # Fetches data from API and loads to DB
├── scraper_pipeline.py    # Scrapes advanced stats (xG) from web
├── feature_engineering.py # Calculates Elo, Form, and Rolling stats
├── train_model.py         # Trains the Random Forest model
├── schema.sql             # Database schema definition
├── requirements.txt       # Python dependencies
└── README.md              # Project documentation
```

---

## 🔮 Future Improvements

-   **Live Data Integration**: Fetch live odds and scores during match days.
-   **Player-Level Analytics**: Incorporate player stats (injuries, top scorers) into the model.
-   **More Leagues**: Expand beyond the current dataset to include major European leagues.
-   **Cloud Deployment**: Deploy the app to Streamlit Cloud or AWS.

---

## 📜 License

This project is licensed under the MIT License.

---

*(c) 2025 DON_GENIUS*
