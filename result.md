# Codebase Analysis Result

## 1. Remaining Refactoring & Enhancements

All core refactoring, robustness, scheduling, multi-league, UI polish, and directory organization tasks are complete.

## 2. Additional Features to Add

- **Advanced Metrics:** Expected Threat (xT) - *Partially implemented via xGChain/xGBuildup*, Passing Networks.
- **Data Sources:** Add more data sources to the pipeline.

## 3. Next Recommended Task

**👉 Passing Networks (Requires New Data Source)**
- **Why:** Visualize team passing structure.
- **How:** Requires event-level data (passer, receiver, location). Hard to scrape from Understat. Might need a new source or manual event logging.

**👉 Automated Backtesting**
- **Why:** Validate model performance over time.
- **How:** Create a script to simulate betting on past seasons using the V5 model.

## 4. Codebase Analysis & Refactoring Opportunities

### 🔍 Observations
- **Dashboard Versioning:** `dashboard.py` still references "V4" in the title and footer, despite using Model V5.
- **Code Duplication:** Feature calculation logic (Elo, Rolling Stats) exists in both `dashboard.py` and `feature_engineering_v5.py`. This creates a risk of inconsistency.
- **Hardcoded Values:** Feature importance in the dashboard is hardcoded. It should ideally be loaded dynamically.
- **Deployment:** No `Dockerfile` or `Procfile` exists for easy deployment.

### 🛠 Recommended Refactors
1.  **Update Dashboard Strings:** Change "V4" to "V5" in UI.
2.  **Centralize Configuration:** Move model version and common constants to `config.py`.
3.  **Dynamic Feature Importance:** Save feature importance to a JSON file during training and load it in the dashboard.
4.  **Dockerization:** Add a `Dockerfile` for containerized deployment.
