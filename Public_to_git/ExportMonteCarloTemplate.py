"""Export a Monte Carlo CSV template with min/max numeric ranges."""

import argparse
import csv
from pathlib import Path

from CaseDefaults import default_case_values


def _build_template_row(defaults: dict[str, object]) -> tuple[list[str], dict[str, object]]:
    fieldnames: list[str] = ["case_name", "number_of_runs"]
    row: dict[str, object] = {
        "case_name": str(defaults.get("case_name", "monte_carlo_case")),
        "number_of_runs": 1000,
    }

    for key, value in defaults.items():
        if key == "case_name":
            continue
        if isinstance(value, bool):
            # Booleans are fixed options in this template (no min/max).
            fieldnames.append(key)
            row[key] = value
        elif isinstance(value, (int, float)):
            fieldnames.extend([f"{key}_min", f"{key}_max"])
            row[f"{key}_min"] = value
            row[f"{key}_max"] = value
        else:
            # Non-boolean, non-numeric fields remain fixed options.
            fieldnames.append(key)
            row[key] = value

    return fieldnames, row


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a Monte Carlo input template CSV.")
    parser.add_argument(
        "--output",
        default="monte_carlo_template.csv",
        help="Path for generated Monte Carlo template CSV (default: monte_carlo_template.csv).",
    )
    args = parser.parse_args()

    defaults = default_case_values()
    fieldnames, row = _build_template_row(defaults)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)

    print(f"Wrote Monte Carlo template to: {output_path}")


if __name__ == "__main__":
    main()
