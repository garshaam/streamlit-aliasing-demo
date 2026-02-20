"""Export a CSV template containing all projection inputs and default values."""

import argparse
import csv
from pathlib import Path

from CaseDefaults import default_case_values


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a default projection cases CSV.")
    parser.add_argument(
        "--output",
        default="cases_template.csv",
        help="Path for generated CSV template (default: cases_template.csv).",
    )
    args = parser.parse_args()

    defaults = default_case_values()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(defaults.keys()))
        writer.writeheader()
        writer.writerow(defaults)

    print(f"Wrote default cases template to: {output_path}")


if __name__ == "__main__":
    main()
