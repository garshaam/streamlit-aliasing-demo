"""Run projection cases from CSV and export final-year summary metrics."""

import argparse
import csv
from pathlib import Path

from CaseDefaults import default_case_values
from CompanyStock import generate_company_stock_positions
from Employment import generate_employment_cashflows
from House import generate_house_cashflows
from Miscellaneous import generate_misc_cashflows
from PretaxOutflow import generate_espp_positions, generate_roth_ira_positions
from Rent import generate_rent_cashflows


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "on"}


def _parse_int(value: object, fallback: int) -> int:
    if value is None or str(value).strip() == "":
        return fallback
    return int(float(str(value).strip()))


def _parse_float(value: object, fallback: float) -> float:
    if value is None or str(value).strip() == "":
        return fallback
    return float(str(value).strip())


def _sum_cashflows(start_year: int, end_year: int, *cashflow_sets: dict[int, float]) -> dict[int, float]:
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


def _normalize_case(raw_case: dict[str, object], defaults: dict[str, object]) -> dict[str, object]:
    normalized: dict[str, object] = {}
    normalized["case_name"] = str(raw_case.get("case_name", defaults["case_name"])).strip() or str(defaults["case_name"])

    int_fields = [
        "start_year",
        "projection_years",
        "purchase_year",
        "mortgage_term_years",
        "company_stock_vesting_years",
        "company_stock_start_year",
        "company_stock_cliff_years",
    ]
    float_fields = [
        "initial_net_worth",
        "investment_return_pct",
        "salary",
        "raise_pct",
        "annual_bonus",
        "effective_tax_rate_pct",
        "purchase_price",
        "down_payment_pct",
        "mortgage_rate_pct",
        "property_tax_pct",
        "home_insurance_pct",
        "maintenance_pct",
        "home_appreciation_pct",
        "annual_tenant_rent_income",
        "tenant_rent_growth_pct",
        "annual_rent",
        "annual_rent_growth_pct",
        "annual_living_expenses",
        "expense_inflation_pct",
        "espp_annual_contribution",
        "espp_discount_pct",
        "roth_ira_contribution",
        "roth_ira_starting_value",
        "company_stock_grant",
        "company_stock_appreciation_pct",
    ]
    bool_fields = [
        "buy_house",
        "has_company_stock",
        "sell_company_stock_when_possible",
    ]

    for field in int_fields:
        normalized[field] = _parse_int(raw_case.get(field), int(defaults[field]))
    for field in float_fields:
        normalized[field] = _parse_float(raw_case.get(field), float(defaults[field]))
    for field in bool_fields:
        normalized[field] = _parse_bool(raw_case.get(field) if field in raw_case else defaults[field])

    # Backward compatibility for older case files that used sell_company_stock_on_vest.
    if "sell_company_stock_when_possible" not in raw_case and "sell_company_stock_on_vest" in raw_case:
        normalized["sell_company_stock_when_possible"] = _parse_bool(raw_case.get("sell_company_stock_on_vest"))

    return normalized


def _run_case(case: dict[str, object]) -> dict[str, object]:
    start_year = int(case["start_year"])
    projection_years = int(case["projection_years"])
    end_year = start_year + projection_years - 1

    employment_cashflows = generate_employment_cashflows(
        start_year,
        end_year,
        float(case["salary"]),
        float(case["raise_pct"]),
        float(case["annual_bonus"]),
        float(case["effective_tax_rate_pct"]),
    )

    if bool(case["buy_house"]):
        housing_cashflows, house_equity = generate_house_cashflows(
            start_year,
            end_year,
            int(case["purchase_year"]),
            float(case["purchase_price"]),
            float(case["down_payment_pct"]),
            float(case["mortgage_rate_pct"]),
            int(case["mortgage_term_years"]),
            float(case["property_tax_pct"]),
            float(case["home_insurance_pct"]),
            float(case["maintenance_pct"]),
            float(case["home_appreciation_pct"]),
            float(case["annual_tenant_rent_income"]),
            float(case["tenant_rent_growth_pct"]),
        )
    else:
        housing_cashflows = generate_rent_cashflows(
            start_year,
            end_year,
            float(case["annual_rent"]),
            float(case["annual_rent_growth_pct"]),
        )
        house_equity = {year: 0.0 for year in range(start_year, end_year + 1)}

    misc_cashflows = generate_misc_cashflows(
        start_year,
        end_year,
        float(case["annual_living_expenses"]),
        float(case["expense_inflation_pct"]),
    )

    espp_cashflows, espp_account_value, _espp_discount_gains = generate_espp_positions(
        start_year,
        end_year,
        float(case["espp_annual_contribution"]),
        float(case["espp_discount_pct"]),
        # If selling when possible, ESPP behaves like liquid proceeds; otherwise it tracks company stock.
        float(case["investment_return_pct"])
        if bool(case["sell_company_stock_when_possible"])
        else float(case["company_stock_appreciation_pct"]),
    )

    if bool(case["sell_company_stock_when_possible"]):
        espp_cashflows_effective = {
            year: float(case["espp_annual_contribution"]) * (float(case["espp_discount_pct"]) / 100.0)
            for year in range(start_year, end_year + 1)
        }
    else:
        espp_cashflows_effective = espp_cashflows

    if bool(case["has_company_stock"]):
        (
            company_stock_vested,
            company_stock_non_liquid,
            company_stock_total,
            company_stock_newly_vested,
        ) = generate_company_stock_positions(
            start_year,
            end_year,
            float(case["company_stock_grant"]),
            int(case["company_stock_vesting_years"]),
            float(case["company_stock_appreciation_pct"]),
            int(case["company_stock_start_year"]),
            int(case["company_stock_cliff_years"]),
        )
    else:
        company_stock_vested = {year: 0.0 for year in range(start_year, end_year + 1)}
        company_stock_non_liquid = {year: 0.0 for year in range(start_year, end_year + 1)}
        company_stock_total = {year: 0.0 for year in range(start_year, end_year + 1)}
        company_stock_newly_vested = {year: 0.0 for year in range(start_year, end_year + 1)}

    sold_stock_cashflows = {
        year: company_stock_newly_vested.get(year, 0.0) if bool(case["sell_company_stock_when_possible"]) else 0.0
        for year in range(start_year, end_year + 1)
    }

    # Roth phase-out income includes salary, bonus, and newly vested company stock.
    roth_phaseout_income = _add_income_components(
        start_year,
        end_year,
        _employment_gross_income_by_year(
            start_year,
            end_year,
            float(case["salary"]),
            float(case["raise_pct"]),
            float(case["annual_bonus"]),
        ),
        company_stock_newly_vested,
    )

    roth_cashflows, roth_account_value, roth_contribution_used = generate_roth_ira_positions(
        start_year,
        end_year,
        float(case["roth_ira_contribution"]),
        float(case["investment_return_pct"]),
        max_annual_contribution=7000.0,
        starting_account_value=float(case["roth_ira_starting_value"]),
        annual_income_by_year=roth_phaseout_income,
        phaseout_start_income=146000.0,
        phaseout_end_income=161000.0,
    )

    total_cashflows = _sum_cashflows(
        start_year,
        end_year,
        employment_cashflows,
        housing_cashflows,
        misc_cashflows,
        espp_cashflows_effective,
        roth_cashflows,
        sold_stock_cashflows,
    )

    liquid_value = float(case["initial_net_worth"])
    liquid_return = float(case["investment_return_pct"]) / 100.0
    liquid_net_worth = {}
    projected_net_worth = {}

    for year in range(start_year, end_year + 1):
        liquid_value = (liquid_value * (1.0 + liquid_return)) + total_cashflows[year]
        if bool(case["sell_company_stock_when_possible"]):
            # When selling is enabled, ESPP is treated as sold immediately.
            # Net liquid impact is modeled via cashflow (discount gain), so avoid double counting.
            liquid_net_worth[year] = liquid_value
            espp_value_in_net_worth = 0.0
        else:
            # When selling is disabled, ESPP remains invested as company-stock-like holdings.
            liquid_net_worth[year] = liquid_value
            espp_value_in_net_worth = espp_account_value[year]

        if bool(case["sell_company_stock_when_possible"]):
            stock_value_in_net_worth = company_stock_non_liquid[year]
        else:
            stock_value_in_net_worth = company_stock_total[year]

        projected_net_worth[year] = (
            liquid_net_worth[year]
            + house_equity[year]
            + stock_value_in_net_worth
            + espp_value_in_net_worth
            + roth_account_value[year]
        )

    return {
        "case_name": case["case_name"],
        "start_year": start_year,
        "final_year": end_year,
        "buy_house": bool(case["buy_house"]),
        "has_company_stock": bool(case["has_company_stock"]),
        "sell_company_stock_when_possible": bool(case["sell_company_stock_when_possible"]),
        "projected_net_worth_final": projected_net_worth[end_year],
        "liquid_net_worth_final": liquid_net_worth[end_year],
        "housing_equity_final": house_equity[end_year],
        "company_stock_value_final": (
            company_stock_non_liquid[end_year]
            if bool(case["sell_company_stock_when_possible"])
            else (company_stock_total[end_year] + espp_account_value[end_year])
        ),
        "company_stock_total_final": company_stock_total[end_year],
        "company_stock_non_liquid_final": company_stock_non_liquid[end_year],
        "company_stock_vested_final": company_stock_vested[end_year],
        "company_stock_sold_when_possible_final": company_stock_newly_vested[end_year] if bool(case["sell_company_stock_when_possible"]) else 0.0,
        "espp_account_value_final": 0.0 if bool(case["sell_company_stock_when_possible"]) else espp_account_value[end_year],
        "roth_ira_value_final": roth_account_value[end_year],
        "roth_ira_contribution_used_final": roth_contribution_used[end_year],
        "employment_cashflow_final": employment_cashflows[end_year],
        "housing_cashflow_final": housing_cashflows[end_year],
        "misc_cashflow_final": misc_cashflows[end_year],
        "espp_cashflow_final": espp_cashflows_effective[end_year],
        "sold_stock_cashflow_final": sold_stock_cashflows[end_year],
        "roth_ira_cashflow_final": roth_cashflows[end_year],
        "total_cashflow_final": total_cashflows[end_year],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run projection cases from CSV and write final-year summaries.")
    parser.add_argument("input_csv", help="Input CSV file containing one case per row.")
    parser.add_argument(
        "--output",
        default="case_results.csv",
        help="Output CSV path for final-year summary metrics (default: case_results.csv).",
    )
    args = parser.parse_args()

    input_path = Path(args.input_csv)
    output_path = Path(args.output)
    defaults = default_case_values()

    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    summaries: list[dict[str, object]] = []
    with input_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row_index, raw_case in enumerate(reader, start=1):
            normalized_case = _normalize_case(raw_case, defaults)
            if not str(normalized_case["case_name"]).strip():
                normalized_case["case_name"] = f"case_{row_index}"
            summaries.append(_run_case(normalized_case))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if summaries:
        fieldnames = list(summaries[0].keys())
    else:
        fieldnames = [
            "case_name",
            "start_year",
            "final_year",
            "projected_net_worth_final",
            "liquid_net_worth_final",
        ]

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summaries)

    print(f"Processed {len(summaries)} case(s). Wrote results to: {output_path}")


if __name__ == "__main__":
    main()
