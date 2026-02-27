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
    file = r"knitting_machine_data.xlsx"

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

date_range = st.sidebar.date_input(
    "Date Range",
    value=(),
    min_value=machine_df["Date"].min(),
    max_value=machine_df["Date"].max(),
    format="YYYY/MM/DD"
)

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

    # 🔍 Machine Search
    search_machine = st.text_input(
        "Search Machine Number",
        placeholder="Type machine number (e.g., 12)"
    )


    df = machine_f.copy()

    if search_machine.strip().isdigit():
        df =df[
            df["Machine_No"] == int(search_machine)
        ]


    # efficiency
    df["Efficiency %"] = df["Actual_Rolls"] / df["Expected_Rolls"] * 100

    # machine specs
    specs = (
        df.groupby("Machine_No")
        .agg(
            RPM=("RPM", "mean"),
            Counter_12hrs=("Counter_12hrs", "mean"),
            Counter_Set_Per_Roll=("Counter_Set_Per_Roll", "mean"),
        )
        .reset_index()
    )

    # DAY SHIFT
    day = (
        df[df["Shift"] == "Day"]
        .groupby("Machine_No")
        .agg(
            Day_Expected_rolls=("Expected_Rolls", "sum"),
            Day_Actual_rolls=("Actual_Rolls", "sum"),
        )
        .reset_index()
    )
    day["Day Eff %"] = day["Day_Actual_rolls"] / day["Day_Expected_rolls"] * 100

    # NIGHT SHIFT
    night = (
        df[df["Shift"] == "Night"]
        .groupby("Machine_No")
        .agg(
            Night_Expected_rolls=("Expected_Rolls", "sum"),
            Night_Actual_rolls=("Actual_Rolls", "sum"),
        )
        .reset_index()
    )
    night["Night Eff %"] = night["Night_Actual_rolls"] / night["Night_Expected_rolls"] * 100

    # TOTAL
    # Calculate Overall Efficiency (average of day and night)
    summary_temp = specs.merge(day, on="Machine_No", how="left") \
                .merge(night, on="Machine_No", how="left")
    
    summary_temp["Overall Eff %"] = (
        (summary_temp["Day Eff %"] + summary_temp["Night Eff %"]) / 2
    )
    
    summary = summary_temp

    # format numbers (clean look)
    summary["RPM"] = summary["RPM"].round().astype(int)
    summary["Counter_12hrs"] = summary["Counter_12hrs"].round().astype(int)
    summary["Counter_Set_Per_Roll"] = summary["Counter_Set_Per_Roll"].round().astype(int)

    for col in summary.columns:
        if "Eff" in col:
            summary[col] = summary[col].round(1)

    summary = summary.rename(columns={
        "Machine_No": "Machine",
        "Counter_12hrs": "Counter (12 hrs)",
        "Counter_Set_Per_Roll": "Counter per Roll"
    })

    st.dataframe(
        summary.sort_values("Machine"),
        use_container_width=True,
        hide_index=True
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

    # ============================
    # 📋 Production Summary Table
    # ============================
    st.subheader("📋 Production Table")

    col1, col2 = st.columns(2)

    with col1:
        machine_search = st.text_input(
            "Search by Machine Number",
            placeholder="e.g. 1 or 25"
        )

    with col2:
        date_search = st.date_input("Search by Date", value=None)

    prod_table = machine_f.copy()

    # Machine filter
    if machine_search:
        prod_table = prod_table[
            prod_table["Machine_No"] == int(machine_search)
        ]

    # Date filter
    if date_search:
        prod_table = prod_table[
            prod_table["Date"] == pd.to_datetime(date_search)
        ]

    # ✅ Remove time from date
    prod_table["Date"] = prod_table["Date"].dt.date

    # Create summary
    prod_table = (
        prod_table
        .groupby(["Date", "Machine_No"])["Actual_Rolls"]
        .sum()
        .reset_index()
        .rename(columns={
            "Machine_No": "Machine Number",
            "Actual_Rolls": "Total_Rolls"
        })
        .sort_values(["Date", "Machine Number"])
    )

    st.data_editor(
        prod_table,
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


    st.subheader("🧑‍🏭 Operator Performance Summary")

    # ---------- Operator Filter ----------
    operators = ["All"] + sorted(operator_f["Operator_Name"].dropna().unique().tolist())

    selected_operator = st.selectbox(
        "Select Operator (optional)",
        operators
    )

    data = operator_f.copy()

    if selected_operator != "All":
        data = data[data["Operator_Name"] == selected_operator]

    # ---------- Summary Calculation ----------
    summary = (
        data.groupby("Operator_Name")
        .agg(
            Production=("Actual_Rolls", "sum"),
            Machines_Handled=("Machine_No", lambda x: ", ".join(map(str, sorted(x.unique())))),
            Expected=("Expected_Rolls", "sum"),
            Actual=("Actual_Rolls", "sum"),
        )
        .reset_index()
    )

    # Efficiency %
    summary["Efficiency %"] = (
        summary["Actual"] / summary["Expected"] * 100
    ).round(2)

    # Remove helper columns
    summary = summary.drop(columns=["Expected", "Actual"])

    # Rename columns for display
    summary.columns = [
        "Machine Operator",
        "Production",
        "Machines Handled",
        "Efficiency %"
    ]

    # Sort by efficiency
    summary = summary.sort_values("Efficiency %", ascending=False)

    # ---------- Display ----------
    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True
    )
