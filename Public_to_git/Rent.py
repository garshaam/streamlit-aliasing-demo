"""Simple rent cashflow helper for the dashboard."""


def generate_rent_cashflows(
    start_year: int,
    end_year: int,
    annual_rent: float,
    annual_rent_growth_pct: float,
) -> dict[int, float]:
    """Return yearly rent cashflows keyed by year.

    Cashflow values are negative costs and rent grows annually.
    """

    if end_year < start_year:
        return {}

    growth_rate = annual_rent_growth_pct / 100.0
    cashflows: dict[int, float] = {}
    for year in range(start_year, end_year + 1):
        year_offset = year - start_year
        rent_for_year = annual_rent * ((1.0 + growth_rate) ** year_offset)
        cashflows[year] = -rent_for_year

    return cashflows
