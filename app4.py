import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Blue Collar Storage • Financials", layout="wide", page_icon="🔧")

st.title("🔧 Blue Collar Storage – 5-Year Financial Projections")
st.markdown("**Open-Air Contractor Bays + RV/Boat Storage** • Powdersville / Anderson County, SC")

# ====================== SIDEBAR ======================
with st.sidebar:
    st.header("📍 Business Setup")
    acres = st.number_input("Land Size (acres)", 3.0, 6.0, 4.0, step=0.1)
    land_per_acre = st.number_input("Land Price per Acre ($)", 40000, 200000, 75000)
    improvements = st.number_input("Development/Improvements ($)", 100000, 1000000, 250000)
    down_pct = st.slider("Down Payment %", 10, 30, 20)
    
    total_capex = acres * land_per_acre + improvements
    down_payment = total_capex * down_pct / 100
    loan_amount = total_capex - down_payment
    
    st.metric("Total Startup Capex", f"${total_capex:,.0f}")
    st.metric("SBA Loan Amount", f"${loan_amount:,.0f}")

    st.header("💰 Revenue Drivers")
    col1, col2 = st.columns(2)
    with col1:
        contractor_spots = st.number_input("Contractor Bays", 10, 100, 40)
        contractor_rate = st.number_input("Contractor $/mo", 100, 400, 200)
        rv_spots = st.number_input("RV/Boat Spots", 20, 150, 60)
        rv_rate = st.number_input("RV/Boat $/mo", 50, 200, 100)
    with col2:
        conex_spots = st.number_input("Conex Boxes (Y3+)", 0, 50, 20)
        conex_rate = st.number_input("Conex $/mo", 100, 300, 150)
        alacarte_pct = st.slider("A la Carte % of base rental", 0, 30, 15) / 100

    st.header("📈 Occupancy Ramp")
    occ = [st.slider(f"Year {y} Occupancy %", 30, 100, v) / 100 
           for y, v in zip(range(1,6), [45,75,85,92,95])]

    st.header("💸 Expenses & Loan")
    fixed_opex = st.number_input("Fixed Annual OpEx ($)", 15000, 100000, 35000)
    prop_tax_rate = st.number_input("Property Tax %", 0.1, 2.0, 0.8) / 100
    maint_fixed_pct = st.number_input("Maint % of Improvements", 0.5, 5.0, 2.0) / 100
    maint_var_pct = st.number_input("Variable Maint % of Revenue", 5, 20, 8) / 100
    loan_rate = st.number_input("Loan Interest Rate %", 5.0, 12.0, 8.5, step=0.1)
    loan_term = st.number_input("Loan Term (years)", 10, 25, 20)
    eff_tax_rate = st.number_input("Effective Tax Rate %", 0, 40, 25) / 100

    if st.button("🚀 Calculate Projections", type="primary", use_container_width=True):
        st.session_state.run_calc = True

# ====================== CALCULATIONS ======================
def calculate_loan_schedule(principal, annual_rate, years):
    monthly_rate = annual_rate / 12 / 100
    months = years * 12
    if monthly_rate == 0:
        pmt = principal / months
    else:
        pmt = principal * monthly_rate * (1 + monthly_rate)**months / ((1 + monthly_rate)**months - 1)
    
    balance = principal
    schedule = []
    for year in range(1, 6):
        annual_interest = 0.0
        annual_principal = 0.0
        for _ in range(12):
            if balance <= 0: break
            interest = balance * monthly_rate
            principal_pay = min(pmt - interest, balance)
            annual_interest += interest
            annual_principal += principal_pay
            balance -= principal_pay
        schedule.append({
            "Year": year,
            "Beg Balance": round(balance + annual_principal, 2),
            "Payment": round(annual_interest + annual_principal, 2),
            "Interest": round(annual_interest, 2),
            "Principal": round(annual_principal, 2),
            "End Balance": round(max(0, balance), 2)
        })
    return pd.DataFrame(schedule)

if "run_calc" not in st.session_state:
    st.session_state.run_calc = False

if st.session_state.run_calc:
    loan_df = calculate_loan_schedule(loan_amount, loan_rate, loan_term)
    annual_dep = improvements / 20.0

    data = []
    cash = 50000.0
    fixed_assets_net = float(improvements)
    land_cost = acres * land_per_acre

    for year in range(1, 6):
        occ_rate = occ[year-1]
        
        contractor_rev = contractor_spots * contractor_rate * 12 * occ_rate
        rv_rev = rv_spots * rv_rate * 12 * occ_rate
        conex_rev = (year >= 3) * conex_spots * conex_rate * 12 * occ_rate
        base_rental = contractor_rev + rv_rev + conex_rev
        alacarte_rev = base_rental * alacarte_pct
        total_rev = base_rental + alacarte_rev

        prop_tax = (land_cost + improvements) * prop_tax_rate
        maint_fixed = improvements * maint_fixed_pct
        maint_var = total_rev * maint_var_pct
        total_opex = fixed_opex + prop_tax + maint_fixed + maint_var

        noi = total_rev - total_opex
        interest = float(loan_df.loc[year-1, "Interest"])
        ebt = noi - annual_dep - interest
        taxes = max(0, ebt * eff_tax_rate)
        net_income = ebt - taxes

        principal_pay = float(loan_df.loc[year-1, "Principal"])
        op_cash = net_income + annual_dep
        net_cf = op_cash - principal_pay
        cash += net_cf

        fixed_assets_net = max(0, fixed_assets_net - annual_dep)
        total_assets = cash + land_cost + fixed_assets_net
        loan_bal = float(loan_df.loc[year-1, "End Balance"])
        equity = total_assets - loan_bal

        data.append({
            "Year": f"Year {year}",
            "Revenue": total_rev,
            "OpEx": total_opex,
            "NOI": noi,
            "Depreciation": annual_dep,
            "Interest": interest,
            "EBT": ebt,
            "Taxes": taxes,
            "Net Income": net_income,
            "Op Cash Flow": op_cash,
            "Principal Pay": principal_pay,
            "Net Cash Flow": net_cf,
            "Ending Cash": cash,
            "Land": land_cost,
            "Improvements Net": fixed_assets_net,
            "Total Assets": total_assets,
            "Loan Balance": loan_bal,
            "Equity": equity,
            "DSCR": noi / loan_df.loc[year-1, "Payment"] if loan_df.loc[year-1, "Payment"] > 0 else 0
        })

    df = pd.DataFrame(data)

    # ====================== TABS ======================
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "📈 P&L", "💸 Cash Flow", "📉 Balance Sheet", "🏦 Loan & DSCR"])

    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        y5 = df.iloc[4]
        col1.metric("Y5 Revenue", f"${y5['Revenue']:,.0f}")
        col2.metric("Y5 Net Income", f"${y5['Net Income']:,.0f}")
        col3.metric("Y5 Cash", f"${y5['Ending Cash']:,.0f}")
        col4.metric("Y5 DSCR", f"{y5['DSCR']:.2f}x")

        fig = px.bar(df, x="Year", y="Revenue", title="Revenue Growth")
        st.plotly_chart(fig, use_container_width=True)

    # === ROBUST FORMATTING FUNCTION ===
    def money_format(df, columns):
        styled = df.copy()
        for col in columns:
            if col in styled.columns:
                styled[col] = pd.to_numeric(styled[col], errors='coerce')
        return styled.style.format("${:,.0f}", subset=[c for c in columns if c in styled.columns])

    with tab2:
        st.subheader("Profit & Loss")
        cols = ["Year","Revenue","OpEx","NOI","Depreciation","Interest","EBT","Taxes","Net Income"]
        st.dataframe(money_format(df, cols[1:]), use_container_width=True)

    with tab3:
        st.subheader("Cash Flow")
        cols = ["Year","Op Cash Flow","Principal Pay","Net Cash Flow","Ending Cash"]
        st.dataframe(money_format(df, cols[1:]), use_container_width=True)

    with tab4:
        st.subheader("Balance Sheet")
        cols = ["Year","Ending Cash","Land","Improvements Net","Total Assets","Loan Balance","Equity"]
        st.dataframe(money_format(df, cols[1:]), use_container_width=True)

    with tab5:
        st.subheader("Loan Schedule & DSCR")
        loan_display = loan_df.copy()
        loan_display["DSCR"] = df["DSCR"].values
        st.dataframe(loan_display.style.format({
            "Beg Balance":"${:,.0f}", "Payment":"${:,.0f}", "Interest":"${:,.0f}",
            "Principal":"${:,.0f}", "End Balance":"${:,.0f}", "DSCR":"{:.2f}x"
        }), use_container_width=True)

    # Excel Export
    with pd.ExcelWriter("blue_collar_storage_projections.xlsx", engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Summary", index=False)
        loan_df.to_excel(writer, sheet_name="Loan Schedule", index=False)

    with open("blue_collar_storage_projections.xlsx", "rb") as f:
        st.download_button("📥 Download Excel", f, file_name="blue_collar_storage_projections.xlsx")

else:
    st.info("👈 Adjust sidebar inputs then click **Calculate Projections**")

st.caption("All set for your SBA loan package or internal planning.")