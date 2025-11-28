import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import xgboost as xgb
from sqlalchemy import create_engine, text
import numpy as np
import odds_integration
import config
from streamlit_extras.metric_cards import style_metric_cards

# --- CONFIGURATION ---
st.set_page_config(page_title="The Culture AI (V4)", layout="centered", page_icon="🐼")

# --- CUSTOM CSS ---
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">', unsafe_allow_html=True)
load_css("styles.css")

DB_CONNECTION = config.DB_CONNECTION

# --- CACHED FUNCTIONS ---
@st.cache_resource
def get_db_engine():
    return create_engine(DB_CONNECTION)

@st.cache_data
def load_data(league="EPL"):
    """Loads all match data and calculates current stats."""
    engine = get_db_engine()
    
    # 1. Load History
    query = """
    SELECT 
        m.date, m.match_id, m.home_team_id, m.away_team_id,
        m.home_goals, m.away_goals,
        s.home_xg, s.away_xg,
        s.home_ppda, s.away_ppda,
        s.home_deep, s.away_deep,
        t_home.name as home_name, t_away.name as away_name
    FROM matches m
    JOIN match_stats s ON m.match_id = s.match_id
    JOIN teams t_home ON m.home_team_id = t_home.team_id
    JOIN teams t_away ON m.away_team_id = t_away.team_id
    WHERE m.league = :league
    ORDER BY m.date ASC;
    """
    df = pd.read_sql(text(query), engine, params={"league": league})
    
    # 2. Calculate Elo
    current_elo = {}
    elo_history = []
    K_FACTOR = 20
    
    for index, row in df.iterrows():
        h = row['home_name']
        a = row['away_name']
        date = row['date']
        
        h_rating = current_elo.get(h, 1500)
        a_rating = current_elo.get(a, 1500)
        
        # Outcome
        if row['home_goals'] > row['away_goals']: actual = 1.0
        elif row['home_goals'] == row['away_goals']: actual = 0.5
        else: actual = 0.0
        
        expected_h = 1 / (1 + 10 ** ((a_rating - h_rating) / 400))
        
        new_h = h_rating + K_FACTOR * (actual - expected_h)
        new_a = a_rating + K_FACTOR * ((1 - actual) - (1 - expected_h))
        
        current_elo[h] = new_h
        current_elo[a] = new_a
        
        elo_history.append({'date': date, 'team': h, 'elo': new_h})
        elo_history.append({'date': date, 'team': a, 'elo': new_a})

    # 3. Calculate Rolling Tactical Stats (Last 5)
    # We need to restructure to a long format (team, date, stats) to use rolling
    
    # Prepare Home Rows
    h_df = df[['date', 'home_name', 'home_xg', 'home_ppda', 'home_deep', 'home_goals']].rename(
        columns={'home_name': 'team', 'home_xg': 'xg', 'home_ppda': 'ppda', 'home_deep': 'deep', 'home_goals': 'goals'}
    )
    h_df['is_home'] = True
    
    # Prepare Away Rows
    a_df = df[['date', 'away_name', 'away_xg', 'away_ppda', 'away_deep', 'away_goals']].rename(
        columns={'away_name': 'team', 'away_xg': 'xg', 'away_ppda': 'ppda', 'away_deep': 'deep', 'away_goals': 'goals'}
    )
    a_df['is_home'] = False
    
    # Combine and Sort
    all_stats = pd.concat([h_df, a_df]).sort_values(['team', 'date'])
    
    # Fill NaNs with means before rolling (crucial for stability)
    for col in ['xg', 'ppda', 'deep']:
        all_stats[col] = all_stats[col].fillna(all_stats[col].mean())

    # Calculate Rolling 5
    stats_dict = {}
    for team in all_stats['team'].unique():
        team_data = all_stats[all_stats['team'] == team].copy()
        
        # Rolling averages
        team_data['roll_xg'] = team_data['xg'].rolling(5, min_periods=1).mean()
        team_data['roll_ppda'] = team_data['ppda'].rolling(5, min_periods=1).mean()
        team_data['roll_deep'] = team_data['deep'].rolling(5, min_periods=1).mean()
        team_data['roll_goals'] = team_data['goals'].rolling(5, min_periods=1).mean()
        
        # Get the LATEST stats (tail 1)
        if not team_data.empty:
            latest = team_data.iloc[-1]
            stats_dict[team] = {
                'xg_5': latest['roll_xg'],
                'ppda_5': latest['roll_ppda'],
                'deep_5': latest['roll_deep'],
                'goals_5': latest['roll_goals']
            }
        else:
            stats_dict[team] = {'xg_5': 0, 'ppda_5': 0, 'deep_5': 0, 'goals_5': 0}
        
    return df, current_elo, stats_dict, pd.DataFrame(elo_history)

@st.cache_resource
def load_model():
    model = xgb.XGBClassifier()
    try:
        model.load_model("football_v4.json")
    except:
        st.error("Could not load 'football_v4.json'. Make sure to run 'train_model_v4.py' first.")
        return None
    return model

def get_last_5_matches(team_name, full_df):
    """Extracts the last 5 matches for a specific team."""
    team_matches = full_df[(full_df['home_name'] == team_name) | (full_df['away_name'] == team_name)].copy()
    team_matches = team_matches.sort_values('date', ascending=False).head(5)
    
    display_data = []
    for _, row in team_matches.iterrows():
        if row['home_name'] == team_name:
            opponent = row['away_name']
            location = "(H)"
            goals_for = row['home_goals']
            goals_against = row['away_goals']
            xg_for = row['home_xg']
            xg_against = row['away_xg']
        else:
            opponent = row['home_name']
            location = "(A)"
            goals_for = row['away_goals']
            goals_against = row['home_goals']
            xg_for = row['away_xg']
            xg_against = row['home_xg']
            
        if goals_for > goals_against: result = "W"
        elif goals_for == goals_against: result = "D"
        else: result = "L"
        
        display_data.append({
            "Date": row['date'],
            "Opponent": f"{opponent} {location}",
            "Result": f"{result} {goals_for}-{goals_against}",
            "xG": f"{xg_for:.2f} - {xg_against:.2f}"
        })
    
    return pd.DataFrame(display_data)

def get_h2h_matches(team1, team2, full_df):
    """Extracts head-to-head matches."""
    h2h = full_df[
        ((full_df['home_name'] == team1) & (full_df['away_name'] == team2)) |
        ((full_df['home_name'] == team2) & (full_df['away_name'] == team1))
    ].copy()
    
    h2h = h2h.sort_values('date', ascending=False)
    
    display_data = []
    for _, row in h2h.iterrows():
        if row['home_name'] == team1:
            home = team1
            away = team2
            score = f"{row['home_goals']} - {row['away_goals']}"
        else:
            home = team2
            away = team1
            score = f"{row['home_goals']} - {row['away_goals']}"
            
        display_data.append({
            "Date": row['date'],
            "Home": home,
            "Score": score,
            "Away": away,
            "xG": f"{row['home_xg']:.2f} - {row['away_xg']:.2f}"
        })
        
    return pd.DataFrame(display_data)

def get_league_table(full_df):
    """Calculates the league table for the CURRENT SEASON."""
    # Ensure date is datetime
    full_df = full_df.copy()
    full_df['date'] = pd.to_datetime(full_df['date'])
    
    # Determine Current Season Start
    if full_df.empty: return pd.DataFrame()
    
    max_date = full_df['date'].max()
    # If we are in the second half of the year (Aug+), season started this year.
    # If we are in the first half (Jan-May), season started last year.
    # Using July 1st as a safe cutoff.
    if max_date.month >= 7: 
        season_start = pd.Timestamp(year=max_date.year, month=7, day=1)
    else:
        season_start = pd.Timestamp(year=max_date.year - 1, month=7, day=1)
        
    # Filter for current season
    season_df = full_df[full_df['date'] >= season_start]
    
    table = {}
    
    for _, row in season_df.iterrows():
        home = row['home_name']
        away = row['away_name']
        h_goals = row['home_goals']
        a_goals = row['away_goals']
        
        if home not in table: table[home] = {'P': 0, 'W': 0, 'D': 0, 'L': 0, 'GF': 0, 'GA': 0, 'Pts': 0}
        if away not in table: table[away] = {'P': 0, 'W': 0, 'D': 0, 'L': 0, 'GF': 0, 'GA': 0, 'Pts': 0}
        
        # Update Home
        table[home]['P'] += 1
        table[home]['GF'] += h_goals
        table[home]['GA'] += a_goals
        
        # Update Away
        table[away]['P'] += 1
        table[away]['GF'] += a_goals
        table[away]['GA'] += h_goals
        
        # Result
        if h_goals > a_goals:
            table[home]['W'] += 1
            table[home]['Pts'] += 3
            table[away]['L'] += 1
        elif h_goals == a_goals:
            table[home]['D'] += 1
            table[home]['Pts'] += 1
            table[away]['D'] += 1
            table[away]['Pts'] += 1
        else:
            table[away]['W'] += 1
            table[away]['Pts'] += 3
            table[home]['L'] += 1
            
    # Convert to DataFrame
    if not table: return pd.DataFrame()
    
    df_table = pd.DataFrame.from_dict(table, orient='index')
    df_table['GD'] = df_table['GF'] - df_table['GA']
    
    # Sort
    df_table = df_table.sort_values(by=['Pts', 'GD', 'GF'], ascending=False)
    
    return df_table

def get_top_players(league="EPL", limit=10):
    """Fetches top scorers for the current season."""
    engine = get_db_engine()
    try:
        query = """
        SELECT p.name as "Player", t.name as "Team", s.goals as "Goals", s.assists as "Assists", 
               s.xg as "xG", s.xa as "xA", s.xg_chain as "xGChain", s.xg_buildup as "xGBuildup"
        FROM player_season_stats s
        JOIN players p ON s.player_id = p.player_id
        JOIN teams t ON p.team_id = t.team_id
        WHERE s.season = '2025' AND t.league = :league
        ORDER BY s.goals DESC
        LIMIT :limit
        """
        return pd.read_sql(text(query), engine, params={"limit": limit, "league": league})
    except Exception as e:
        st.error(f"DB Error: {e}")
        return pd.DataFrame()

# --- MAIN UI ---
st.title("🏟️ The Culture AI (V4)")

# Sidebar for API Key
with st.sidebar:
    st.header("⚙️ Settings")
    
    # League Selector
    selected_league = st.selectbox("Select League", ["EPL", "La_Liga", "Bundesliga"])
    
    # Use config key as default if available
    default_key = config.ODDS_API_KEY if config.ODDS_API_KEY else ""
    odds_api_key = st.text_input("Odds API Key", type="password", value=default_key, help="Get free key at the-odds-api.com")

# Load Data
df, elo_dict, form_dict, elo_hist_df = load_data(selected_league)

if df.empty:
    st.warning(f"⚠️ No match data found for **{selected_league}**. Please run `python3 scripts/etl_pipeline.py` to fetch data.")
    st.stop()

model = load_model()

# Style Cards
style_metric_cards(border_left_color="#1E88E5", background_color="#1E1E1E", border_size_px=1, border_color="#333")

# --- CONTROL PANEL ---
st.markdown("### ⚙️ Match Configuration")

with st.container():
    c_team1, c_team2 = st.columns(2)
    
    teams = sorted(list(elo_dict.keys()))
    
    with c_team1:
        home_team = st.selectbox("Home Team", teams, index=0)
        home_rest = st.slider("Home Rest Days", 1, 14, 7, help="Days since last match")
    with c_team2:
        away_team = st.selectbox("Away Team", teams, index=1)
        away_rest = st.slider("Away Rest Days", 1, 14, 7, help="Days since last match")
        
    st.divider()
    
    c_bank, c_odds = st.columns([1, 2])
    with c_bank:
        bankroll = st.number_input("Bankroll (₦)", value=1000, step=100)
    with c_odds:
        st.caption("Bookie Odds (for Value Calculation)")
        
        # Live Odds Logic
        def_h, def_d, def_a = 2.00, 3.50, 3.80
        if odds_api_key:
            with st.spinner("Fetching live odds..."):
                odds_df = odds_integration.fetch_live_odds(odds_api_key)
                match_odds = odds_integration.map_teams(home_team, away_team, odds_df)
                if match_odds is not None:
                    def_h = match_odds['home_odd']
                    def_d = match_odds['draw_odd']
                    def_a = match_odds['away_odd']
                    st.success(f"✅ Live Odds: {match_odds['bookmaker']}")
                else:
                    st.warning("Match not found in live odds.")

        oc1, oc2, oc3 = st.columns(3)
        with oc1: odds_home = st.number_input("Home Odds", value=float(def_h), step=0.01)
        with oc2: odds_draw = st.number_input("Draw Odds", value=float(def_d), step=0.01)
        with oc3: odds_away = st.number_input("Away Odds", value=float(def_a), step=0.01)

st.divider()

# --- PREDICTION LOGIC ---
if home_team == away_team:
    st.error("Select two different teams!")
elif model is not None:
    h_elo = elo_dict[home_team]
    a_elo = elo_dict[away_team]
    h_stats = form_dict.get(home_team, {'xg_5': 1.0, 'ppda_5': 10.0, 'deep_5': 5.0})
    a_stats = form_dict.get(away_team, {'xg_5': 1.0, 'ppda_5': 10.0, 'deep_5': 5.0})
    
    # Input Vector (MUST MATCH train_model_v4.py)
    # features = ['elo_diff', 'home_rest', 'away_rest', 'home_ppda_5', 'away_ppda_5', 'home_deep_5', 'away_deep_5', 'home_xg_5', 'away_xg_5']
    
    input_data = pd.DataFrame([{
        'elo_diff': h_elo - a_elo,
        'home_rest': home_rest,
        'away_rest': away_rest,
        'home_ppda_5': h_stats['ppda_5'],
        'away_ppda_5': a_stats['ppda_5'],
        'home_deep_5': h_stats['deep_5'],
        'away_deep_5': a_stats['deep_5'],
        'home_xg_5': h_stats['xg_5'],
        'away_xg_5': a_stats['xg_5']
    }])
    
    # Predict
    probs = model.predict_proba(input_data)[0]
    prob_away = probs[0]
    prob_draw = probs[1]
    prob_home = probs[2]
    
    # --- VALUE CALCULATION ---
    ev_home = (prob_home * odds_home) - 1
    ev_draw = (prob_draw * odds_draw) - 1
    ev_away = (prob_away * odds_away) - 1
    
    best_ev = max(ev_home, ev_draw, ev_away)
    
    if best_ev > 0:
        if best_ev == ev_home:
            bet_target = "Home Win"
            bet_prob = prob_home
            bet_odds = odds_home
            rec_color = "#4ade80"
        elif best_ev == ev_draw:
            bet_target = "Draw"
            bet_prob = prob_draw
            bet_odds = odds_draw
            rec_color = "#facc15"
        else:
            bet_target = "Away Win"
            bet_prob = prob_away
            bet_odds = odds_away
            rec_color = "#f87171"
            
        # Kelly
        b = bet_odds - 1
        p = bet_prob
        q = 1 - p
        kelly_fraction = (b * p - q) / b if b > 0 else 0
        kelly_stake = max(0, bankroll * kelly_fraction * 0.5)
        
        value_msg = f"✅ VALUE FOUND: {bet_target}"
        rec_msg = f"Bet ₦{kelly_stake:.2f} (EV: {best_ev:.2f})"
        implied_odds = 1/bet_prob
    else:
        value_msg = "❌ NO VALUE FOUND"
        rec_msg = "Do Not Bet"
        rec_color = "#888888"
        implied_odds = 0
        bet_odds = 0

    # --- MAIN DISPLAY ---
    def glass_metric(label, value, delta=None, icon=None):
        delta_html = ""
        if delta is not None:
            color_class = "delta-pos" if delta >= 0 else "delta-neg"
            sign = "+" if delta > 0 else ""
            delta_html = f'<div class="metric-delta {color_class}">{sign}{delta}</div>'
        icon_html = f'<i class="{icon}"></i> ' if icon else ""
        return f"""
        <div class="glass-card metric-container">
            <div class="metric-label">{icon_html}{label}</div>
            <div class="metric-value">{value}</div>
            {delta_html}
        </div>
        """

    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col1:
        st.markdown(f"<h3 style='text-align: center;'>{home_team}</h3>", unsafe_allow_html=True)
        st.markdown(glass_metric("Elo Rating", int(h_elo), int(h_elo - 1500), "fas fa-shield-alt"), unsafe_allow_html=True)
        st.markdown(glass_metric("Avg xG (Last 5)", f"{h_stats['xg_5']:.2f}", None, "fas fa-bullseye"), unsafe_allow_html=True)
        
        st.markdown(f"""
            <div style="text-align: center; margin-top: 10px; color: #4ade80;">
                <div style="font-size: 0.8rem;">Win Prob</div>
                <div style="font-size: 1.5rem; font-weight: bold;">{prob_home:.1%}</div>
                <div style="font-size: 0.7rem; color: #888;">EV: {ev_home:.2f}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        st.markdown("<div class='vs-text'>VS</div>", unsafe_allow_html=True)
        
        st.markdown(f"""
            <div style="text-align: center; margin-bottom: 20px; color: #facc15;">
                <span style="font-size: 0.9rem;">Draw: <b>{prob_draw:.1%}</b> (EV: {ev_draw:.2f})</span>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="glass-card" style="border: 1px solid {rec_color}; box-shadow: 0 0 15px {rec_color}40;">
            <div class="metric-label"><i class="fas fa-coins"></i> AI Recommendation</div>
            <div style="font-size: 1.2rem; color: #ffffff; margin-top: 5px; font-weight: 600;">{value_msg}</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: {rec_color}; margin-top: 5px;">
                {rec_msg}
            </div>
            <div style="font-size: 0.8rem; color: #aaa; margin-top: 10px;">
                Model Odds: {implied_odds:.2f} | Bookie: {bet_odds:.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"<h3 style='text-align: center;'>{away_team}</h3>", unsafe_allow_html=True)
        st.markdown(glass_metric("Elo Rating", int(a_elo), int(a_elo - 1500), "fas fa-shield-alt"), unsafe_allow_html=True)
        st.markdown(glass_metric("Avg xG (Last 5)", f"{a_stats['xg_5']:.2f}", None, "fas fa-bullseye"), unsafe_allow_html=True)
        
        st.markdown(f"""
            <div style="text-align: center; margin-top: 10px; color: #f87171;">
                <div style="font-size: 0.8rem;">Win Prob</div>
                <div style="font-size: 1.5rem; font-weight: bold;">{prob_away:.1%}</div>
                <div style="font-size: 0.7rem; color: #888;">EV: {ev_away:.2f}</div>
            </div>
        """, unsafe_allow_html=True)

    st.divider()

    # --- TACTICAL COMPARISON (RADAR) ---
    st.subheader("🧠 Tactical Analysis (Last 5 Games)")
    
    # Normalize for Radar to ensuring all axes are visible
    # We scale everything to 0-100 based on "reasonable max" values for football
    
    categories = ['xG Created', 'Deep Completions', 'Pressing Intensity', 'Goals Scored']
    
    # Define Max Values for Normalization
    MAX_XG = 3.0
    MAX_DEEP = 20.0
    MAX_PPDA_SCORE = 30.0 # Since we invert PPDA (30-0), max score is 30
    MAX_GOALS = 4.0
    
    # Calculate Scores
    h_ppda_score = max(0, 30 - h_stats['ppda_5'])
    a_ppda_score = max(0, 30 - a_stats['ppda_5'])
    
    # Normalize (Value / Max * 100)
    h_norm = [
        min(100, (h_stats['xg_5'] / MAX_XG) * 100),
        min(100, (h_stats['deep_5'] / MAX_DEEP) * 100),
        min(100, (h_ppda_score / MAX_PPDA_SCORE) * 100),
        min(100, (h_stats['goals_5'] / MAX_GOALS) * 100)
    ]
    
    a_norm = [
        min(100, (a_stats['xg_5'] / MAX_XG) * 100),
        min(100, (a_stats['deep_5'] / MAX_DEEP) * 100),
        min(100, (a_ppda_score / MAX_PPDA_SCORE) * 100),
        min(100, (a_stats['goals_5'] / MAX_GOALS) * 100)
    ]
    
    # Raw values for hover text
    h_text = [f"{h_stats['xg_5']:.2f}", f"{h_stats['deep_5']:.1f}", f"{h_stats['ppda_5']:.1f} (PPDA)", f"{h_stats['goals_5']:.1f}"]
    a_text = [f"{a_stats['xg_5']:.2f}", f"{a_stats['deep_5']:.1f}", f"{a_stats['ppda_5']:.1f} (PPDA)", f"{a_stats['goals_5']:.1f}"]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=h_norm,
        theta=categories,
        fill='toself',
        name=home_team,
        line_color='#4ade80',
        text=h_text,
        hoverinfo="text+name"
    ))
    
    fig.add_trace(go.Scatterpolar(
        r=a_norm,
        theta=categories,
        fill='toself',
        name=away_team,
        line_color='#f87171',
        text=a_text,
        hoverinfo="text+name"
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False),
            bgcolor='rgba(255, 255, 255, 0.05)'
        ),
        height=500, # Increased size
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', size=14),
        showlegend=True,
        margin=dict(l=80, r=80, t=20, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.caption("Note: 'Pressing Intensity' is derived from PPDA (Passes Allowed Per Defensive Action). Higher is more intense pressing.")

    st.divider()

    # --- HISTORICAL DATA ---
    st.subheader("📅 Recent Match History")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**{home_team} Form**")
        st.dataframe(get_last_5_matches(home_team, df), use_container_width=True, hide_index=True)
    with c2:
        st.markdown(f"**{away_team} Form**")
        st.dataframe(get_last_5_matches(away_team, df), use_container_width=True, hide_index=True)
        
    st.subheader("⚔️ Head-to-Head")
    st.dataframe(get_h2h_matches(home_team, away_team, df), use_container_width=True, hide_index=True)

    st.divider()

    # --- LEAGUE & PLAYERS ---
    tab_league, tab_players = st.tabs(["🏆 League Standings", "🏃 Top Players"])
    
    with tab_league:
        st.dataframe(get_league_table(df), use_container_width=True)
        
    with tab_players:
        top_players = get_top_players(selected_league, 15)
        if not top_players.empty:
            st.dataframe(top_players, use_container_width=True)
        else:
            st.info("Player data not available. Please run 'scraper_players.py' and ensure schema is updated.")


    # --- FOOTER ---
    st.markdown('<div class="footer">(c) 2025 DON_GENIUS | V4 Model</div>', unsafe_allow_html=True)