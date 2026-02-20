"""Company stock vesting and valuation helpers for the dashboard."""


def generate_company_stock_positions(
    start_year: int,
    end_year: int,
    initial_grant_value: float,
    vesting_years: int,
    annual_appreciation_pct: float,
    vesting_start_year: int | None = None,
    cliff_years: int = 0,
) -> tuple[dict[int, float], dict[int, float], dict[int, float], dict[int, float]]:
    """Return yearly company stock split into vested, non-liquid, total, and newly vested.

    Assumptions (placeholder):
    - Full grant value is awarded at vesting start year as non-liquid.
    - Price appreciates annually by ``annual_appreciation_pct``.
    - Vesting is linear across ``vesting_years`` after an optional cliff.
    - Newly vested value for a year is priced at that year's stock value.
    """

    if end_year < start_year:
        return {}, {}, {}, {}

    vested_values = {year: 0.0 for year in range(start_year, end_year + 1)}
    non_liquid_values = {year: 0.0 for year in range(start_year, end_year + 1)}
    total_values = {year: 0.0 for year in range(start_year, end_year + 1)}
    newly_vested_values = {year: 0.0 for year in range(start_year, end_year + 1)}
    if initial_grant_value <= 0 or vesting_years <= 0:
        return vested_values, non_liquid_values, total_values, newly_vested_values

    start_vest = start_year if vesting_start_year is None else vesting_start_year
    if start_vest > end_year:
        return vested_values, non_liquid_values, total_values, newly_vested_values

    appreciation = annual_appreciation_pct / 100.0
    cliff = max(0, cliff_years)
    prior_vested_fraction = 0.0

    for year in range(start_year, end_year + 1):
        years_since_grant = year - start_vest
        if years_since_grant < 0 or years_since_grant < cliff:
            vested_fraction = 0.0
        else:
            years_after_cliff = years_since_grant - cliff
            vested_fraction = min(1.0, (years_after_cliff + 1) / vesting_years)

        if years_since_grant < 0:
            current_grant_value = 0.0
        else:
            current_grant_value = initial_grant_value * ((1.0 + appreciation) ** years_since_grant)

        newly_vested_fraction = max(0.0, vested_fraction - prior_vested_fraction)
        vested_value = current_grant_value * vested_fraction
        unvested_value = max(0.0, current_grant_value - vested_value)
        newly_vested_values[year] = current_grant_value * newly_vested_fraction
        vested_values[year] = vested_value
        non_liquid_values[year] = unvested_value
        total_values[year] = current_grant_value
        prior_vested_fraction = vested_fraction

    return vested_values, non_liquid_values, total_values, newly_vested_values
