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
