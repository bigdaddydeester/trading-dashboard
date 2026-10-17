import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# -----------------------------
# DARK MODE THEME
# -----------------------------
st.set_page_config(page_title="Two‑Zone Trading Dashboard", layout="wide")

dark_css = """
<style>
body {
    background-color: #0e1117;
    color: #e0e0e0;
}
[data-testid="stHeader"] {
    background-color: #0e1117;
}
.block-container {
    padding-top: 2rem;
}
</style>
"""
st.markdown(dark_css, unsafe_allow_html=True)

st.title("📈 Two‑Zone Strategy Performance Dashboard (Dark Mode)")

# -----------------------------
# FILE UPLOAD
# -----------------------------
uploaded_files = st.file_uploader(
    "Upload one or more CSV files", type=["csv"], accept_multiple_files=True
)

if not uploaded_files:
    st.info("Upload CSV files to generate your dashboard.")
    st.stop()

# -----------------------------
# LOAD & MERGE DATA
# -----------------------------
dfs = []
for f in uploaded_files:
    df = pd.read_csv(f)
    df["source_file"] = f.name
    dfs.append(df)

df = pd.concat(dfs, ignore_index=True)

# -----------------------------
# CLEANUP
# -----------------------------
if "pnl" not in df.columns:
    st.error("CSV must contain a 'pnl' column.")
    st.stop()

df["pnl_clean"] = (
    df["pnl"]
    .astype(str)
    .str.replace("$", "")
    .str.replace("(", "-")
    .str.replace(")", "")
    .str.replace(",", "")
    .astype(float)
)

# Parse date
if "date" in df.columns:
    df["date"] = pd.to_datetime(df["date"])
else:
    st.warning("No 'date' column found; calendar view disabled.")

# Duration → seconds
def parse_duration(x):
    x = str(x)
    if "min" in x:
        parts = x.split()
        mins = int(parts[0].replace("min", ""))
        secs = int(parts[1].replace("sec", ""))
        return mins * 60 + secs
    return int(x.replace("sec", ""))

df["hold_seconds"] = df["duration"].apply(parse_duration) if "duration" in df.columns else np.nan

# -----------------------------
# FILTERS
# -----------------------------
st.sidebar.header("Filters")

zones = df["zone"].unique().tolist() if "zone" in df.columns else []
markets = df["market_condition"].unique().tolist() if "market_condition" in df.columns else []
mistakes = df["mistake"].unique().tolist() if "mistake" in df.columns else []

selected_zones = st.sidebar.multiselect("Zones", zones, default=zones)
selected_markets = st.sidebar.multiselect("Market Conditions", markets, default=markets)
selected_mistakes = st.sidebar.multiselect("Mistakes", mistakes, default=mistakes)

filtered = df.copy()
if selected_zones and "zone" in df.columns:
    filtered = filtered[filtered["zone"].isin(selected_zones)]
if selected_markets and "market_condition" in df.columns:
    filtered = filtered[filtered["market_condition"].isin(selected_markets)]
if selected_mistakes and "mistake" in df.columns:
    filtered = filtered[filtered["mistake"].isin(selected_mistakes)]

st.subheader("Filtered Trade Data")
st.dataframe(filtered)

if len(filtered) == 0:
    st.warning("No trades match current filters.")
    st.stop()

# -----------------------------
# METRICS
# -----------------------------
wins = filtered[filtered["pnl_clean"] > 0]
losses = filtered[filtered["pnl_clean"] < 0]

biggest_win = filtered["pnl_clean"].max()
biggest_loss = filtered["pnl_clean"].min()
win_rate = len(wins) / len(filtered)
avg_win = wins["pnl_clean"].mean() if len(wins) else 0
avg_loss = losses["pnl_clean"].mean() if len(losses) else 0
expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
avg_hold = filtered["hold_seconds"].mean()

# Win streak
streaks = []
current = 0
for pnl in filtered["pnl_clean"]:
    if pnl > 0:
        current += 1
    else:
        current = 0
    streaks.append(current)
longest_win_streak = max(streaks)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Biggest Win", f"${biggest_win:,.2f}")
    st.metric("Win Rate", f"{win_rate*100:.1f}%")
with col2:
    st.metric("Biggest Loss", f"${biggest_loss:,.2f}")
    st.metric("Expectancy", f"${expectancy:,.2f}")
with col3:
    st.metric("Avg Hold Time (sec)", f"{avg_hold:.1f}")
    st.metric("Longest Win Streak", longest_win_streak)

# -----------------------------
# ZONE PERFORMANCE
# -----------------------------
st.subheader("Zone‑Based PnL (Color‑coded)")

if "zone" in filtered.columns:
    zone_chart = (
        alt.Chart(filtered)
        .mark_bar()
        .encode(
            x="zone:N",
            y="sum(pnl_clean):Q",
            color=alt.Color("zone:N", scale=alt.Scale(scheme="dark2")),
            tooltip=["zone", "sum(pnl_clean)"]
        )
        .properties(height=300)
    )
    st.altair_chart(zone_chart, use_container_width=True)

# -----------------------------
# MISTAKE TAGGING
# -----------------------------
st.subheader("Mistake Tagging")

if "mistake" in filtered.columns:
    mistake_counts = filtered["mistake"].value_counts().reset_index()
    mistake_counts.columns = ["mistake", "count"]
    mistake_chart = (
        alt.Chart(mistake_counts)
        .mark_bar()
        .encode(
            x="mistake:N",
            y="count:Q",
            color=alt.Color("mistake:N", scale=alt.Scale(scheme="category20")),
            tooltip=["mistake", "count"]
        )
        .properties(height=300)
    )
    st.altair_chart(mistake_chart, use_container_width=True)

# -----------------------------
# PNL OVER TIME
# -----------------------------
st.subheader("PnL Over Time")

if "date" in filtered.columns:
    pnl_time = (
        alt.Chart(filtered)
        .mark_line(point=True)
        .encode(
            x="date:T",
            y="sum(pnl_clean):Q",
            color=alt.Color("zone:N", scale=alt.Scale(scheme="dark2")),
            tooltip=["date", "sum(pnl_clean)"]
        )
        .properties(height=300)
    )
    st.altair_chart(pnl_time, use_container_width=True)

# -----------------------------
# AUTO INSIGHTS
# -----------------------------
st.subheader("Auto‑Generated Insights")

insights = []

if "zone" in filtered.columns:
    zone_perf = filtered.groupby("zone")["pnl_clean"].mean().sort_values()
    insights.append(f"Best zone: **{zone_perf.idxmax()}** (${zone_perf.max():.2f}).")
    insights.append(f"Weakest zone: **{zone_perf.idxmin()}** (${zone_perf.min():.2f}).")

if "market_condition" in filtered.columns:
    mc_perf = filtered.groupby("market_condition")["pnl_clean"].mean().sort_values()
    insights.append(f"Strongest market condition: **{mc_perf.idxmax()}**.")
    insights.append(f"Weakest market condition: **{mc_perf.idxmin()}**.")

if "mistake" in filtered.columns:
    most_common_mistake = filtered["mistake"].value_counts().idxmax()
    insights.append(f"Most common mistake: **{most_common_mistake}**.")

for i in insights:
    st.markdown(f"- {i}")

# -----------------------------
# TRUE PNL CALENDAR (AUTO MONTHS)
# -----------------------------
st.subheader("📅 P&L Calendar")

if "date" in filtered.columns:
    daily = filtered.groupby("date").agg(
        total_pnl=("pnl_clean", "sum"),
        trades=("pnl_clean", "count")
    ).reset_index()

    # Build calendar for ALL months in dataset
    for (year, month), group in daily.groupby([daily.date.dt.year, daily.date.dt.month]):
        st.markdown(f"### {year}-{month:02d}")

        # Build full month grid
        start = pd.Timestamp(year=year, month=month, day=1)
        end = start + pd.offsets.MonthEnd(0)
        all_days = pd.date_range(start=start, end=end, freq="D")

        cal = pd.DataFrame({"date": all_days})
        cal = cal.merge(group, on="date", how="left")

        cal["weekday"] = cal["date"].dt.weekday
        cal["week"] = ((cal["date"].dt.day - 1) // 7)

        grid = cal.pivot(index="week", columns="weekday", values="total_pnl")

        def color_pnl(val):
            if pd.isna(val):
                return "background-color: #1a1a1a; color: #555;"
            if val > 0:
                return "background-color: #0f5132; color: #d1e7dd;"
            if val < 0:
                return "background-color: #842029; color: #f8d7da;"
            return "background-color: #2c2c2c; color: #ccc;"

        styled = grid.style.applymap(color_pnl).format("{:.2f}")
        st.dataframe(styled, height=250)
