import streamlit as st
import pandas as pd
import plotly.express as px

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="MAA ASHISH – Production Intelligence",
    layout="wide"
)

# ----------------------------
# LOAD DATA
# ----------------------------
@st.cache_data
def load_data():
    file = r"knitting_machine_6months_data_final_v2.xlsx"

    machine = pd.read_excel(file, sheet_name="Machine_Data")
    operator = pd.read_excel(file, sheet_name="operator efficiency")

    machine.columns = machine.columns.str.strip()
    operator.columns = operator.columns.str.strip()

    for df in [machine, operator]:
        df["Date"] = pd.to_datetime(df["Date"])
        df["Year"] = df["Date"].dt.year
        df["Month"] = df["Date"].dt.month
        df["Month_Name"] = df["Date"].dt.strftime("%B")

    return machine, operator


machine_df, operator_df = load_data()

# ----------------------------
# SIDEBAR FILTERS
# ----------------------------
st.sidebar.title("🔍 Filters")

year_sel = st.sidebar.multiselect(
    "Year",
    sorted(machine_df["Year"].unique()),
    default=sorted(machine_df["Year"].unique())
)

month_sel = st.sidebar.multiselect(
    "Month",
    sorted(machine_df["Month_Name"].unique())
)

shift_sel = st.sidebar.multiselect(
    "Shift",
    sorted(machine_df["Shift"].unique()),
    default=sorted(machine_df["Shift"].unique())
)

date_range = st.sidebar.date_input("Date Range", [])

# ----------------------------
# FILTER FUNCTION
# ----------------------------
def apply_filters(df):
    df = df.copy()

    if len(date_range) == 2:
        start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        df = df[(df["Date"] >= start) & (df["Date"] <= end)]
    else:
        if year_sel:
            df = df[df["Year"].isin(year_sel)]
        if month_sel:
            df = df[df["Month_Name"].isin(month_sel)]

    if "Shift" in df.columns and shift_sel:
        df = df[df["Shift"].isin(shift_sel)]

    return df


machine_f = apply_filters(machine_df)
operator_f = apply_filters(operator_df)

if machine_f.empty:
    st.warning("⚠️ No data available for selected filters")
    st.stop()

st.title("🧶 MAA ASHISH – Production Intelligence Dashboard")

# ----------------------------
# TABS
# ----------------------------
tab_machine, tab_prod, tab_operator = st.tabs(
    ["⚙️ Machine Dashboard", "📊 Production Dashboard", "👷 Operator Efficiency"]
)

# ==================================================
# ⚙️ MACHINE DASHBOARD
# ==================================================
with tab_machine:

    st.subheader("⚙️ Machine Performance Overview")

    # UPDATED Efficiency Calculation
    machine_eff = machine_f.copy()
    machine_eff["Efficiency %"] = (
        machine_eff["Actual_Rolls"] / machine_eff["Expected_Rolls"]
    ) * 100

    top_n = st.number_input(
        "Show Top N Efficient Machines",
        min_value=1,
        max_value=20,
        value=5
    )

    top_machines = (
        machine_eff
        .groupby("Machine_No")
        .agg(
            Avg_Efficiency=("Efficiency %", "mean"),
            Total_Rolls=("Actual_Rolls", "sum")
        )
        .reset_index()
        .sort_values("Avg_Efficiency", ascending=False)
        .head(top_n)
    )

    # Ensure machines sorted correctly
    top_machines = top_machines.sort_values("Machine_No")

    fig = px.bar(
        top_machines,
        x=top_machines["Machine_No"].astype(str),   # force categorical axis
        y="Avg_Efficiency",
        text=top_machines["Avg_Efficiency"].round(1).astype(str) + "%",
        category_orders={"x": top_machines["Machine_No"].astype(str).tolist()}
    )

    fig.update_layout(
        xaxis_title="Machine Number",
        yaxis_title="Average Efficiency (%)",
        xaxis_type="category"   # ⭐ ensures categorical spacing
    )

    fig.update_yaxes(range=[0, 100])

    st.plotly_chart(fig, use_container_width=True)


    # Rolls by Machine
    st.subheader("📦 Rolls Produced by Machine")

    rolls_by_machine = (
        machine_f
        .groupby("Machine_No")["Actual_Rolls"]
        .sum()
        .reset_index()
    )

    rolls_by_machine["Machine_No"] = rolls_by_machine["Machine_No"].astype(str)

    fig = px.line(
        rolls_by_machine,
        x="Machine_No",
        y="Actual_Rolls",
        markers=True
    )

    st.plotly_chart(fig, use_container_width=True)

    # MACHINE SUMMARY TABLE
    st.subheader("🔎 Machine-wise Performance Summary")

    machine_summary = (
    machine_f
    .groupby("Machine_No")
    .agg(
        Avg_Rpm=("RPM", "mean"),
        Total_Expected_Rolls=("Expected_Rolls", "sum"),
        Total_Actual_Rolls=("Actual_Rolls", "sum")
    )
    .reset_index()
)

# remove decimals from Avg RPM
    machine_summary["Avg_Rpm"] = machine_summary["Avg_Rpm"].round(0).astype(int)

    machine_summary["Efficiency %"] = (
        machine_summary["Total_Actual_Rolls"] /
        machine_summary["Total_Expected_Rolls"] * 100
    ).round(2)


    machine_summary["Efficiency %"] = machine_summary["Efficiency %"].round(2)

    machine_input = st.text_input(
        "Enter Machine Number (leave empty to view all)",
        placeholder="e.g. 1"
    )

    if machine_input.strip().isdigit():
        machine_summary_view = machine_summary[
            machine_summary["Machine_No"] == int(machine_input)
        ]
    else:
        machine_summary_view = machine_summary.copy()

    st.data_editor(
        machine_summary_view,
        use_container_width=True,
        hide_index=True,
        disabled=True
    )

# ==================================================
# 📊 PRODUCTION DASHBOARD
# ==================================================
with tab_prod:

    st.subheader("📊 Production Overview")

    total_rolls = machine_f["Actual_Rolls"].sum()
    avg_daily = machine_f.groupby("Date")["Actual_Rolls"].sum().mean()

    c1, c2 = st.columns(2)
    c1.metric("Total Rolls Produced", f"{total_rolls:,.0f}")
    c2.metric("Avg Daily Rolls", f"{avg_daily:.1f}")

    prod_trend = (
        machine_f
        .groupby("Date")["Actual_Rolls"]
        .sum()
        .reset_index()
    )

    fig = px.line(prod_trend, x="Date", y="Actual_Rolls", markers=True)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Production Table")

    view_type = st.selectbox(
    "View By",
    ["Machine-wise", "Date-wise"]
)

    if view_type == "Machine-wise":

        table = (
            machine_f
            .groupby("Machine_No")["Actual_Rolls"]
            .sum()
            .reset_index()
            .sort_values("Machine_No")
        )

    else:   # Date-wise → show Date + Machine

        table = (
            machine_f
            .groupby(["Date", "Machine_No"])["Actual_Rolls"]
            .sum()
            .reset_index()
            .sort_values(["Date", "Machine_No"])
        )

        # cleaner date format
        table["Date"] = table["Date"].dt.strftime("%Y-%m-%d")

    st.data_editor(
        table,
        use_container_width=True,
        hide_index=True,
        disabled=True
    )

    
# ==================================================
# 👷 OPERATOR EFFICIENCY DASHBOARD
# ==================================================
with tab_operator:

    st.subheader("👷 Operator Efficiency Overview")

    operator_summary = (
        operator_f
        .groupby("Operator_Name")["Actual_Rolls"]
        .sum()
        .reset_index()
        .sort_values("Actual_Rolls", ascending=False)
    )

    top_n_ops = st.number_input(
        "Show Top N Operators",
        min_value=1,
        max_value=len(operator_summary),
        value=5,
        step=1
    )

    top_ops = operator_summary.head(top_n_ops)

    fig = px.bar(
        top_ops,
        x="Actual_Rolls",
        y="Operator_Name",
        orientation="h",
        text_auto=True
    )

    st.plotly_chart(fig, use_container_width=True)


    # ==============================
    # Shift Efficiency Comparison
    # ==============================

    st.subheader("🌓 Shift Efficiency Comparison")

    shift_eff = (
        operator_f
        .groupby("Shift")
        .agg(
            Expected_Rolls=("Expected_Rolls", "sum"),
            Actual_Rolls=("Actual_Rolls", "sum")
        )
        .reset_index()
    )

    # Calculate efficiency %
    shift_eff["Efficiency %"] = (
        shift_eff["Actual_Rolls"] / shift_eff["Expected_Rolls"] * 100
    ).round(2)

    fig = px.pie(
        shift_eff,
        names="Shift",
        values="Efficiency %",
        title="Day vs Night Shift Efficiency",
        hole=0.4   # donut style (modern look)
    )

    st.plotly_chart(fig, use_container_width=True)


    st.subheader("👷 Operator Performance Summary")

    st.data_editor(
        operator_summary,
        use_container_width=True,
        hide_index=True,
        disabled=True
    )