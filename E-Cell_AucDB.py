import streamlit as st
import pandas as pd
import time
import sqlite3
from http.server import SimpleHTTPRequestHandler, HTTPServer
import threading

# Constants
INITIAL_TEAM_BUDGET = 10000  # 10000 lakhs = 100 Cr
ADMIN_PASSWORD = "admin123"  # Replace with your desired password

# Set up the Streamlit page (must be the first command)
st.set_page_config(layout="wide")  # Use the full width of the screen

# Hide Streamlit menu, footer, and prevent code inspection
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none !important;}
    </style>
    <script>
    document.addEventListener('contextmenu', event => event.preventDefault());
    document.onkeydown = function(e) {
        if (e.ctrlKey && (e.keyCode === 85 || e.keyCode === 83)) {
            return false;
        }
        if (e.keyCode == 123) {
            return false;
        }
    };
    </script>
    """, unsafe_allow_html=True)

# Custom CSS for better styling
st.markdown("""
    <style>
    body {font-family: 'Arial', sans-serif; background-color: #f5f5f5;}
    .stButton button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        font-size: 16px;
        transition: background-color 0.3s ease;
    }
    .stButton button:hover {background-color: #45a049;}
    .stMetric {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    .slider-container {
        width: 100%;
        overflow: hidden;
        white-space: nowrap;
        background-color: #4CAF50;
        color: white;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 20px;
        position: relative;
    }
    .slider-content {
        display: inline-block;
        padding-left: 50%;
        animation: slide 1800s linear infinite;
    }
    .slider-item {
        display: inline-block;
        margin-right: 50px;
        font-size: 18px;
        font-weight: bold;
    }
    @keyframes slide {
        0% { transform: translateX(0%); }
        100% { transform: translateX(-100%); }
    }
    .popup {
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: #4CAF50;
        color: white;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        z-index: 1000;
        animation: fadeInOut 3s ease-in-out;
    }
    @keyframes fadeInOut {
        0% { opacity: 0; }
        10% { opacity: 1; }
        90% { opacity: 1; }
        100% { opacity: 0; }
    }
    </style>
    """, unsafe_allow_html=True)

# Database setup
def init_db():
    conn = sqlite3.connect("auctiono.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            sold_amount INTEGER,
            rating INTEGER,
            team_bought TEXT,
            Role TEXT,
            nationality TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            team TEXT PRIMARY KEY,
            budget INTEGER,
            password TEXT  -- New column for team password
        )
    """)
    conn.commit()
    return conn

# Initialize database connection
conn = init_db()

# Helper functions
def load_players_from_db():
    return pd.read_sql("SELECT * FROM players", conn)

def load_teams_from_db():
    return pd.read_sql("SELECT * FROM teams", conn)

def save_players_to_db(players_df):
    players_df.to_sql("players", conn, if_exists="replace", index=False)

def save_teams_to_db(teams_df):
    teams_df.to_sql("teams", conn, if_exists="replace", index=False)

def calculate_team_budgets(players_df):
    team_budgets = {}
    teams = load_teams_from_db()  # Load teams with their budgets

    for _, row in teams.iterrows():
        team = row['team']
        budget = row['budget']  # Get the budget from the database
        team_players = players_df[players_df["team_bought"] == team]
        spent_amount = team_players["sold_amount"].sum()
        team_budgets[team] = budget - spent_amount  # Use the budget from the database
    
    return team_budgets

def generate_unique_id():
    players = load_players_from_db()
    return 1 if players.empty else players["id"].max() + 1

def calculate_team_rating(team):
    players = load_players_from_db()
    team_players = players[players["team_bought"] == team]
    return team_players["rating"].sum()

def generate_slider_content():
    players = load_players_from_db()
    sold_players = players[players["team_bought"] != "Unsold"]
    
    if sold_players.empty:
        return "No players have been bought yet."
    
    slider_items = []
    for _, player in sold_players.iterrows():
        nationality = "✈️" if player["nationality"] == "Foreign" else ""
        team_rating = calculate_team_rating(player["team_bought"])
        slider_items.append(
            f"{player['name']} {nationality} ({player['rating']}) | "
            f"{player['team_bought']} ({team_rating})"
        )
    
    return "   🏏   ".join(slider_items * 10)  # Repeat to fill the slider

def show_popup(message):
    popup = st.empty()
    popup.markdown(f'<div class="popup">{message}</div>', unsafe_allow_html=True)
    time.sleep(3)
    popup.empty()

def rank_to_exponent(rank):
    exponents = {1: "¹", 2: "²", 3: "³", 4: "⁴", 5: "⁵", 
                 6: "⁶", 7: "⁷", 8: "⁸", 9: "⁹", 10: "¹⁰"}
    return exponents.get(rank, str(rank))

def start_http_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    httpd.serve_forever()

# Initialize session state
if "players" not in st.session_state:
    st.session_state.players = load_players_from_db()

if "teams" not in st.session_state:
    st.session_state.teams = load_teams_from_db()

if "team_budgets" not in st.session_state:
    st.session_state.team_budgets = calculate_team_budgets(st.session_state.players)

# Initialize session state for password if not already set
if "team_password" not in st.session_state:
    st.session_state.team_password = ""

# Initialize session state for correct password if not already set
if "correct_password" not in st.session_state:
    st.session_state.correct_password = None

# Initialize session state for selected team if not already set
if "selected_team" not in st.session_state:
    st.session_state.selected_team = None

# Start HTTP server
if not hasattr(st.session_state, "http_server_started"):
    threading.Thread(target=start_http_server, daemon=True).start()
    st.session_state.http_server_started = True

# App title and description
st.title("Hindu's E-Cell Mock IPL Auction Dashboard")
st.write("Real-time auction management system with dynamic budget calculation")

# Password protection
password = st.sidebar.text_input("Enter Admin Password", type="password")
is_admin = password == ADMIN_PASSWORD

# Refresh Data button
if st.button("Refresh Data", key="refresh_data_2"):
    st.session_state.players = load_players_from_db()
    st.session_state.teams = load_teams_from_db()
    st.session_state.team_budgets = calculate_team_budgets(st.session_state.players)

# Section 0: Slider for Sold Players
slider_content = generate_slider_content()
st.markdown(
    f'<div class="slider-container"><div class="slider-content">{slider_content}</div></div>',
    unsafe_allow_html=True
)

# Section 1: Team Budgets
st.header("Team Budgets")

# Calculate team rankings
team_rankings = []
for team in st.session_state.team_budgets.keys():
    total_points = calculate_team_rating(team)
    team_rankings.append({"Team": team, "Total Points": total_points})

team_rankings = sorted(team_rankings, key=lambda x: x["Total Points"], reverse=True)

# Display team budgets
budget_cols = st.columns(5)
for i, team in enumerate(team_rankings):
    team_name = team["Team"]
    rank = i + 1
    budget = st.session_state.team_budgets[team_name]
    
    # Calculate Indian and Foreign players for the team
    squad = st.session_state.players[st.session_state.players["team_bought"] == team_name]
    total_indian = len(squad[squad['nationality'] == 'Indian'])
    total_foreign = len(squad[squad['nationality'] == 'Foreign'])
    
    # Calculate total rating for the team
    total_rating = calculate_team_rating(team_name)
    
    with budget_cols[i % 5]:
        # Create a formatted string for team name, player counts, and total rating
        team_info = f"**{team_name}{rank_to_exponent(rank)}** :  {total_rating}  |   {total_indian}/{total_foreign}"
        
        # Display budget with team info using st.metric
        st.metric(
            label=team_info,
            value=f"{budget / 100} Cr"
        )

# Admin Panel
if is_admin:
    with st.sidebar:
        st.header("Admin Panel")
        
        if st.button("Delete All Data"):
            conn.execute("DELETE FROM players")
            conn.execute("DELETE FROM teams")
            conn.commit()
            st.session_state.players = pd.DataFrame()
            st.session_state.teams = pd.DataFrame()
            st.session_state.team_budgets = {}
            st.success("All data has been deleted!")
            st.rerun()
        
        st.subheader("Add New Team")
        new_team = st.text_input("Team Name")
        team_budget = st.number_input("Team Budget (in lakhs)", min_value=0, value=100)
        team_password = st.text_input("Team Password")  # New input for team password
        
        if st.button("Add Team"):
            if new_team.strip() and team_password.strip():
                try:
                    # Insert team, budget, and password into the database
                    conn.execute("INSERT INTO teams (team, budget, password) VALUES (?, ?, ?)", (new_team, team_budget, team_password))
                    conn.commit()
                    st.session_state.teams = load_teams_from_db()
                    st.session_state.team_budgets = calculate_team_budgets(st.session_state.players)
                    st.success(f"Team '{new_team}' with budget '{team_budget}' lakhs and password set!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error(f"Team '{new_team}' already exists!")
            else:
                st.error("Team name and password cannot be empty")
        
        st.subheader("Player Management")
        with st.form("player_form"):
            name = st.text_input("Player Name")
            sold_amount = st.number_input("Sold Amount (in lakhs)", min_value=0, value=0)
            team_options = ["Unsold"] + list(st.session_state.team_budgets.keys())
            team_bought = st.selectbox("Team", options=team_options)
            rating = st.number_input("Rating (1-100)", min_value=1, max_value=100, value=50)
            role = st.selectbox("Role", ["Batter", "Bowler", "Allrounder", "Wicketkeeper"])
            nationality = st.selectbox("Nationality", ["Indian", "Foreign"])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                add_clicked = st.form_submit_button("Add Player")
            with col2:
                update_clicked = st.form_submit_button("Update Player")
            with col3:
                delete_clicked = st.form_submit_button("Delete Player")
            
            # Refresh data before any action
            st.session_state.players = load_players_from_db()  # Refresh data
            st.session_state.team_budgets = calculate_team_budgets(st.session_state.players)  # Refresh budgets

            if add_clicked:
                if name.strip():
                    new_id = generate_unique_id()
                    new_player = {
                        "id": new_id,
                        "name": name,
                        "sold_amount": sold_amount if team_bought != "Unsold" else 0,
                        "rating": rating,
                        "team_bought": team_bought,
                        "Role": role,
                        "nationality": nationality
                    }
                    new_df = pd.DataFrame([new_player])
                    st.session_state.players = pd.concat([st.session_state.players, new_df], ignore_index=True)
                    save_players_to_db(st.session_state.players)
                    st.session_state.team_budgets = calculate_team_budgets(st.session_state.players)
                    
                    if team_bought != "Unsold":
                        show_popup(f"{name} ({rating}) sold to {team_bought} for {sold_amount} lakhs")
                    st.success("Player added!")
                    st.rerun()  # Rerun the app to reflect changes
                else:
                    st.error("Player name cannot be empty")
            
            if update_clicked:
                if name.strip():
                    players = st.session_state.players
                    if name in players["name"].values:
                        idx = players.index[players["name"] == name].tolist()[0]
                        
                        # Get original values for budget adjustment
                        original_team = players.at[idx, "team_bought"]
                        original_amount = players.at[idx, "sold_amount"]
                        
                        # Update player
                        players.at[idx, "sold_amount"] = sold_amount if team_bought != "Unsold" else 0
                        players.at[idx, "rating"] = rating
                        players.at[idx, "team_bought"] = team_bought
                        players.at[idx, "Role"] = role
                        players.at[idx, "nationality"] = nationality
                        
                        save_players_to_db(players)
                        st.session_state.team_budgets = calculate_team_budgets(players)
                        st.success("Player updated!")
                        st.rerun()  # Rerun the app to reflect changes
                    else:
                        st.error("Player not found")
                else:
                    st.error("Player name cannot be empty")
            
            if delete_clicked:
                if name.strip():
                    players = st.session_state.players
                    if name in players["name"].values:
                        players = players[players["name"] != name]
                        st.session_state.players = players
                        save_players_to_db(players)
                        st.session_state.team_budgets = calculate_team_budgets(players)
                        st.success("Player deleted!")
                        st.rerun()  # Rerun the app to reflect changes
                    else:
                        st.error("Player not found")
                else:
                    st.error("Player name cannot be empty")

# Section 2: Players List
st.header("Players List")
if not st.session_state.players.empty:
    st.dataframe(st.session_state.players.sort_values("id", ascending=False))
else:
    st.write("No players added yet")

# Section 3: Team Squads
st.header("Team Squads")
selected_team = st.selectbox("Select Team", options=list(st.session_state.team_budgets.keys()))

# Store the selected team in session state
st.session_state.selected_team = selected_team

if selected_team:
    # Check if the user is an admin
    if is_admin:
        # Admin can see the squad without a password
        squad = st.session_state.players[st.session_state.players["team_bought"] == selected_team]
        if not squad.empty:
            st.dataframe(squad)
            
            total_spent = squad["sold_amount"].sum() / 100  # Convert to Cr
            remaining_budget = st.session_state.team_budgets[selected_team] / 100  # Convert to Cr
            total_rating = squad["rating"].sum()
            
            # Count Indian and Foreign players
            total_indian = len(squad[squad['nationality'] == 'Indian'])
            total_foreign = len(squad[squad['nationality'] == 'Foreign'])
            
            # Count player types
            total_players = len(squad)  # Total number of players bought
            batters = len(squad[squad['Role'] == 'Batter'])
            bowlers = len(squad[squad['Role'] == 'Bowler'])
            allrounders = len(squad[squad['Role'] == 'Allrounder'])
            wicketkeepers = len(squad[squad['Role'] == 'Wicketkeeper'])
            
            # Create a DataFrame for the summary excluding Total Spent and Remaining Budget
            summary_data = {
                "Description": [
                    "Total Rating",
                    "Player Counts",
                    "Batters",
                    "Bowlers",
                    "Allrounders",
                    "Wicketkeepers",
                    "Indian",
                    "Foreign"
                ],
                "Count": [
                    total_rating,
                    total_players,
                    batters,
                    bowlers,
                    allrounders,
                    wicketkeepers,
                    total_indian,
                    total_foreign
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            
            # Set multi-index for better layout
            summary_df = summary_df.set_index("Description").T
            
            # Display the summary DataFrame
            st.dataframe(summary_df, use_container_width=True)  # Use container width for better layout
            
            # Display remaining budget
            st.write(f"**Total Spent:** {total_spent} Cr")
            st.write(f"**Remaining Budget:** {remaining_budget} Cr")
        else:
            st.write(f"No players bought by {selected_team} yet")
    else:
        # Password input for team for non-admin users
        team_password = st.text_input("Enter Password for Team", type="password", value=st.session_state.team_password)

        # Store the password in session state
        st.session_state.team_password = team_password

        # Fetch the password from the database
        team_info = load_teams_from_db()
        team_row = team_info[team_info['team'] == selected_team]
        st.session_state.correct_password = team_row['password'].values[0] if not team_row.empty else None

        # Check if the entered password is correct
        if team_password == st.session_state.correct_password:
            squad = st.session_state.players[st.session_state.players["team_bought"] == selected_team]
            if not squad.empty:
                st.dataframe(squad)
                
                total_spent = squad["sold_amount"].sum() / 100  # Convert to Cr
                remaining_budget = st.session_state.team_budgets[selected_team] / 100  # Convert to Cr
                total_rating = squad["rating"].sum()
                
                # Count Indian and Foreign players
                total_indian = len(squad[squad['nationality'] == 'Indian'])
                total_foreign = len(squad[squad['nationality'] == 'Foreign'])
                
                # Count player types
                total_players = len(squad)  # Total number of players bought
                batters = len(squad[squad['Role'] == 'Batter'])
                bowlers = len(squad[squad['Role'] == 'Bowler'])
                allrounders = len(squad[squad['Role'] == 'Allrounder'])
                wicketkeepers = len(squad[squad['Role'] == 'Wicketkeeper'])
                
                # Create a DataFrame for the summary excluding Total Spent and Remaining Budget
                summary_data = {
                    "Description": [
                        "Total Rating",
                        "Player Counts",
                        "Batters",
                        "Bowlers",
                        "Allrounders",
                        "Wicketkeepers",
                        "Indian",
                        "Foreign"
                    ],
                    "Count": [
                        total_rating,
                        total_players,
                        batters,
                        bowlers,
                        allrounders,
                        wicketkeepers,
                        total_indian,
                        total_foreign
                    ]
                }
                
                summary_df = pd.DataFrame(summary_data)
                
                # Set multi-index for better layout
                summary_df = summary_df.set_index("Description").T
                
                # Display the summary DataFrame
                st.dataframe(summary_df, use_container_width=True)  # Use container width for better layout
                
                # Display remaining budget
                st.write(f"**Total Spent:** {total_spent} Cr")
                st.write(f"**Remaining Budget:** {remaining_budget} Cr")
            else:
                st.write(f"No players bought by {selected_team} yet")
        elif team_password:  # Only show error if the password field is not empty
            st.error("Incorrect password. Please try again.")

# Section 4: Rankings
st.header("Team Rankings")
if team_rankings:
    for i, team in enumerate(team_rankings):
        st.write(f"{i+1}. {team['Team']}: {team['Total Points']} points")
else:
    st.write("No teams have players yet")

# Section 5: Unsold Players
st.header("Unsold Players")
unsold = st.session_state.players[st.session_state.players["team_bought"] == "Unsold"]
if not unsold.empty:
    st.dataframe(unsold)
else:
    st.write("No unsold players")
