import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
st.set_page_config(layout="wide")

df = pd.concat([
    pd.read_json("StreamingHistory_music_0.json"),
    pd.read_json("StreamingHistory_music_1.json"),
], ignore_index=True)
df["endTime"] = pd.to_datetime(df["endTime"])
df["minutesPlayed"] = df["msPlayed"] / 60_000

df_filtered = df[df["msPlayed"] >= 30_000]

all_artists = df_filtered.groupby("artistName").size().sort_values(ascending=False).reset_index()
all_artists.columns = ["Artist", "Plays"]

top_artists = all_artists.head(10)
fomo_artists = all_artists.head(100).copy()

all_tracks = df_filtered.groupby(["artistName", "trackName"]).size().sort_values(ascending=False).reset_index()
all_tracks.columns = ["Artist", "Track", "Plays"]

top_tracks = all_tracks.head(10)
fomo_tracks = all_tracks.head(100).copy()

with open("SpotifyTop2024.json", encoding="utf-8") as f:
    raw_2024 = json.load(f)

with open("SpotifyTop2025.json", encoding="utf-8") as f:
    raw_2025 = json.load(f)

songs_2024 = pd.DataFrame(raw_2024["top_100_songs"])
songs_2025 = pd.DataFrame(raw_2025["top_100_songs"])
chart_tracks = pd.concat([songs_2024, songs_2025], ignore_index=True).drop_duplicates(subset=["title", "artist"])

artists_2024 = pd.DataFrame(raw_2024["top_100_artists"])
artists_2025 = pd.DataFrame(raw_2025["top_100_artists"])
chart_artists = pd.concat([artists_2024, artists_2025], ignore_index=True).drop_duplicates(subset=["artist"])

chart_artist_ranks = dict(zip(chart_artists["artist"].str.lower().str.strip(), chart_artists["rank"])) 
def score_artist(row):
    name = row["Artist"].lower().strip()
    if name in chart_artist_ranks:
        return (101 - chart_artist_ranks[name]) / 100 
    else:
        return -((101 - row["user_rank"]) / 100) * 0.75
    
fomo_artists["user_rank"] = range(1, len(fomo_artists) + 1)
fomo_artists["score"] = fomo_artists.apply(score_artist, axis=1)

chart_track_ranks = dict(zip(zip(chart_tracks["artist"].str.lower().str.strip(), chart_tracks["title"].str.lower().str.strip()), chart_tracks["rank"]))
def score_track(row):
    key = (row["Artist"].lower().strip(), row["Track"].lower().strip())
    if key in chart_track_ranks:
        return (101 - chart_track_ranks[key]) / 100 
    else:
        return -((101 - row["user_rank"]) / 100) * 0.75
     
fomo_tracks["user_rank"] = range(1, len(fomo_tracks) + 1)
fomo_tracks["score"] = fomo_tracks.apply(score_track, axis=1)

artist_fomo = fomo_artists["score"].sum()
track_fomo = fomo_tracks["score"].sum()

fomo_score = (artist_fomo * 0.5) + (track_fomo * 0.5)

max_possible = sum((101 - i) / 100 for i in range(1, 101))
min_possible = -max_possible

fomo_score_normalized = ((fomo_score - min_possible) / (max_possible - min_possible)) * 100

#Create the Streamlit dashboard
st.title("Spotify Listening Dashboard")

#Display the FOMO Score as a gauge
fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=round(fomo_score_normalized, 1),
    title={"text": "FOMO Score", "font": {"size": 50}},
    number={"suffix": " / 100"},
    gauge={
        "axis": {"range": [0, 100], "tickvals": [0, 25, 50, 75, 100]},
        "bar": {"color": "royalblue"},
        "steps": [
            {"range": [0, 25], "color": "lightgreen"},
            {"range": [25, 50], "color": "yellow"},
            {"range": [50, 75], "color": "orange"},
            {"range": [75, 100], "color": "tomato"},
        ]
    }
))

st.plotly_chart(fig_gauge)

st.markdown("""
**Fear Of Missing Out (FOMO) Score Key:**
- 🟢  **0-25** — Very independent taste, rarely follows global trends
- 🟡  **25-50** — Mostly niche but with some mainstream influence
- 🟠  **50-75** — Mixed, follows trends somewhat
- 🔴 **75-100** — High FOMO, closely aligned with global trends
""")
st.markdown("<small>Disclaimer: This score is not meant to be a definitive measure of music taste or social influence</small>", unsafe_allow_html=True)

# Top 10 Artists graph
fig_artists = px.bar(top_artists, x="Plays", y="Artist", orientation="h",       
    title="Your Top 10 Artists", template="plotly_white",
    color="Artist", color_discrete_sequence=["turquoise"])
fig_artists.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)


# Top 10 Tracks graph
fig_tracks = px.bar(top_tracks, x="Plays", y="Track", orientation="h",
    title="Your Top 10 Tracks", template="plotly_white",
    color="Artist", color_discrete_sequence=["coral"])
fig_tracks.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig_artists)
with col2:
    st.plotly_chart(fig_tracks)

# Global Top 10 tables
col1, col2 = st.columns(2)
with col1:
    st.subheader("Global Top 10 Artists (2024-2025)")
    st.dataframe(
        chart_artists[["rank", "artist"]].head(10).rename(columns={"rank": "Rank", "artist": "Artist"}),
        hide_index=True)

with col2:
    st.subheader("Global Top 10 Tracks (2024-2025)")
    st.dataframe(
        chart_tracks[["rank", "title", "artist"]].head(10).rename(columns={"rank": "Rank", "title": "Track", "artist": "Artist"}),
        hide_index=True)

# Matched Artists table
matched_artists = fomo_artists[fomo_artists["score"] > 0][["Artist", "Plays"]]
st.subheader("Your Artists That Match Global Trends")
if len(matched_artists) > 0:
    st.dataframe(matched_artists, hide_index=True)
else:
    st.write("No matches found — truly independent taste!")

# Matched Tracks table
matched_tracks = fomo_tracks[fomo_tracks["score"] > 0][["Artist", "Track", "Plays"]]
st.subheader("Your Tracks That Match Global Trends")
if len(matched_tracks) > 0:
    st.dataframe(matched_tracks, hide_index=True)
else:
    st.write("No matches found — truly independent taste!")



