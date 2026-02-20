"""Streamlit dashboard for net-worth projection over time."""

# from __future__ import annotations

from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from CompanyStock import generate_company_stock_positions
from Employment import generate_employment_cashflows
from House import generate_house_cashflows
from Miscellaneous import generate_misc_cashflows
from PretaxOutflow import generate_espp_positions, generate_roth_ira_positions
from Rent import generate_rent_cashflows


def _sum_cashflows(start_year: int, end_year: int, *cashflow_sets: dict[int, float]) -> dict[int, float]:
    """Combine yearly cashflow dictionaries by summing values per year."""
    combined = {}
    for year in range(start_year, end_year + 1):
        combined[year] = sum(cashflow.get(year, 0.0) for cashflow in cashflow_sets)
    return combined


def _employment_gross_income_by_year(
    start_year: int,
    end_year: int,
    initial_salary: float,
    annual_raise_pct: float,
    annual_bonus: float,
) -> dict[int, float]:
    """Return yearly gross employment income used for Roth IRA phase-out."""
    raise_rate = annual_raise_pct / 100.0
    gross_income: dict[int, float] = {}
    for year in range(start_year, end_year + 1):
        year_offset = year - start_year
        salary_for_year = initial_salary * ((1.0 + raise_rate) ** year_offset)
        gross_income[year] = salary_for_year + annual_bonus
    return gross_income


def _add_income_components(
    start_year: int,
    end_year: int,
    base_income_by_year: dict[int, float],
    additional_income_by_year: dict[int, float],
) -> dict[int, float]:
    """Return yearly income with additional components included."""
    combined_income: dict[int, float] = {}
    for year in range(start_year, end_year + 1):
        combined_income[year] = base_income_by_year.get(year, 0.0) + additional_income_by_year.get(year, 0.0)
    return combined_income


st.set_page_config(page_title="Financial Projection Dashboard", page_icon="$", layout="wide")
st.title("Striver Financial Projection Dashboard")
st.write("Estimate yearly cashflow and net worth. Preset for prospective SpaceX employees.")

current_year = date.today().year

with st.sidebar:
    st.header("Projection Inputs")
    start_year = st.number_input("Start year", min_value=1900, max_value=2200, value=current_year, step=1)
    projection_years = st.slider("Years to project", min_value=1, max_value=60, value=30, step=1)
    end_year = int(start_year) + int(projection_years) - 1

    initial_net_worth = st.number_input(
        "Initial liquid net worth ($)", min_value=-5_000_000.0, max_value=50_000_000.0, value=30_000.0, step=5_000.0
    )
    investment_return_pct = st.slider("Expected annual return on liquid assets (%)", -20.0, 20.0, 9.0, 0.1)

    st.divider()
    st.subheader("Employment")
    salary = st.number_input("Salary in start year ($)", min_value=0.0, value=120_000.0, step=1_000.0)
    raise_pct = st.slider("Expected raise per year (%)", min_value=-10.0, max_value=20.0, value=4.0, step=0.1)
    annual_bonus = st.number_input("Annual bonus ($)", min_value=0.0, value=0.0, step=1_000.0)
    effective_tax_rate_pct = st.slider("Effective tax rate (%)", min_value=0.0, max_value=60.0, value=24.0, step=0.5)

    st.divider()
    st.subheader("Housing")
    buy_house = st.checkbox("Plan to buy a house", value=True)
    previous_buy_house = st.session_state.get("previous_buy_house", buy_house)
    purchase_year = None
    purchase_price = 0.0
    down_payment_pct = 0.0
    mortgage_rate_pct = 0.0
    mortgage_term_years = 30
    property_tax_pct = 0.0
    home_insurance_pct = 0.0
    maintenance_pct = 0.0
    home_appreciation_pct = 0.0
    annual_tenant_rent_income = 0.0
    tenant_rent_growth_pct = 0.0
    annual_rent = 0.0
    annual_rent_growth_pct = 0.0

    if buy_house:
        default_purchase_year = min(max(int(start_year) + 0, int(start_year)), int(end_year))
        purchase_year = int(
            st.number_input(
                "House purchase year",
                min_value=int(start_year),
                max_value=int(end_year),
                value=default_purchase_year,
                step=1,
            )
        )
        home_appreciation_pct = st.slider(
            "Home appreciation per year (%)",
            min_value=-5.0,
            max_value=15.0,
            value=3.5,
            step=0.1,
            key="home_appreciation_pct_input",
        )
        years_until_purchase = max(0, int(purchase_year) - int(start_year))
        purchase_price_default = 300_000.0 * ((1.0 + (home_appreciation_pct / 100.0)) ** years_until_purchase)
        previous_default_purchase_price = st.session_state.get("purchase_price_default_value")
        existing_purchase_price = st.session_state.get("purchase_price_input")
        if existing_purchase_price is None:
            st.session_state["purchase_price_input"] = purchase_price_default
        elif previous_default_purchase_price is not None and abs(
            float(existing_purchase_price) - float(previous_default_purchase_price)
        ) < 0.01:
            st.session_state["purchase_price_input"] = purchase_price_default
        st.session_state["purchase_price_default_value"] = purchase_price_default
        purchase_price = st.number_input(
            "Purchase price ($)",
            min_value=0.0,
            value=purchase_price_default,
            step=5_000.0,
            key="purchase_price_input",
        )
        st.session_state["last_house_purchase_price"] = purchase_price
        down_payment_pct = st.slider("Down payment (%)", min_value=0.0, max_value=100.0, value=10.0, step=1.0)
        mortgage_rate_pct = st.slider("Mortgage rate (%)", min_value=0.0, max_value=15.0, value=6.0, step=0.1)
        mortgage_term_years = st.selectbox("Mortgage term (years)", options=[10, 15, 20, 30], index=3)
        property_tax_pct = st.slider("Property tax (% of home value)", min_value=0.0, max_value=5.0, value=1.6, step=0.1)
        home_insurance_pct = st.slider("Home insurance (% of home value)", min_value=0.0, max_value=5.0, value=1.4, step=0.1)
        maintenance_pct = st.slider("Maintenance (% of home value)", min_value=0.0, max_value=5.0, value=1.75, step=0.1)
        annual_tenant_rent_income = st.number_input(
            "Annual rent from tenants ($)",
            min_value=0.0,
            value=8400.0,
            step=1_000.0,
        )
        tenant_rent_growth_pct = st.slider(
            "Tenant rent growth per year (%)",
            min_value=-20.0,
            max_value=20.0,
            value=-10.0,
            step=0.1,
        )
    else:
        default_house_price_for_rent = st.session_state.get("last_house_purchase_price", 300_000.0)
        default_rent = default_house_price_for_rent * 0.028
        if "annual_rent_input" not in st.session_state:
            st.session_state["annual_rent_input"] = default_rent
        if previous_buy_house:
            st.session_state["annual_rent_input"] = default_rent
        annual_rent = st.number_input("Annual rent ($)", min_value=0.0, step=1_000.0, key="annual_rent_input")
        annual_rent_growth_pct = st.slider(
            "Rent growth per year (%)", min_value=-5.0, max_value=20.0, value=3.0, step=0.1
        )
    st.session_state["previous_buy_house"] = buy_house

    st.divider()
    st.subheader("Miscellaneous")
    annual_living_expenses = st.number_input("Annual living expenses ($)", min_value=0.0, value=30_000.0, step=1_000.0)
    expense_inflation_pct = st.slider("Expense inflation per year (%)", min_value=-5.0, max_value=15.0, value=8.0, step=0.1)

    st.divider()
    st.subheader("Pretax Outflow")
    espp_annual_contribution = st.number_input(
        "ESPP annual contribution from liquid cash ($)",
        min_value=0.0,
        value=25_000.0,
        step=1_000.0,
    )
    espp_discount_pct = st.slider("ESPP purchase discount (%)", min_value=0.0, max_value=25.0, value=15.0, step=1.0)
    st.caption("ESPP growth depends on the company stock sale setting below.")

    roth_ira_contribution = st.number_input(
        "Roth IRA annual contribution ($, max 7000)",
        min_value=0.0,
        max_value=7000.0,
        value=7000.0,
        step=100.0,
    )
    roth_ira_starting_value = st.number_input(
        "Starting Roth IRA balance ($)",
        min_value=0.0,
        value=40_000.0,
        step=1_000.0,
    )
    st.caption("Roth IRA growth is tied to liquid asset return rate.")
    st.caption("Roth IRA phase-out (\\$146,000 to \\$161,000) uses salary + bonus + newly vested company stock.")

    st.divider()
    st.subheader("Company Stock")
    sell_company_stock_when_possible = st.checkbox("Sell company stock when possible", value=False)
    st.info(
        "This setting affects both vested company stock and ESPP. "
        "If enabled, vested company stock is sold into liquid assets and ESPP is modeled at liquid return. "
        "If disabled, vested company stock is held and ESPP is modeled at company stock return."
    )
    company_stock_grant = st.number_input("Initial grant value ($)", min_value=0.0, value=110_000.0, step=5_000.0)
    company_stock_vesting_years = st.slider("Vesting period (years)", min_value=1, max_value=10, value=5, step=1)
    company_stock_appreciation_pct = st.slider(
        "Company stock appreciation per year (%)", min_value=-50.0, max_value=100.0, value=15.0, step=0.5
    )
    company_stock_start_year = st.number_input(
        "Vesting start year",
        min_value=int(start_year),
        max_value=int(end_year),
        value=int(start_year),
        step=1,
    )
    company_stock_cliff_years = st.slider("Vesting cliff (years)", min_value=0, max_value=4, value=1, step=1)

employment_cashflows = generate_employment_cashflows(
    int(start_year),
    int(end_year),
    salary,
    raise_pct,
    annual_bonus,
    effective_tax_rate_pct,
)

if buy_house:
    housing_cashflows, house_equity = generate_house_cashflows(
        int(start_year),
        int(end_year),
        purchase_year,
        purchase_price,
        down_payment_pct,
        mortgage_rate_pct,
        int(mortgage_term_years),
        property_tax_pct,
        home_insurance_pct,
        maintenance_pct,
        home_appreciation_pct,
        annual_tenant_rent_income,
        tenant_rent_growth_pct,
    )
else:
    housing_cashflows = generate_rent_cashflows(
        int(start_year),
        int(end_year),
        annual_rent,
        annual_rent_growth_pct,
    )
    house_equity = {year: 0.0 for year in range(int(start_year), int(end_year) + 1)}

misc_cashflows = generate_misc_cashflows(
    int(start_year),
    int(end_year),
    annual_living_expenses,
    expense_inflation_pct,
)

espp_cashflows, espp_account_value, espp_discount_gain = generate_espp_positions(
    int(start_year),
    int(end_year),
    espp_annual_contribution,
    espp_discount_pct,
    # If selling when possible, ESPP behaves like liquid proceeds; otherwise it tracks company stock.
    (investment_return_pct if sell_company_stock_when_possible else company_stock_appreciation_pct),
)

if sell_company_stock_when_possible:
    # If shares are sold as soon as possible, treat ESPP cashflow as realized discount gain.
    espp_cashflows_effective = {
        year: espp_annual_contribution * (espp_discount_pct / 100.0)
        for year in range(int(start_year), int(end_year) + 1)
    }
else:
    # Otherwise ESPP remains a contribution outflow.
    espp_cashflows_effective = espp_cashflows

(
    company_stock_vested,
    company_stock_non_liquid,
    company_stock_value_total,
    company_stock_newly_vested,
) = generate_company_stock_positions(
    int(start_year),
    int(end_year),
    company_stock_grant,
    int(company_stock_vesting_years),
    company_stock_appreciation_pct,
    int(company_stock_start_year),
    int(company_stock_cliff_years),
)

sold_stock_cashflows = {
    year: company_stock_newly_vested.get(year, 0.0) if sell_company_stock_when_possible else 0.0
    for year in range(int(start_year), int(end_year) + 1)
}

# Roth phase-out income includes salary, bonus, and newly vested company stock.
roth_phaseout_income = _add_income_components(
    int(start_year),
    int(end_year),
    _employment_gross_income_by_year(
        int(start_year),
        int(end_year),
        salary,
        raise_pct,
        annual_bonus,
    ),
    company_stock_newly_vested,
)

roth_cashflows, roth_account_value, roth_actual_contribution = generate_roth_ira_positions(
    int(start_year),
    int(end_year),
    roth_ira_contribution,
    investment_return_pct,
    max_annual_contribution=7000.0,
    starting_account_value=roth_ira_starting_value,
    annual_income_by_year=roth_phaseout_income,
    phaseout_start_income=146000.0,
    phaseout_end_income=161000.0,
)

total_cashflows = _sum_cashflows(
    int(start_year),
    int(end_year),
    employment_cashflows,
    housing_cashflows,
    misc_cashflows,
    espp_cashflows_effective,
    roth_cashflows,
    sold_stock_cashflows,
)

liquid_net_worth = {}
projected_net_worth = {}
company_stock_value_held_by_year = {}
liquid_value = float(initial_net_worth)
liquid_return = investment_return_pct / 100.0

for year in range(int(start_year), int(end_year) + 1):
    liquid_value = (liquid_value * (1.0 + liquid_return)) + total_cashflows[year]
    if sell_company_stock_when_possible:
        # When selling is enabled, ESPP is treated as sold immediately.
        # Net liquid impact is modeled via cashflow (discount gain), so avoid double counting.
        liquid_net_worth[year] = liquid_value
        espp_value_in_net_worth = 0.0
    else:
        # When selling is disabled, ESPP remains invested as company-stock-like holdings.
        liquid_net_worth[year] = liquid_value
        espp_value_in_net_worth = espp_account_value.get(year, 0.0)

    if sell_company_stock_when_possible:
        stock_value_in_net_worth = company_stock_non_liquid.get(year, 0.0)
    else:
        stock_value_in_net_worth = company_stock_value_total.get(year, 0.0)

    company_stock_value_held_by_year[year] = stock_value_in_net_worth + espp_value_in_net_worth

    projected_net_worth[year] = (
        liquid_net_worth[year]
        + house_equity.get(year, 0.0)
        + stock_value_in_net_worth
        + espp_value_in_net_worth
        + roth_account_value.get(year, 0.0)
    )

table_rows = []
for year in range(int(start_year), int(end_year) + 1):
    table_rows.append(
        {
            "Year": year,
            "Employment Cashflow": employment_cashflows.get(year, 0.0),
            "Housing Cashflow": housing_cashflows.get(year, 0.0),
            "Misc Cashflow": misc_cashflows.get(year, 0.0),
            "ESPP Cashflow": espp_cashflows_effective.get(year, 0.0),
            "Roth IRA Cashflow": roth_cashflows.get(year, 0.0),
            "Sold Stock Cashflow": sold_stock_cashflows.get(year, 0.0),
            "Total Cashflow": total_cashflows.get(year, 0.0),
            "House Equity": house_equity.get(year, 0.0),
            "ESPP Account Value": 0.0 if sell_company_stock_when_possible else espp_account_value.get(year, 0.0),
            "Roth IRA Value": roth_account_value.get(year, 0.0),
            "Roth IRA Contribution Used": roth_actual_contribution.get(year, 0.0),
            "ESPP Discount Gain": espp_discount_gain.get(year, 0.0),
            "Company Stock Value Held": company_stock_value_held_by_year.get(year, 0.0),
            "Company Stock (Vested)": company_stock_vested.get(year, 0.0),
            "Company Stock (Unvested)": company_stock_non_liquid.get(year, 0.0),
            "Company Stock Sold When Possible": company_stock_newly_vested.get(year, 0.0) if sell_company_stock_when_possible else 0.0,
            "Liquid Net Worth": liquid_net_worth.get(year, 0.0),
            "Projected Net Worth": projected_net_worth.get(year, 0.0),
        }
    )

results_df = pd.DataFrame(table_rows)

left_col, right_col = st.columns(2)

# Persist chart series toggles in session state.
net_worth_series_defaults = {
    "show_net_projected": True,
    "show_net_liquid": True,
    "show_net_housing_equity": True,
    "show_net_company_held": True,
    "show_net_company_non_liquid": True,
    "show_net_roth_ira": True,
}
cashflow_series_defaults = {
    "show_cf_employment": True,
    "show_cf_housing": True,
    "show_cf_misc": True,
    "show_cf_espp": True,
    "show_cf_roth_ira": True,
    "show_cf_sold_stock": True,
    "show_cf_total": True,
}
for key, default_value in {**net_worth_series_defaults, **cashflow_series_defaults}.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

selected_net_worth_series = []
if st.session_state["show_net_projected"]:
    selected_net_worth_series.append("Projected Net Worth")
if st.session_state["show_net_liquid"]:
    selected_net_worth_series.append("Liquid Net Worth")
if st.session_state["show_net_housing_equity"]:
    selected_net_worth_series.append("House Equity")
if st.session_state["show_net_company_held"]:
    selected_net_worth_series.append("Company Stock Value Held")
if st.session_state["show_net_company_non_liquid"]:
    selected_net_worth_series.append("Company Stock (Unvested)")
if st.session_state["show_net_roth_ira"]:
    selected_net_worth_series.append("Roth IRA Value")

selected_cashflow_series = []
if st.session_state["show_cf_employment"]:
    selected_cashflow_series.append("Employment Cashflow")
if st.session_state["show_cf_housing"]:
    selected_cashflow_series.append("Housing Cashflow")
if st.session_state["show_cf_misc"]:
    selected_cashflow_series.append("Misc Cashflow")
if st.session_state["show_cf_espp"]:
    selected_cashflow_series.append("ESPP Cashflow")
if st.session_state["show_cf_roth_ira"]:
    selected_cashflow_series.append("Roth IRA Cashflow")
if st.session_state["show_cf_sold_stock"]:
    selected_cashflow_series.append("Sold Stock Cashflow")
if st.session_state["show_cf_total"]:
    selected_cashflow_series.append("Total Cashflow")

left_col.subheader("Net Worth Over Time")
if selected_net_worth_series:
    net_worth_chart_df = results_df[["Year"] + selected_net_worth_series].copy()
    net_worth_chart_df["YearLabel"] = net_worth_chart_df["Year"].astype(int).astype(str)
    net_worth_chart_df = net_worth_chart_df.melt(
        id_vars=["Year", "YearLabel"],
        var_name="Series",
        value_name="Value",
    )
    year_order = results_df["Year"].astype(int).astype(str).tolist()
    base_net = alt.Chart(net_worth_chart_df).encode(
        x=alt.X("YearLabel:N", sort=year_order, axis=alt.Axis(title="Year", labelAngle=45)),
        y=alt.Y("Value:Q", title="Value"),
        color=alt.Color("Series:N", title="Series", legend=alt.Legend(orient="bottom")),
    )
    hover_nearest = alt.selection_point(fields=["YearLabel"], nearest=True, on="mousemove", empty=False)
    net_worth_line = base_net.mark_line()
    net_worth_hover_points = base_net.mark_circle(size=70).transform_filter(hover_nearest).encode(
        tooltip=[
            alt.Tooltip("YearLabel:N", title="Year"),
            alt.Tooltip("Series:N", title="Series"),
            alt.Tooltip("Value:Q", title="Value", format=",.0f"),
        ]
    )
    net_worth_hitbox = base_net.mark_circle(size=140, opacity=0.0).add_params(hover_nearest)
    net_worth_chart = alt.layer(net_worth_line, net_worth_hitbox, net_worth_hover_points)
    left_col.altair_chart(net_worth_chart, use_container_width=True)
else:
    left_col.info("Select at least one net worth series below.")

left_col.caption("Display Series")
net_toggle_col_1, net_toggle_col_2 = left_col.columns(2)
net_toggle_col_1.checkbox("Projected Net Worth", key="show_net_projected")
net_toggle_col_2.checkbox("Liquid Net Worth", key="show_net_liquid")
net_toggle_col_1.checkbox("Housing Equity", key="show_net_housing_equity")
net_toggle_col_2.checkbox("Company Stock Value Held", key="show_net_company_held")
net_toggle_col_1.checkbox("Company Stock (Unvested)", key="show_net_company_non_liquid")
net_toggle_col_2.checkbox("Roth IRA Value", key="show_net_roth_ira")

right_col.subheader("Yearly Cashflow")
if selected_cashflow_series:
    cashflow_chart_df = results_df[["Year"] + selected_cashflow_series].copy()
    cashflow_chart_df["YearLabel"] = cashflow_chart_df["Year"].astype(int).astype(str)
    cashflow_chart_df = cashflow_chart_df.melt(
        id_vars=["Year", "YearLabel"],
        var_name="Series",
        value_name="Value",
    )
    year_order = results_df["Year"].astype(int).astype(str).tolist()
    cashflow_chart = (
        alt.Chart(cashflow_chart_df)
        .mark_bar()
        .encode(
            x=alt.X("YearLabel:N", sort=year_order, axis=alt.Axis(title="Year", labelAngle=45)),
            y=alt.Y("Value:Q", title="Value"),
            color=alt.Color("Series:N", title="Series", legend=alt.Legend(orient="bottom")),
            xOffset="Series:N",
            tooltip=[
                alt.Tooltip("YearLabel:N", title="Year"),
                alt.Tooltip("Series:N", title="Series"),
                alt.Tooltip("Value:Q", title="Value", format=",.0f"),
            ],
        )
    )
    right_col.altair_chart(cashflow_chart, use_container_width=True)
else:
    right_col.info("Select at least one cashflow series below.")

right_col.caption("Display Series")
cf_toggle_col_1, cf_toggle_col_2 = right_col.columns(2)
cf_toggle_col_1.checkbox("Employment Cashflow", key="show_cf_employment")
cf_toggle_col_2.checkbox("Housing Cashflow", key="show_cf_housing")
cf_toggle_col_1.checkbox("Misc Cashflow", key="show_cf_misc")
cf_toggle_col_2.checkbox("ESPP Cashflow", key="show_cf_espp")
cf_toggle_col_1.checkbox("Roth IRA Cashflow", key="show_cf_roth_ira")
cf_toggle_col_2.checkbox("Sold Stock Cashflow", key="show_cf_sold_stock")
cf_toggle_col_1.checkbox("Total Cashflow", key="show_cf_total")

negative_liquid_years = [year for year, value in liquid_net_worth.items() if value < 0.0]
if negative_liquid_years:
    first_negative_year = min(negative_liquid_years)
    worst_liquid_year = min(liquid_net_worth, key=liquid_net_worth.get)
    worst_liquid_value = liquid_net_worth.get(worst_liquid_year, 0.0)
    st.warning(
        f"Liquid net worth goes negative in {first_negative_year}. "
        f"Lowest liquid net worth is \\${worst_liquid_value:,.0f} in {worst_liquid_year}."
    )

st.subheader("Summary")
final_year = int(end_year)
final_projected_value = projected_net_worth.get(final_year, 0.0)
final_liquid_value = liquid_net_worth.get(final_year, 0.0)
final_housing_value = house_equity.get(final_year, 0.0)
final_company_stock_held = company_stock_value_held_by_year.get(final_year, 0.0)
final_roth_value = roth_account_value.get(final_year, 0.0)
final_components_sum = final_liquid_value + final_housing_value + final_company_stock_held + final_roth_value

st.caption("Projected net worth = Liquid net worth + Housing equity + Company stock value held + Roth IRA value")
summary_col_1, summary_col_2, summary_col_3, summary_col_4, summary_col_5 = st.columns(5)
summary_col_1.metric("Projected net worth (final year)", f"${final_projected_value:,.0f}")
summary_col_2.metric("Liquid net worth (final year)", f"${final_liquid_value:,.0f}")
summary_col_3.metric("Housing equity (final year)", f"${final_housing_value:,.0f}")
summary_col_4.metric("Company stock value held (final year)", f"${final_company_stock_held:,.0f}")
summary_col_5.metric("Roth IRA value (final year)", f"${final_roth_value:,.0f}")
st.caption(f"Component sum check: \\${final_components_sum:,.0f}")

start_year_int = int(start_year)
all_years = range(start_year_int, final_year + 1)

with st.expander("Liquid Net Worth Breakdown"):
    cumulative_total_cashflow = sum(total_cashflows.get(year, 0.0) for year in all_years)
    implied_liquid_growth = final_liquid_value - float(initial_net_worth) - cumulative_total_cashflow
    liquid_checksum = float(initial_net_worth) + cumulative_total_cashflow + implied_liquid_growth
    st.write(f"Initial liquid net worth: \\${float(initial_net_worth):,.0f}")
    st.write(f"Cumulative total cashflow ({start_year_int}-{final_year}): \\${cumulative_total_cashflow:,.0f}")
    st.write(f"Implied liquid investment growth: \\${implied_liquid_growth:,.0f}")
    st.write(f"Liquid net worth checksum: \\${liquid_checksum:,.0f}")

with st.expander("Company Stock Value Held Breakdown (Final Year)"):
    final_vested_stock = company_stock_vested.get(final_year, 0.0)
    final_unvested_stock = company_stock_non_liquid.get(final_year, 0.0)
    final_espp_held = 0.0 if sell_company_stock_when_possible else espp_account_value.get(final_year, 0.0)
    vested_held_component = 0.0 if sell_company_stock_when_possible else final_vested_stock
    st.write(f"Vested stock held: \\${vested_held_component:,.0f}")
    st.write(f"Unvested stock held: \\${final_unvested_stock:,.0f}")
    st.write(f"ESPP held as stock: \\${final_espp_held:,.0f}")
    st.write(f"Company stock held (final year): \\${final_company_stock_held:,.0f}")

with st.expander("Roth IRA Value Check (Final Year)"):
    st.write(f"Roth IRA value (final year): \\${final_roth_value:,.0f}")

with st.expander("Housing Equity Value Check (Final Year)"):
    st.write(f"Housing equity (final year): \\${final_housing_value:,.0f}")

with st.expander("Cashflow Checks (All Years)"):
    cumulative_employment_cashflow = sum(employment_cashflows.get(year, 0.0) for year in all_years)
    cumulative_housing_cashflow = sum(housing_cashflows.get(year, 0.0) for year in all_years)
    cumulative_misc_cashflow = sum(misc_cashflows.get(year, 0.0) for year in all_years)
    cumulative_espp_cashflow = sum(espp_cashflows_effective.get(year, 0.0) for year in all_years)
    cumulative_roth_cashflow = sum(roth_cashflows.get(year, 0.0) for year in all_years)
    cumulative_sold_stock_cashflow = sum(sold_stock_cashflows.get(year, 0.0) for year in all_years)
    cumulative_total_cashflow = sum(total_cashflows.get(year, 0.0) for year in all_years)

    cumulative_cashflow_checksum = (
        cumulative_employment_cashflow
        + cumulative_housing_cashflow
        + cumulative_misc_cashflow
        + cumulative_espp_cashflow
        + cumulative_roth_cashflow
        + cumulative_sold_stock_cashflow
    )

    st.write(f"Cumulative employment cashflow ({start_year_int}-{final_year}): ${cumulative_employment_cashflow:,.0f}")
    st.write(f"Cumulative housing cashflow ({start_year_int}-{final_year}): ${cumulative_housing_cashflow:,.0f}")
    st.write(f"Cumulative misc cashflow ({start_year_int}-{final_year}): ${cumulative_misc_cashflow:,.0f}")
    st.write(f"Cumulative ESPP cashflow ({start_year_int}-{final_year}): ${cumulative_espp_cashflow:,.0f}")
    st.write(f"Cumulative Roth IRA cashflow ({start_year_int}-{final_year}): ${cumulative_roth_cashflow:,.0f}")
    st.write(f"Cumulative sold stock cashflow ({start_year_int}-{final_year}): ${cumulative_sold_stock_cashflow:,.0f}")
    st.write(f"Cumulative cashflow checksum: ${cumulative_cashflow_checksum:,.0f}")
    st.write(f"Cumulative total cashflow: ${cumulative_total_cashflow:,.0f}")
    st.write(f"Cashflow checksum delta: ${cumulative_total_cashflow - cumulative_cashflow_checksum:,.0f}")

st.subheader("Projection Table")
st.dataframe(
    results_df.style.format(
        {
            "Employment Cashflow": "${:,.0f}",
            "Housing Cashflow": "${:,.0f}",
            "Misc Cashflow": "${:,.0f}",
            "ESPP Cashflow": "${:,.0f}",
            "Roth IRA Cashflow": "${:,.0f}",
            "Sold Stock Cashflow": "${:,.0f}",
            "Total Cashflow": "${:,.0f}",
            "House Equity": "${:,.0f}",
            "ESPP Account Value": "${:,.0f}",
            "Roth IRA Value": "${:,.0f}",
            "Roth IRA Contribution Used": "${:,.0f}",
            "ESPP Discount Gain": "${:,.0f}",
            "Company Stock Value Held": "${:,.0f}",
            "Company Stock (Vested)": "${:,.0f}",
            "Company Stock (Unvested)": "${:,.0f}",
            "Company Stock Sold When Possible": "${:,.0f}",
            "Liquid Net Worth": "${:,.0f}",
            "Projected Net Worth": "${:,.0f}",
        }
    ),
    use_container_width=True,
)
