"""Miscellaneous recurring cashflow helpers for the dashboard."""

from __future__ import annotations


def generate_misc_cashflows(
    start_year: int,
    end_year: int,
    annual_living_expenses: float,
    expense_inflation_pct: float,
) -> dict[int, float]:
    """Return yearly net miscellaneous cashflows keyed by year.

    Placeholder assumptions:
    - Living expenses inflate annually.
    - Other income and other expenses are constant nominal values.
    """

    if end_year < start_year:
        return {}

    inflation = expense_inflation_pct / 100.0
    cashflows: dict[int, float] = {}
    for year in range(start_year, end_year + 1):
        year_offset = year - start_year
        inflated_expenses = annual_living_expenses * ((1.0 + inflation) ** year_offset)
        cashflows[year] = -inflated_expenses

    return cashflows
