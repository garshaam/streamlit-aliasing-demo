"""Employment cashflow helpers for the financial projection dashboard."""

# from __future__ import annotations


def generate_employment_cashflows(
    start_year: int,
    end_year: int,
    initial_salary: float,
    annual_raise_pct: float,
    annual_bonus: float = 0.0,
    effective_tax_rate_pct: float = 0.0,
) -> dict[int, float]:
    """Return yearly after-tax employment cashflows keyed by year.

    This is intentionally simple as a placeholder model:
    - Salary compounds annually by ``annual_raise_pct``.
    - Bonus is assumed constant each year.
    - A single effective tax rate is applied to salary + bonus.
    """

    if end_year < start_year:
        return {}

    raise_rate = annual_raise_pct / 100.0
    tax_rate = max(0.0, min(effective_tax_rate_pct / 100.0, 1.0))

    cashflows: dict[int, float] = {}
    for year in range(start_year, end_year + 1):
        year_offset = year - start_year
        salary = initial_salary * ((1.0 + raise_rate) ** year_offset)
        gross_income = salary + annual_bonus
        after_tax_income = gross_income * (1.0 - tax_rate)
        cashflows[year] = after_tax_income

    return cashflows
