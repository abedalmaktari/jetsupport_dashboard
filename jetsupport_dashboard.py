# -*- coding: utf-8 -*-
# ==========================================================
# JetSupport Engine Wash Performance Dashboard
# ==========================================================
# (c) 2025 JetSupport - Developed by A. Almaktari

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# -------------------- PAGE CONFIG --------------------
st.set_page_config(page_title="JetSupport Engine Wash Dashboard", layout="wide")

# -------------------- BRAND COLORS --------------------
JS_BLUE = "#00529B"
JS_RED = "#E43D30"
BG_COLOR = "#FFFFFF"
SECTION_BG = "#F5F6F8"
TEXT_COLOR = "#0B1F33"
PLOTLY_TEMPLATE = "plotly_white"

# -------------------- GLOBAL STYLE --------------------
st.markdown(
    f"""
<style>
html, body, [data-testid="stAppViewContainer"], [class*="View"], .main, .block-container {{
    background-color: {BG_COLOR} !important;
    color: {TEXT_COLOR} !important;
}}

/* Sidebar + widgets */
section[data-testid="stSidebar"] {{
    background-color: {SECTION_BG} !important;
    color: {TEXT_COLOR} !important;
}}
section[data-testid="stSidebar"] * {{
    background-color: transparent !important;
    color: {TEXT_COLOR} !important;
}}
div[data-baseweb="input"], div[data-baseweb="select"], textarea, input {{
    background-color: #FFFFFF !important;
    color: {TEXT_COLOR} !important;
    border: 1px solid #DADCE0 !important;
    border-radius: 8px !important;
}}

/* File uploader box */
[data-testid="stFileUploaderDropzone"] {{
    background-color: #FFFFFF !important;
    border: 1px dashed #C7CBD1 !important;
}}
[data-testid="stFileUploaderDropzone"] * {{
    color: {TEXT_COLOR} !important;
}}

/* Top bar */
header[data-testid="stHeader"] {{
    background-color: {BG_COLOR} !important;
    color: {TEXT_COLOR} !important;
    border-bottom: 1px solid #E0E0E0 !important;
}}

/* Metrics */
div[data-testid="stMetric"] {{
    background-color: #FFFFFF !important;
    color: {TEXT_COLOR} !important;
    border-radius: 12px;
    padding: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}}

/* Text elements */
h1, h2, h3, h4, h5, h6, p, label, span {{
    color: {TEXT_COLOR} !important;
}}

/* Buttons, sliders, radio */
button, [role="radiogroup"] label {{
    color: {TEXT_COLOR} !important;
}}
div[role="slider"] > div {{
    background-color: {JS_BLUE} !important;
}}

/* Alert/info boxes */
[data-testid="stAlert"] {{
    border-radius: 10px !important;
    border: 1px solid #E0E0E0 !important;
}}

/* Scrollbars light */
::-webkit-scrollbar {{
    width: 8px;
}}
::-webkit-scrollbar-thumb {{
    background-color: #C7CBD1;
    border-radius: 10px;
}}
</style>
""",
    unsafe_allow_html=True,
)

# -------------------- HEADER --------------------
logo_path = Path("jetsupport_logo.png")
with st.container():
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)
        else:
            st.warning("⚠️ jetsupport_logo.png not found next to this file.")
    with col_title:
        st.markdown(
            f"""
            <div style="background:#FFFFFF;
                        border-radius:10px;padding:14px 18px;
                        box-shadow:0 2px 4px rgba(0,0,0,0.05);">
                <h1 style="margin:0;color:{TEXT_COLOR};font-weight:800;font-size:2rem;">
                    JetSupport Engine Wash Performance Dashboard
                </h1>
                <p style="color:#5A6B7A;margin-top:6px;font-size:1rem;">
                    Monitor engine performance, optimise compressor wash intervals,
                    and quantify sustainability benefits using QAR data or simulation models.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# -------------------- SIDEBAR --------------------
st.sidebar.title("JetSupport Dashboard")
st.sidebar.header("⚙️ Data Mode")
mode = st.sidebar.radio("Choose mode:", ["📊 QAR Data", "🧠 Simulation Model"])
qar_mode = mode == "📊 QAR Data"

DOMINANT, ACCENT = (JS_BLUE, JS_RED) if qar_mode else (JS_RED, JS_BLUE)
st.markdown(
    f"<div style='background:{DOMINANT};padding:10px;border-radius:10px;color:white;text-align:center;'>"
    f"<b>{'📊 QAR Data' if qar_mode else '🧠 Simulation Model'} Mode Active</b>"
    f"</div>",
    unsafe_allow_html=True,
)
st.write("")

# -------------------- QAR FILE UPLOAD --------------------
st.sidebar.header("📁 QAR Upload")
uploaded_file = st.sidebar.file_uploader("Upload (.csv or .dat)", type=["csv", "dat"])
qar_df = None
if uploaded_file:
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            qar_df = pd.read_csv(uploaded_file)
        else:
            qar_df = pd.read_csv(uploaded_file, delim_whitespace=True, engine="python")
        st.sidebar.success(f"✅ Loaded {uploaded_file.name}")
    except Exception as e:
        st.sidebar.error(f"⚠️ Error reading file: {e}")

# -------------------- OPERATIONAL INPUTS --------------------
st.sidebar.header("🔧 Operational Inputs")
EGT_before = st.sidebar.number_input("EGT before wash (°C)", 400, 800, 630)
EGT_after = st.sidebar.number_input("EGT after wash (°C)", 400, 800, 620)
flight_time = st.sidebar.number_input("Average flight duration (hr)", 0.5, 10.0, 2.5)
flights_per_year = st.sidebar.number_input("Flights per year", 50, 2000, 600)
fuel_price = st.sidebar.number_input("Jet-A1 price (€ / kg)", 0.1, 3.0, 0.8)
wash_cost = st.sidebar.number_input("Cost per compressor wash (€)", 1000, 20000, 4000)
aircraft_name = st.sidebar.text_input("Aircraft ID / Client", "NetJets Citation")

# -------------------- CONSTANTS --------------------
CF = 3.16
fuel_flow = 0.521
deg_rate_default = 0.013
recovery_default = 1.00

# -------------------- MODE-SPECIFIC INPUTS --------------------
if qar_mode:
    st.sidebar.markdown("---")
    st.sidebar.header("📊 QAR-derived Inputs")
    degradation_rate = st.sidebar.number_input(
        "Degradation rate (% per flight)",
        0.00001, 0.05, 0.01200, 0.00001, format="%.5f",
    )
    recovery_factor = st.sidebar.slider(
        "Efficiency recovery per wash (% of lost perf)", 50, 100, 92
    ) / 100.0

    if qar_df is not None:
        st.success("📈 QAR data detected — auto-computing ΔSFC and trends.")
        if {"Fuel_Flow_Pre", "Fuel_Flow_Post"}.issubset(qar_df.columns):
            qar_df["Delta_SFC"] = (
                (qar_df["Fuel_Flow_Pre"] - qar_df["Fuel_Flow_Post"]) / qar_df["Fuel_Flow_Pre"] * 100.0
            )
            dSFC = qar_df["Delta_SFC"].mean()
        else:
            dSFC = 1.6
        fuel_flow_pre = qar_df.get("Fuel_Flow_Pre", pd.Series([1250])).mean()
        fuel_flow_post = qar_df.get("Fuel_Flow_Post", pd.Series([1230])).mean()
    else:
        st.info("No QAR file — enter manual values.")
        fuel_flow_pre = st.sidebar.number_input("Fuel flow pre-wash (kg/hr)", 500, 4000, 1250)
        fuel_flow_post = st.sidebar.number_input("Fuel flow post-wash (kg/hr)", 400, 4000, 1230)
        dSFC = (fuel_flow_pre - fuel_flow_post) / fuel_flow_pre * 100.0
else:
    st.sidebar.markdown("---")
    st.sidebar.header("🧠 Simulation Settings")
    degradation_rate = deg_rate_default
    recovery_factor = recovery_default
    dSFC = 0.08 * (EGT_before - EGT_after)

# -------------------- CORE CALCS --------------------
fuel_saved_flight = fuel_flow * (dSFC / 100.0) * flight_time * 3600.0
CO2_saved_flight = fuel_saved_flight * CF
CO2_saved_annual = CO2_saved_flight * flights_per_year / 1000.0
cost_saved_annual = fuel_saved_flight * flights_per_year * fuel_price

# -------------------- KPI CARDS --------------------
st.subheader("📊 Key Results")
c1, c2, c3 = st.columns(3)
c1.metric("ΔSFC", f"{dSFC:.2f} %")
c2.metric("Fuel Saved / Flight", f"{fuel_saved_flight:.1f} kg")
c3.metric("Annual CO₂ Saved", f"{CO2_saved_annual:.1f} t")
c4, c5 = st.columns(2)
c4.metric("💶 Annual Cost Saved", f"€ {cost_saved_annual:,.2f}")
c5.metric("Mode", "QAR Data" if qar_mode else "Simulation Model")

# -------------------- PLOTLY LAYOUT FUNCTION --------------------
def clean_plotly(fig):
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor=BG_COLOR,
        plot_bgcolor="#FFFFFF",
        font=dict(color=TEXT_COLOR, size=14),
        xaxis=dict(showgrid=True, gridcolor="#D9D9D9", linewidth=1.5),
        yaxis=dict(showgrid=True, gridcolor="#D9D9D9", linewidth=1.5),
        legend=dict(bgcolor="#FFFFFF", bordercolor="#E0E0E0", borderwidth=1)
    )

# -------------------- KPI GAUGES --------------------
st.subheader("📈 Efficiency Gauges")
gcols = st.columns(3)

g1 = go.Figure(go.Indicator(mode="gauge+number", value=dSFC,
                            title={"text": "ΔSFC (%)"},
                            gauge={"axis": {"range": [0, 5]},
                                   "bar": {"color": DOMINANT}}))
clean_plotly(g1)
gcols[0].plotly_chart(g1, use_container_width=True)

g2 = go.Figure(go.Indicator(mode="gauge+number", value=CO2_saved_annual,
                            title={"text": "CO₂ Saved (t)"},
                            gauge={"axis": {"range": [0, max(10.0, CO2_saved_annual * 1.25)]},
                                   "bar": {"color": ACCENT}}))
clean_plotly(g2)
gcols[1].plotly_chart(g2, use_container_width=True)

g3 = go.Figure(go.Indicator(mode="gauge+number", value=cost_saved_annual / 1000.0,
                            title={"text": "Annual Cost Saved (×1000 €)"},
                            gauge={"axis": {"range": [0, max(10.0, (cost_saved_annual / 1000.0) * 1.25)]},
                                   "bar": {"color": DOMINANT}}))
clean_plotly(g3)
gcols[2].plotly_chart(g3, use_container_width=True)

# -------------------- COST–BENEFIT --------------------
st.markdown("---")
st.subheader("🧩 Engine Wash Optimization (Cost–Benefit)")

max_interval = st.sidebar.slider("Max wash interval (flights)", 20, 200, 120, 10)
intervals = list(range(20, max_interval + 1, 10))
fuel_costs, wash_costs, net_savings = [], [], []

deg = 0.0
fuel_burn = 0.0
for _ in range(flights_per_year):
    fuel_burn += 1.0 + deg / 100.0
    deg += degradation_rate
baseline_fuel_kg = fuel_flow * flight_time * 3600.0 * fuel_burn
baseline_cost = baseline_fuel_kg * fuel_price

for iv in intervals:
    deg = 0.0
    fuel_burn = 0.0
    for i in range(flights_per_year):
        fuel_burn += 1.0 + deg / 100.0
        deg += degradation_rate
        if (i + 1) % iv == 0:
            deg *= (1.0 - recovery_factor)
    fuel_kg = fuel_flow * flight_time * 3600.0 * fuel_burn
    fuel_cost = fuel_kg * fuel_price
    n_washes = flights_per_year // iv
    total_wash_cost = n_washes * wash_cost
    net = baseline_cost - (fuel_cost + total_wash_cost)
    fuel_costs.append(fuel_cost)
    wash_costs.append(total_wash_cost)
    net_savings.append(net)

opt_idx = int(np.argmax(net_savings))
opt_interval = intervals[opt_idx]
opt_net = net_savings[opt_idx]
opt_washes = flights_per_year // opt_interval

st.success(
    f"Optimal wash interval: **{opt_interval} flights** "
    f"({opt_washes} washes/yr) → Maximum annual net saving: **€{opt_net:,.0f}**"
)

df_opt = pd.DataFrame({
    "Interval (flights)": intervals,
    "Wash cost (€)": wash_costs,
    "Net saving (€)": net_savings
})
fig_opt = px.line(
    df_opt,
    x="Interval (flights)",
    y=["Wash cost (€)", "Net saving (€)"],
    title="Annual Cost–Benefit of Engine Wash Frequency",
    color_discrete_sequence=[ACCENT, DOMINANT],
)
clean_plotly(fig_opt)
fig_opt.add_vline(x=opt_interval, line_dash="dot", line_color="#DD3333")
st.plotly_chart(fig_opt, use_container_width=True)

# -------------------- DEGRADATION & RECOVERY --------------------
st.subheader("📉 Efficiency Degradation & Post-Wash Recovery (Year)")
cycles = np.arange(flights_per_year)
eff_no, eff_two, eff_opt = [], [], []
deg_no, deg_two, deg_opt = 0.0, 0.0, 0.0
interval_two = max(flights_per_year // 2, 1)

for c in cycles:
    eff_no.append(100 - deg_no)
    eff_two.append(100 - deg_two)
    eff_opt.append(100 - deg_opt)
    deg_no += degradation_rate
    deg_two += degradation_rate
    deg_opt += degradation_rate
    if (c + 1) % interval_two == 0:
        deg_two *= (1.0 - recovery_factor)
    if (c + 1) % opt_interval == 0:
        deg_opt *= (1.0 - recovery_factor)

df_deg = pd.DataFrame({
    "Flight": cycles,
    "No wash": eff_no,
    "2 washes/year": eff_two,
    f"Optimized ({opt_interval} flights)": eff_opt
})
fig_deg = px.line(
    df_deg,
    x="Flight",
    y=["No wash", "2 washes/year", f"Optimized ({opt_interval} flights)"],
    title="Efficiency Degradation and Recovery (Saw-tooth)",
    color_discrete_sequence=["#9AA6B2", ACCENT, DOMINANT],
)
clean_plotly(fig_deg)
st.plotly_chart(fig_deg, use_container_width=True)

# -------------------- FOOTER --------------------
st.markdown("---")
st.markdown(
    f"<div style='text-align:center;color:#555;'>"
    "(c) 2025 JetSupport - Developed by A. Almaktari."
    "</div>",
    unsafe_allow_html=True,
)
