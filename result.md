# Codebase Analysis Result

## 1. Files Needing Enhancements & Refactoring

### `dashboard.py` (High Priority)
- **Refactoring:**
  - **Model Upgrade:** Currently uses the older `football_model.json`. Needs to be updated to use `football_v4.json` which includes advanced tactical features (PPDA, Deep Completions, Rest Days).
  - **Feature Consistency:** The input vector construction in `dashboard.py` must match the feature set used in `train_model_v4.py`.
  - **Code Structure:** Move the large CSS block to a separate `styles.css` file or a dedicated Python module.
  - **Configuration:** Move database connection strings and API keys to a `.env` file or a `config.py` module to avoid hardcoding.
  - **Error Handling:** Add try-except blocks around database connections and model loading to handle failures gracefully.

### `etl_pipeline.py` & `scraper_pipeline.py`
- **Enhancements:**
  - **Robustness:** Add retry logic for network requests and better logging for scraping failures.
  - **Data Validation:** Implement checks to ensure scraped data is within expected ranges before saving to the database.

## 2. Additional Features to Add

- **Tactical Analysis Dashboard:** Visualize the new V4 features (PPDA, Deep Completions) in the UI. Show how teams compare tactically, not just by goals/xG.
- **Live Odds Integration:** Instead of manual input, integrate with a free/freemium Odds API to fetch real-time bookmaker odds.
- **League Standings Table:** Auto-generate a live league table from the match history in the database.
- **Player-Level Analytics:** If data permits, add a section for top scorers, assist leaders, and player xG performance.
- **Simulation Mode:** Allow users to tweak input parameters (e.g., "What if Home Team had 5 days rest instead of 2?") to see how it affects the prediction.

## 3. Redundant Files (Recommended for Deletion)

The following files appear to be older versions, one-off scripts, or experiments that are no longer the primary source of truth:

- `feature_engineering_v2.py`: Obsolete. Replaced by `v4`.
- `feature_engineering_v3.py`: Obsolete. Replaced by `v4`.
- `train_model_xgb.py`: Redundant. `train_model.py` and `train_model_v4.py` cover this.
- `upgrade_db_v4.py`: One-off migration script.
- `fix_database.py`: One-off utility script.
- `check_data.py`: One-off debugging script.
- `bulk_import.py`: One-off import script.
- `football_xgb.json`: Old model file.
- `football_v4.json`: Keep this ONLY if you plan to switch to it immediately. Otherwise, `football_model.json` is the one currently in use. (Recommendation: Switch to V4 and keep this, delete the old one).

**Note:** `feature_engineering.py` and `train_model.py` are currently *active* because `dashboard.py` relies on them. They should only be deleted **after** `dashboard.py` is refactored to use the V4 pipeline.
