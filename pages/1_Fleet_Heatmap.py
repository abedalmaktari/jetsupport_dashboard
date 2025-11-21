# -*- coding: utf-8 -*-
# ==========================================================
# JetSupport Fleet Health Monitoring (Heatmap + Trendlines)
# ==========================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# -------------------- COLORS & THEME --------------------
JS_BLUE = "#00529B"
JS_RED = "#E43D30"

base_theme = st.get_option("theme.base") or "light"
plotly_template = "plotly_dark" if base_theme == "dark" else "plotly_white"
text_color = "#E5E7EB" if base_theme == "dark" else "#0B1F33"

# -------------------- HEADER --------------------
st.markdown(f"""
<h1 style='color:{text_color};'>📈 JetSupport Fleet Health Monitoring</h1>
<p style='color:{'#C9D1D9' if base_theme=='dark' else '#5A6B7A'};'>
View fleet-wide ΔSFC efficiency trends, identify abnormal degradation patterns, and compare aircraft performance.
</p>
""", unsafe_allow_html=True)

# -------------------- FILE UPLOAD --------------------
uploaded_file = st.sidebar.file_uploader("Upload Fleet QAR (.csv / .dat)", type=["csv", "dat"])

if not uploaded_file:
    st.info("Upload a fleet dataset containing columns at least: Aircraft_ID, Month, and either ΔSFC or (Fuel_Flow_Pre & Fuel_Flow_Post).")
    st.stop()

try:
    if uploaded_file.name.lower().endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file, delim_whitespace=True, engine="python")
except Exception as e:
    st.error(f"⚠️ Error reading file: {e}")
    st.stop()

# -------------------- VALIDATION --------------------
required = {"Aircraft_ID", "Month"}
if not required.issubset(df.columns):
    st.error("Dataset must include columns: Aircraft_ID and Month.")
    st.stop()

# Compute ΔSFC if needed
if "ΔSFC" not in df.columns and {"Fuel_Flow_Pre", "Fuel_Flow_Post"}.issubset(df.columns):
    df["ΔSFC"] = (df["Fuel_Flow_Pre"] - df["Fuel_Flow_Post"]) / df["Fuel_Flow_Pre"] * 100.0

if "ΔSFC" not in df.columns:
    st.error("Dataset must include ΔSFC or (Fuel_Flow_Pre & Fuel_Flow_Post) to compute it.")
    st.stop()

# -------------------- FIX MONTH ORDER --------------------
try:
    df["Month_dt"] = pd.to_datetime(df["Month"], format="%b %y")
except Exception:
    st.warning("⚠️ Could not parse Month column automatically. Ensure it’s in format like 'Jan 25'.")
    st.stop()

df = df.sort_values(["Aircraft_ID", "Month_dt"])
df["Month"] = df["Month_dt"].dt.strftime("%b %y")

# -------------------- AGGREGATION --------------------
df_group = df.groupby(["Aircraft_ID", "Month"])["ΔSFC"].mean().reset_index()

# Maintain correct month order and fill blanks as NaN (white in heatmap)
month_order = sorted(df_group["Month"].unique(), key=lambda x: pd.to_datetime(x, format="%b %y"))
pivot = (
    df_group.pivot(index="Aircraft_ID", columns="Month", values="ΔSFC")
    .reindex(columns=month_order)
    .sort_index()
)

# -------------------- HEATMAP --------------------
st.subheader("🌡️ Fleet Performance Heatmap (ΔSFC %)")
fig = px.imshow(
    pivot,
    color_continuous_scale="RdYlGn_r",
    aspect="auto",
    labels=dict(x="Month", y="Aircraft ID", color="ΔSFC (%)"),
    title="Average ΔSFC per Aircraft and Month — Red = Worse, Green = Better",
    zmin=np.nanmin(pivot.values),
    zmax=np.nanmax(pivot.values),
)
fig.update_layout(
    template=plotly_template,
    coloraxis_colorbar=dict(title="ΔSFC (%)"),
)
st.plotly_chart(fig, use_container_width=True)

# -------------------- MULTI-AIRCRAFT LINE GRAPH --------------------
st.subheader("📊 Aircraft ΔSFC Trendline Comparison")

# Dropdown selection for one or multiple aircraft
aircraft_options = sorted(df_group["Aircraft_ID"].unique().tolist())
selected_aircraft = st.multiselect(
    "Select Aircraft to View Trendlines:",
    options=aircraft_options,
    default=aircraft_options[:3],  # Default to first 3 for convenience
    help="Select one or multiple aircraft to display their ΔSFC performance trends."
)

# Filter dataset based on selection
if selected_aircraft:
    df_filtered = df_group[df_group["Aircraft_ID"].isin(selected_aircraft)]
    fig_line = px.line(
        df_filtered,
        x="Month",
        y="ΔSFC",
        color="Aircraft_ID",
        markers=True,
        title="ΔSFC Trend per Aircraft (Monthly Average)",
        line_shape="linear",
    )
    fig_line.update_layout(
        template=plotly_template,
        xaxis_title="Month",
        yaxis_title="ΔSFC (%)",
        font=dict(color=text_color, size=14),
        legend_title="Aircraft ID",
    )
    # Optional stacked offset look (for better separation)
    for i, trace in enumerate(fig_line.data):
        trace.line.width = 3
        trace.line.shape = "spline"
        trace.opacity = 0.9
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("Select one or more aircraft from the dropdown to display their ΔSFC trends.")

# -------------------- METRICS --------------------
avg_deg = float(df_group["ΔSFC"].mean())
worst_row = df_group.loc[df_group["ΔSFC"].idxmax()]
best_row = df_group.loc[df_group["ΔSFC"].idxmin()]

c1, c2, c3 = st.columns(3)
c1.metric("Fleet Avg ΔSFC", f"{avg_deg:.2f}%")
c2.metric("Best (Lowest ΔSFC)", f"{best_row['Aircraft_ID']} • {best_row['Month']} • {best_row['ΔSFC']:.2f}%")
c3.metric("Worst (Highest ΔSFC)", f"{worst_row['Aircraft_ID']} • {worst_row['Month']} • {worst_row['ΔSFC']:.2f}%")

# -------------------- ALERT SYSTEM --------------------
threshold = st.slider("Alert threshold for abnormal ΔSFC (%)", 0.5, 5.0, 2.0, 0.1)
abnormal = df_group[df_group["ΔSFC"] > threshold]

if not abnormal.empty:
    st.warning(f"⚠️ {len(abnormal)} aircraft-month cells exceed ΔSFC > {threshold:.1f}%. Consider scheduling inspections or washes.")
else:
    st.success("✅ No ΔSFC values exceed the selected alert threshold.")

# -------------------- DOWNLOAD --------------------
csv = pivot.to_csv(index=True).encode("utf-8")
st.download_button("💾 Download Heatmap Data (CSV)", csv, "fleet_heatmap.csv", "text/csv")
