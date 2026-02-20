"""Helpers for modeling outflows from liquid cash into long-term accounts."""


def generate_espp_positions(
    start_year: int,
    end_year: int,
    annual_contribution: float,
    discount_pct: float,
    annual_growth_pct: float,
) -> tuple[dict[int, float], dict[int, float], dict[int, float]]:
    """Return ESPP yearly cashflows, account value, and discount gain.

    - Cashflow is negative (contribution from liquid assets).
    - Contribution buys company stock at a discount.
    - Account value grows by ``annual_growth_pct`` each year.
    """

    if end_year < start_year:
        return {}, {}, {}

    contribution = max(0.0, annual_contribution)
    growth_rate = annual_growth_pct / 100.0
    discount_rate = max(0.0, min(discount_pct / 100.0, 0.99))

    cashflows = {year: 0.0 for year in range(start_year, end_year + 1)}
    account_values = {year: 0.0 for year in range(start_year, end_year + 1)}
    discount_gains = {year: 0.0 for year in range(start_year, end_year + 1)}

    account_value = 0.0
    for year in range(start_year, end_year + 1):
        account_value *= 1.0 + growth_rate
        purchased_market_value = contribution / (1.0 - discount_rate) if contribution > 0 else 0.0
        discount_gain = max(0.0, purchased_market_value - contribution)
        account_value += purchased_market_value

        cashflows[year] = -contribution
        account_values[year] = account_value
        discount_gains[year] = discount_gain

    return cashflows, account_values, discount_gains


def generate_roth_ira_positions(
    start_year: int,
    end_year: int,
    annual_contribution: float,
    annual_growth_pct: float,
    max_annual_contribution: float = 7000.0,
    starting_account_value: float = 0.0,
    annual_income_by_year: dict[int, float] | None = None,
    phaseout_start_income: float = 146000.0,
    phaseout_end_income: float = 161000.0,
) -> tuple[dict[int, float], dict[int, float], dict[int, float]]:
    """Return Roth IRA yearly cashflows, account value, and actual contribution.

    - Contribution is capped by ``max_annual_contribution``.
    - Contribution is phase-out adjusted using annual income.
    - Existing IRA balance starts at ``starting_account_value``.
    - Cashflow is negative (contribution from liquid assets).
    - Account value grows by ``annual_growth_pct`` each year.
    """

    if end_year < start_year:
        return {}, {}, {}

    growth_rate = annual_growth_pct / 100.0
    contribution_cap = max(0.0, max_annual_contribution)
    requested_contribution = max(0.0, annual_contribution)
    cashflows = {year: 0.0 for year in range(start_year, end_year + 1)}
    account_values = {year: 0.0 for year in range(start_year, end_year + 1)}
    contributions = {year: 0.0 for year in range(start_year, end_year + 1)}

    account_value = max(0.0, starting_account_value)
    for year in range(start_year, end_year + 1):
        income = annual_income_by_year.get(year, 0.0) if annual_income_by_year is not None else 0.0
        phaseout_factor = _roth_phaseout_factor(income, phaseout_start_income, phaseout_end_income)
        actual_contribution = min(requested_contribution, contribution_cap) * phaseout_factor

        account_value *= 1.0 + growth_rate
        account_value += actual_contribution

        cashflows[year] = -actual_contribution
        account_values[year] = account_value
        contributions[year] = actual_contribution

    return cashflows, account_values, contributions


def _roth_phaseout_factor(income: float, phaseout_start_income: float, phaseout_end_income: float) -> float:
    """Return Roth contribution multiplier based on income phase-out range."""
    if phaseout_end_income <= phaseout_start_income:
        return 1.0
    if income <= phaseout_start_income:
        return 1.0
    if income >= phaseout_end_income:
        return 0.0
    return (phaseout_end_income - income) / (phaseout_end_income - phaseout_start_income)
