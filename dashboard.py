import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import xgboost as xgb
from sqlalchemy import create_engine
# from sklearn.ensemble import RandomForestClassifier # No longer needed

# --- CONFIGURATION ---
st.set_page_config(page_title="Football AI Oracle", layout="wide", page_icon="⚽")

# --- CUSTOM CSS ---
st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
        
        /* Global Settings */
        html, body, .stApp, [data-testid="stAppViewContainer"] {
            font-family: 'Poppins', sans-serif !important;
            background-color: #000000 !important;
            color: #ffffff !important;
        }
        
        /* Glassmorphism Card */
        .glass-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
        }

        /* Headers */
        h1, h2, h3 {
            font-family: 'Poppins', sans-serif !important;
            color: #ffffff !important;
        }

        h1 { font-weight: 600 !important; font-size: 2.5rem !important; }
        h2 { font-weight: 400 !important; font-size: 1.8rem !important; opacity: 0.9; }
        h3 { font-weight: 300 !important; font-size: 1.4rem !important; opacity: 0.8; }

        /* Metrics in Glass */
        .metric-container {
            text-align: center;
        }
        .metric-label {
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.6);
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: #ffffff;
            margin: 5px 0;
        }
        .metric-delta {
            font-size: 0.9rem;
            font-weight: 500;
        }
        .delta-pos { color: #4ade80; }
        .delta-neg { color: #f87171; }
        
        /* Custom Button Styling (Streamlit buttons are hard to style, but we try) */
        div.stButton > button {
            background: rgba(255, 255, 255, 0.1) !important;
            color: white !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 8px !important;
            backdrop-filter: blur(5px);
        }
        div.stButton > button:hover {
            background: rgba(255, 255, 255, 0.2) !important;
            border-color: rgba(255, 255, 255, 0.4) !important;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #000000 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        /* Footer */
        .footer {
            position: fixed;
            left: 0;
            bottom: 0;
            width: 100%;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(5px);
            color: rgba(255, 255, 255, 0.7);
            text-align: center;
            padding: 15px;
            font-size: 0.8rem;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            z-index: 100;
        }

        /* VS Text */
        .vs-text {
            font-size: 3rem;
            font-weight: 900;
            background: -webkit-linear-gradient(45deg, #ffffff, #888888);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            line-height: 1;
            margin-bottom: 10px;
            opacity: 0.8;
        }
    </style>
""", unsafe_allow_html=True)

DB_CONNECTION = "postgresql://postgres@localhost:5432/football_prediction_db"

# --- CACHED FUNCTIONS ---
@st.cache_resource
def get_db_engine():
    return create_engine(DB_CONNECTION)

@st.cache_data
def load_data():
    """Loads all match data and calculates current stats."""
    engine = get_db_engine()
    
    # 1. Load History
    query = """
    SELECT 
        m.date, m.home_team_id, m.away_team_id,
        m.home_goals, m.away_goals,
        s.home_xg, s.away_xg,
        t_home.name as home_name, t_away.name as away_name
    FROM matches m
    JOIN match_stats s ON m.match_id = s.match_id
    JOIN teams t_home ON m.home_team_id = t_home.team_id
    JOIN teams t_away ON m.away_team_id = t_away.team_id
    ORDER BY m.date ASC;
    """
    df = pd.read_sql(query, engine)
    
    # 2. Calculate Elo & Form
    current_elo = {}
    elo_history = []
    
    # Form dictionaries
    K_FACTOR = 20
    
    for index, row in df.iterrows():
        h = row['home_name']
        a = row['away_name']
        date = row['date']
        
        h_rating = current_elo.get(h, 1500)
        a_rating = current_elo.get(a, 1500)
        
        # Determine Outcome
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

    # Calculate Last 5 Stats (Aggregates)
    # We reconstruct a simple DF for this
    # Determine points for each row
    df['home_points'] = df.apply(lambda x: 3 if x['home_goals'] > x['away_goals'] else (1 if x['home_goals'] == x['away_goals'] else 0), axis=1)
    df['away_points'] = df.apply(lambda x: 3 if x['away_goals'] > x['home_goals'] else (1 if x['home_goals'] == x['away_goals'] else 0), axis=1)

    form_df = pd.concat([
        df[['date', 'home_name', 'home_goals', 'home_xg', 'home_points']].rename(columns={'home_name':'team', 'home_goals':'goals', 'home_xg':'xg', 'home_points':'points'}),
        df[['date', 'away_name', 'away_goals', 'away_xg', 'away_points']].rename(columns={'away_name':'team', 'away_goals':'goals', 'away_xg':'xg', 'away_points':'points'})
    ]).sort_values('date')
    
    stats_dict = {}
    for team in form_df['team'].unique():
        last_5 = form_df[form_df['team'] == team].tail(5)
        stats_dict[team] = {
            'goals': last_5['goals'].mean(),
            'xg': last_5['xg'].mean(),
            'points': last_5['points'].mean()
        }
        
    return df, current_elo, stats_dict, pd.DataFrame(elo_history)

@st.cache_resource
def load_model():
    model = xgb.XGBClassifier()
    model.load_model("football_model.json")
    return model

def get_last_5_matches(team_name, full_df):
    """
    Extracts the last 5 matches for a specific team to display in the UI.
    """
    # Filter where team is either home or away
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
            
        # Determine Result string
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
    """
    Extracts head-to-head matches between two teams.
    """
    # Filter for matches between the two teams
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

def get_team_rolling_stats(team_name, full_df, window=10):
    """
    Calculates rolling xG and Goals for a specific team.
    """
    # Filter matches involving the team
    team_matches = full_df[(full_df['home_name'] == team_name) | (full_df['away_name'] == team_name)].copy()
    team_matches = team_matches.sort_values('date', ascending=True) # Sort by date ascending for rolling calc
    
    stats_data = []
    for _, row in team_matches.iterrows():
        if row['home_name'] == team_name:
            xg_for = row['home_xg']
            xg_against = row['away_xg']
            goals_for = row['home_goals']
            goals_against = row['away_goals']
        else:
            xg_for = row['away_xg']
            xg_against = row['home_xg']
            goals_for = row['away_goals']
            goals_against = row['home_goals']
            
        stats_data.append({
            'date': row['date'],
            'xg_for': xg_for,
            'xg_against': xg_against,
            'goals_for': goals_for,
            'goals_against': goals_against
        })
        
    df_stats = pd.DataFrame(stats_data)
    
    # Calculate Rolling Averages
    df_stats['rolling_xg_for'] = df_stats['xg_for'].rolling(window=5, min_periods=1).mean()
    df_stats['rolling_xg_against'] = df_stats['xg_against'].rolling(window=5, min_periods=1).mean()
    
    return df_stats.tail(window) # Return last N matches

# --- MAIN UI ---
st.title("⚽︎ The Culture Football AI Oracle 🏟️")

# Load Data
df, elo_dict, form_dict, elo_hist_df = load_data()
model = load_model()

# --- CONTROL PANEL ---
st.markdown("### ⚙️ Match Configuration & Betting")

# Create a nice layout for the controls
with st.container():
    c_team1, c_team2, c_bank = st.columns([1.5, 1.5, 1])
    
    teams = sorted(list(elo_dict.keys()))
    
    with c_team1:
        home_team = st.selectbox("Home Team", teams, index=0)
    with c_team2:
        away_team = st.selectbox("Away Team", teams, index=1)
    with c_bank:
        bankroll = st.number_input("Bankroll (₦)", value=1000, step=100)
        
    st.caption("Bookie Odds (for Value Calculation)")
    oc1, oc2, oc3 = st.columns(3)
    with oc1: odds_home = st.number_input("Home Odds", value=2.00, step=0.01)
    with oc2: odds_draw = st.number_input("Draw Odds", value=3.50, step=0.01)
    with oc3: odds_away = st.number_input("Away Odds", value=3.80, step=0.01)
    
st.divider()

# --- PREDICTION LOGIC ---
if home_team == away_team:
    st.error("Select two different teams!")
else:
    h_elo = elo_dict[home_team]
    a_elo = elo_dict[away_team]
    h_form = form_dict[home_team]
    a_form = form_dict[away_team]
    
    # Input Vector
    input_data = pd.DataFrame([{
        'elo_diff': h_elo - a_elo,
        'home_elo': h_elo,
        'away_elo': a_elo,
        'home_xg_last_5': h_form['xg'],
        'away_xg_last_5': a_form['xg'],
        'home_points_last_5': h_form['points'],
        'away_points_last_5': a_form['points']
    }])
    
    # Predict Probabilities (Multi-Class: 0=Away, 1=Draw, 2=Home)
    probs = model.predict_proba(input_data)[0]
    prob_away = probs[0]
    prob_draw = probs[1]
    prob_home = probs[2]
    
    # --- VALUE CALCULATION ---
    # EV = (Prob * Odds) - 1
    ev_home = (prob_home * odds_home) - 1
    ev_draw = (prob_draw * odds_draw) - 1
    ev_away = (prob_away * odds_away) - 1
    
    # Find Best Value
    best_ev = max(ev_home, ev_draw, ev_away)
    
    if best_ev > 0:
        if best_ev == ev_home:
            bet_target = "Home Win"
            bet_prob = prob_home
            bet_odds = odds_home
            rec_color = "#4ade80" # Green
        elif best_ev == ev_draw:
            bet_target = "Draw"
            bet_prob = prob_draw
            bet_odds = odds_draw
            rec_color = "#facc15" # Yellow/Orange
        else:
            bet_target = "Away Win"
            bet_prob = prob_away
            bet_odds = odds_away
            rec_color = "#f87171" # Red (using red for away usually, but here it means 'hot' value)
            
        # Kelly Calculation for the Best Bet
        b = bet_odds - 1
        p = bet_prob
        q = 1 - p
        kelly_fraction = (b * p - q) / b
        kelly_stake = max(0, bankroll * kelly_fraction * 0.5) # Using Half Kelly for safety
        
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
    # We use a custom layout with glass cards
    
    # Helper for glass metrics
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
        st.markdown(glass_metric("Avg xG (Last 5)", f"{h_form['xg']:.2f}", None, "fas fa-bullseye"), unsafe_allow_html=True)
        
        # Home Prob
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
        
        # Draw Prob (Center)
        st.markdown(f"""
            <div style="text-align: center; margin-bottom: 20px; color: #facc15;">
                <span style="font-size: 0.9rem;">Draw: <b>{prob_draw:.1%}</b> (EV: {ev_draw:.2f})</span>
            </div>
        """, unsafe_allow_html=True)
        
        # Value Strategy Box
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
        st.markdown(glass_metric("Avg xG (Last 5)", f"{a_form['xg']:.2f}", None, "fas fa-bullseye"), unsafe_allow_html=True)
        
        # Away Prob
        st.markdown(f"""
            <div style="text-align: center; margin-top: 10px; color: #f87171;">
                <div style="font-size: 0.8rem;">Win Prob</div>
                <div style="font-size: 1.5rem; font-weight: bold;">{prob_away:.1%}</div>
                <div style="font-size: 0.7rem; color: #888;">EV: {ev_away:.2f}</div>
            </div>
        """, unsafe_allow_html=True)



    st.divider()

    # --- HEAD TO HEAD ---
    st.subheader("⚔️ Head-to-Head History")
    df_h2h = get_h2h_matches(home_team, away_team, df)
    if not df_h2h.empty:
        st.dataframe(df_h2h, use_container_width=True, hide_index=True)
    else:
        st.info("No recent head-to-head matches found in the database.")

    st.divider()

    # --- ADVANCED STATS ---
    st.subheader("📊 Advanced Performance Metrics")
    
    tab1, tab2 = st.tabs(["Rolling xG Trends", "Finishing Efficiency"])
    
    # Calculate stats for both teams
    home_stats = get_team_rolling_stats(home_team, df, window=10)
    away_stats = get_team_rolling_stats(away_team, df, window=10)
    
    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**{home_team} - xG Trend (Last 10)**")
            fig_h = go.Figure()
            fig_h.add_trace(go.Scatter(x=home_stats['date'], y=home_stats['rolling_xg_for'], name='xG Created', line=dict(color='#4ade80', width=3)))
            fig_h.add_trace(go.Scatter(x=home_stats['date'], y=home_stats['rolling_xg_against'], name='xG Conceded', line=dict(color='#f87171', width=3)))
            fig_h.update_layout(
                height=300, margin=dict(l=10, r=10, t=30, b=10),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ffffff'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(showgrid=False, linecolor='rgba(255,255,255,0.1)'),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', linecolor='rgba(255,255,255,0.1)')
            )
            st.plotly_chart(fig_h, use_container_width=True)
            
        with c2:
            st.markdown(f"**{away_team} - xG Trend (Last 10)**")
            fig_a = go.Figure()
            fig_a.add_trace(go.Scatter(x=away_stats['date'], y=away_stats['rolling_xg_for'], name='xG Created', line=dict(color='#4ade80', width=3)))
            fig_a.add_trace(go.Scatter(x=away_stats['date'], y=away_stats['rolling_xg_against'], name='xG Conceded', line=dict(color='#f87171', width=3)))
            fig_a.update_layout(
                height=300, margin=dict(l=10, r=10, t=30, b=10),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ffffff'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(showgrid=False, linecolor='rgba(255,255,255,0.1)'),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', linecolor='rgba(255,255,255,0.1)')
            )
            st.plotly_chart(fig_a, use_container_width=True)

    with tab2:
        st.caption("Comparing Actual Goals Scored vs Expected Goals (xG). Positive difference means clinical finishing (or luck).")
        c1, c2 = st.columns(2)
        
        # Helper for efficiency chart
        def create_efficiency_chart(stats_df, team_name):
            total_goals = stats_df['goals_for'].sum()
            total_xg = stats_df['xg_for'].sum()
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=['Goals', 'xG'], y=[total_goals, total_xg], marker_color=['#ffffff', '#58a6ff']))
            fig.update_layout(
                title=f"{team_name} (Last 10 Games)",
                height=250, margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ffffff'),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
            )
            return fig

        with c1:
            st.plotly_chart(create_efficiency_chart(home_stats, home_team), use_container_width=True)
        with c2:
            st.plotly_chart(create_efficiency_chart(away_stats, away_team), use_container_width=True)

    st.divider()

    # --- RECENT FORM TABLES ---
    st.subheader("📅 Recent Match History (Last 5)")
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown(f"**{home_team} Form**")
        df_home_last_5 = get_last_5_matches(home_team, df)
        st.dataframe(df_home_last_5, use_container_width=True, hide_index=True)

    with c2:
        st.markdown(f"**{away_team} Form**")
        df_away_last_5 = get_last_5_matches(away_team, df)
        st.dataframe(df_away_last_5, use_container_width=True, hide_index=True)

    # --- CHARTS ---
    st.divider()
    st.subheader("📈 Elo History (5 Years)")
    chart_data = elo_hist_df[elo_hist_df['team'].isin([home_team, away_team])]
    
    fig = go.Figure()
    colors = ['#58a6ff', '#ff6b6b'] # Blue and Red/Pinkish to match theme
    for team, color in zip([home_team, away_team], colors):
        team_data = chart_data[chart_data['team'] == team]
        fig.add_trace(go.Scatter(x=team_data['date'], y=team_data['elo'], mode='lines', name=team, line=dict(color=color, width=3)))
    
    fig.update_layout(
        height=350, 
        margin=dict(l=20, r=20, t=20, b=20), 
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff'),
        xaxis=dict(showgrid=False, linecolor='rgba(255,255,255,0.1)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', linecolor='rgba(255,255,255,0.1)')
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- AI INSIGHTS (Feature Importance) ---
    st.divider()
    st.subheader("🧠 AI Model Insights")
    
    # Get feature importance
    importances = model.feature_importances_
    # Feature names matching the training columns
    feature_names = ['Elo Diff', 'Home Elo', 'Away Elo', 'Home xG (L5)', 'Away xG (L5)', 'Home Pts (L5)', 'Away Pts (L5)']
    
    # Create DataFrame for plotting
    fi_df = pd.DataFrame({'Feature': feature_names, 'Importance': importances})
    fi_df = fi_df.sort_values('Importance', ascending=True)
    
    fig_fi = go.Figure(go.Bar(
        x=fi_df['Importance'],
        y=fi_df['Feature'],
        orientation='h',
        marker=dict(color='#58a6ff')
    ))
    
    fig_fi.update_layout(
        title="What influenced this prediction?",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', linecolor='rgba(255,255,255,0.1)'),
        yaxis=dict(showgrid=False, linecolor='rgba(255,255,255,0.1)')
    )
    st.plotly_chart(fig_fi, use_container_width=True)

    # --- FOOTER ---
    st.markdown('<div class="footer">(c) 2025 DON_GENIUS</div>', unsafe_allow_html=True)