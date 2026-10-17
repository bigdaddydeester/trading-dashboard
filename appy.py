import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(page_title="Two‑Zone Trading Dashboard", layout="wide")

st.title("📈 Two‑Zone Strategy Performance Dashboard")

uploaded_files = st.file_uploader(
    "Upload one or more CSV files", type=["csv"], accept_multiple_files=True
)

if not uploaded_files:
    st.info("Upload CSV files to generate your dashboard.")
    st.stop()

# --- LOAD & MERGE DATA ---
dfs = []
for f in uploaded_files:
    df = pd.read_csv(f)
    df["source_file"] = f.name
    dfs.append(df)

df = pd.concat(dfs, ignore_index=True)

# --- BASIC CLEANUP ---
# Expect columns: date, pnl, duration, zone, market_condition, mistake
# Adjust names if needed
if "pnl" not in df.columns:
    st.error("CSV must contain a 'pnl' column.")
    st.stop()

# Clean PnL
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
    st.warning("No 'date' column found; calendar view will be limited.")

# Duration to seconds
def parse_duration(x):
    x = str(x)
    if "min" in x:
        parts = x.split()
        mins = int(parts[0].replace("min", ""))
        secs = int(parts[1].replace("sec", ""))
        return mins * 60 + secs
    else:
        return int(x.replace("sec", ""))

if "duration" in df.columns:
    df["hold_seconds"] = df["duration"].apply(parse_duration)
else:
    df["hold_seconds"] = np.nan

# --- FILTERS ---
st.sidebar.header("Filters")

zones = df["zone"].unique().tolist() if "zone" in df.columns else []
selected_zones = st.sidebar.multiselect("Zones", zones, default=zones)

markets = df["market_condition"].unique().tolist() if "market_condition" in df.columns else []
selected_markets = st.sidebar.multiselect("Market Conditions", markets, default=markets)

mistakes = df["mistake"].unique().tolist() if "mistake" in df.columns else []
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

# --- METRICS ---
wins = filtered[filtered["pnl_clean"] > 0]
losses = filtered[filtered["pnl_clean"] < 0]

biggest_win = filtered["pnl_clean"].max()
biggest_loss = filtered["pnl_clean"].min()
win_rate = len(wins) / len(filtered) if len(filtered) else 0
avg_win = wins["pnl_clean"].mean() if len(wins) else 0
avg_loss = losses["pnl_clean"].mean() if len(losses) else 0
expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
avg_hold = filtered["hold_seconds"].mean() if filtered["hold_seconds"].notna().any() else np.nan

# Streaks
streaks = []
current = 0
for pnl in filtered["pnl_clean"]:
    if pnl > 0:
        current += 1
    else:
        current = 0
    streaks.append(current)
longest_win_streak = max(streaks) if streaks else 0

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Biggest Win", f"${biggest_win:,.2f}")
    st.metric("Win Rate", f"{win_rate*100:.1f}%")
with col2:
    st.metric("Biggest Loss", f"${biggest_loss:,.2f}")
    st.metric("Expectancy", f"${expectancy:,.2f}")
with col3:
    if not np.isnan(avg_hold):
        st.metric("Avg Hold Time (sec)", f"{avg_hold:.1f}")
    else:
        st.metric("Avg Hold Time (sec)", "N/A")
    st.metric("Longest Win Streak", longest_win_streak)

# --- ZONE‑BASED COLOR CODING ---
st.subheader("Zone‑Based PnL (Color‑coded)")

if "zone" in filtered.columns:
    zone_chart = (
        alt.Chart(filtered)
        .mark_bar()
        .encode(
            x="zone:N",
            y="sum(pnl_clean):Q",
            color=alt.Color("zone:N", scale=alt.Scale(scheme="tableau10")),
            tooltip=["zone", "sum(pnl_clean)"]
        )
        .properties(height=300)
    )
    st.altair_chart(zone_chart, use_container_width=True)
else:
    st.info("Add a 'zone' column to your CSV for zone‑based performance.")

# --- MISTAKE TAGGING VIEW ---
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
else:
    st.info("Add a 'mistake' column (e.g., 'early entry', 'late exit') to analyze execution errors.")

# --- PNL OVER TIME ---
st.subheader("PnL Over Time")

if "date" in filtered.columns:
    pnl_time = (
        alt.Chart(filtered)
        .mark_line(point=True)
        .encode(
            x="date:T",
            y="sum(pnl_clean):Q",
            color=alt.Color("zone:N", scale=alt.Scale(scheme="tableau10"), legend=None) if "zone" in filtered.columns else alt.value("#4CAF50"),
            tooltip=["date", "sum(pnl_clean)"]
        )
        .properties(height=300)
    )
    st.altair_chart(pnl_time, use_container_width=True)
else:
    st.info("Add a 'date' column to see PnL over time.")

# --- AUTO‑GENERATED INSIGHTS ---
st.subheader("Auto‑Generated Insights")

insights = []

if "zone" in filtered.columns:
    zone_perf = filtered.groupby("zone")["pnl_clean"].mean().sort_values()
    worst_zone = zone_perf.index[0]
    best_zone = zone_perf.index[-1]
    insights.append(f"Zone **{best_zone}** currently has the highest average PnL (${zone_perf[best_zone]:.2f}).")
    insights.append(f"Zone **{worst_zone}** underperforms with average PnL (${zone_perf[worst_zone]:.2f}). Consider refining rules there.")

if "market_condition" in filtered.columns:
    mc_perf = filtered.groupby("market_condition")["pnl_clean"].mean().sort_values()
    worst_mc = mc_perf.index[0]
    best_mc = mc_perf.index[-1]
    insights.append(f"Best market condition: **{best_mc}** (${mc_perf[best_mc]:.2f} avg PnL).")
    insights.append(f"Weakest market condition: **{worst_mc}** (${mc_perf[worst_mc]:.2f} avg PnL).")

if "mistake" in filtered.columns:
    most_common_mistake = filtered["mistake"].value_counts().idxmax()
    insights.append(f"Most frequent mistake: **{most_common_mistake}**. Reducing this could improve overall performance.")

if len(insights) == 0:
    st.write("Add 'zone', 'market_condition', and 'mistake' columns for richer insights.")
else:
    for i in insights:
        st.markdown(f"- {i}")

# --- PNL CALENDAR VIEW ---
st.subheader("P&L Calendar")

if "date" in filtered.columns:
    # Aggregate by date
    daily = filtered.groupby("date").agg(
        total_pnl=("pnl_clean", "sum"),
        trades=("pnl_clean", "count")
    ).reset_index()

    # Create calendar‑like table (month view)
    # Assume single month for simplicity
    month = daily["date"].dt.month.mode()[0]
    year = daily["date"].dt.year.mode()[0]

    month_dates = pd.date_range(start=f"{year}-{month}-01", end=f"{year}-{month}-28") + pd.offsets.MonthEnd(0)
    start = month_dates[0].replace(day=1)
    end = month_dates[0]
    all_days = pd.date_range(start=start, end=end, freq="D")
    cal = pd.DataFrame({"date": all_days})
    cal = cal.merge(daily, on="date", how="left")

    cal["day"] = cal["date"].dt.day
    cal["weekday"] = cal["date"].dt.weekday  # 0=Mon
    cal["week"] = ((cal["date"].dt.day - 1) // 7)

    # Pivot to calendar grid
    grid = cal.pivot(index="week", columns="weekday", values="total_pnl")

    # Style: green for positive, red for negative, dark for zero/NaN
    def color_pnl(val):
        if pd.isna(val):
            return "background-color: #222222; color: #888888"
        if val > 0:
            return "background-color: #1b5e20; color: #ffffff"
        if val < 0:
            return "background-color: #b71c1c; color: #ffffff"
        return "background-color: #424242; color: #ffffff"

    styled = grid.style.applymap(color_pnl).format("{:.2f}")
    st.write(f"Month: **{year}-{month:02d}**")
    st.dataframe(styled, height=250)
else:
    st.info("Add a 'date' column to enable the P&L calendar view.")

