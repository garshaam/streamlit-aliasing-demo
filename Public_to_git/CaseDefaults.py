"""Default case schema and values for batch projection CSV workflows."""

from datetime import date


def default_case_values() -> dict[str, object]:
    """Return a dict containing all projection inputs with default values."""
    current_year = date.today().year
    default_purchase_price = 300_000.0
    return {
        "case_name": "default_case",
        "start_year": current_year,
        "projection_years": 30,
        "initial_net_worth": 30_000.0,
        "investment_return_pct": 9.0,
        "salary": 120_000.0,
        "raise_pct": 4.0,
        "annual_bonus": 0.0,
        "effective_tax_rate_pct": 24.0,
        "buy_house": True,
        "purchase_year": current_year,
        "purchase_price": default_purchase_price,
        "down_payment_pct": 10.0,
        "mortgage_rate_pct": 6.0,
        "mortgage_term_years": 30,
        "property_tax_pct": 1.6,
        "home_insurance_pct": 1.4,
        "maintenance_pct": 1.75,
        
        "home_appreciation_pct": 3.5,
        "annual_tenant_rent_income": 8_400.0,
        "tenant_rent_growth_pct": -10.0,
        "annual_rent": default_purchase_price * 0.028,
        "annual_rent_growth_pct": 3.0,
        "annual_living_expenses": 30_000.0,
        "expense_inflation_pct": 8,
        "espp_annual_contribution": 25_000.0,
        "espp_discount_pct": 15.0,
        "roth_ira_contribution": 7000.0,
        "roth_ira_starting_value": 40_000.0,
        "has_company_stock": True,
        "sell_company_stock_when_possible": True,
        "company_stock_grant": 110_000.0,
        "company_stock_vesting_years": 5,
        "company_stock_appreciation_pct": 15.0,
        "company_stock_start_year": current_year,
        "company_stock_cliff_years": 1,
    }
