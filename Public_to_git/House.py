"""House cashflow and equity placeholder model for the dashboard."""

# from __future__ import annotations


def generate_house_cashflows(
    start_year: int,
    end_year: int,
    purchase_year: int | None,
    purchase_price: float,
    down_payment_pct: float,
    mortgage_rate_pct: float,
    mortgage_term_years: int,
    property_tax_pct: float,
    home_insurance_pct: float,
    maintenance_pct: float,
    home_appreciation_pct: float,
    annual_tenant_rent_income: float = 0.0,
    tenant_rent_growth_pct: float = 0.0,
) -> tuple[dict[int, float], dict[int, float]]:
    """Return yearly house cashflows and home equity keyed by year.

    Cashflow values are negative costs.
    Tenant rent income offsets yearly housing costs.
    Equity is estimated as current home value minus remaining mortgage balance.
    """

    years = range(start_year, end_year + 1)
    cashflows = {year: 0.0 for year in years}
    equity = {year: 0.0 for year in years}

    if purchase_year is None or purchase_year > end_year or purchase_year < start_year:
        return cashflows, equity

    home_value_growth = home_appreciation_pct / 100.0
    maintenance_rate = maintenance_pct / 100.0
    property_tax_rate = property_tax_pct / 100.0
    home_insurance_rate = home_insurance_pct / 100.0
    annual_mortgage_rate = mortgage_rate_pct / 100.0
    tenant_rent_growth_rate = tenant_rent_growth_pct / 100.0
    down_payment = purchase_price * max(0.0, min(down_payment_pct / 100.0, 1.0))
    principal = max(0.0, purchase_price - down_payment)

    total_months = max(0, mortgage_term_years * 12)
    monthly_rate = annual_mortgage_rate / 12.0
    monthly_payment = _monthly_payment(principal, monthly_rate, total_months)

    remaining_balance = principal
    paid_months = 0

    for year in range(purchase_year, end_year + 1):
        age = year - purchase_year
        home_value = purchase_price * ((1.0 + home_value_growth) ** age)

        yearly_mortgage_paid = 0.0
        for _ in range(12):
            if paid_months >= total_months or remaining_balance <= 0:
                break

            interest = remaining_balance * monthly_rate
            principal_component = monthly_payment - interest
            if principal_component > remaining_balance:
                principal_component = remaining_balance
                monthly_cash = interest + principal_component
            else:
                monthly_cash = monthly_payment

            remaining_balance -= principal_component
            yearly_mortgage_paid += monthly_cash
            paid_months += 1

        property_tax = home_value * property_tax_rate
        home_insurance = home_value * home_insurance_rate
        maintenance = home_value * maintenance_rate
        tenant_rent_income = annual_tenant_rent_income * ((1.0 + tenant_rent_growth_rate) ** age)

        year_cashflow = -(yearly_mortgage_paid + property_tax + home_insurance + maintenance) + tenant_rent_income
        if year == purchase_year:
            year_cashflow -= down_payment
        cashflows[year] = year_cashflow
        equity[year] = max(0.0, home_value - remaining_balance)

    return cashflows, equity


def _monthly_payment(principal: float, monthly_rate: float, total_months: int) -> float:
    """Compute fixed monthly mortgage payment."""
    if principal <= 0 or total_months <= 0:
        return 0.0
    if monthly_rate == 0:
        return principal / total_months

    factor = (1 + monthly_rate) ** total_months
    return principal * (monthly_rate * factor) / (factor - 1)
