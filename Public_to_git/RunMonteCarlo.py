"""Run Monte Carlo simulations from a range template CSV and export results."""

import argparse
import csv
import random
from pathlib import Path

from CaseDefaults import default_case_values
from RunCases import _normalize_case, _run_case


def _parse_int(value: object, fallback: int) -> int:
    if value is None or str(value).strip() == "":
        return fallback
    return int(float(str(value).strip()))


def _parse_float(value: object, fallback: float) -> float:
    if value is None or str(value).strip() == "":
        return fallback
    return float(str(value).strip())


def _parse_bool(value: object, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback
    text = str(value).strip().lower()
    if text == "":
        return fallback
    return text in {"1", "true", "yes", "y", "on"}


def _sample_normal_from_range(min_value: float, max_value: float, rng: random.Random) -> float:
    low = min(min_value, max_value)
    high = max(min_value, max_value)
    if high == low:
        return low

    # 95% of a normal distribution lies within approximately mean +/- 1.96 sigma.
    mean = (low + high) / 2.0
    sigma = (high - low) / 3.92
    return rng.normalvariate(mean, sigma)


def _build_sampled_case(
    raw_template: dict[str, object],
    defaults: dict[str, object],
    run_index: int,
    rng: random.Random,
) -> dict[str, object]:
    sampled: dict[str, object] = {}
    template_case_name = str(raw_template.get("case_name", defaults["case_name"])).strip() or str(defaults["case_name"])

    for key, default_value in defaults.items():
        if key == "case_name":
            sampled[key] = f"{template_case_name}_run_{run_index}"
            continue

        if isinstance(default_value, bool):
            sampled[key] = _parse_bool(raw_template.get(key), bool(default_value))
            continue

        if isinstance(default_value, int):
            min_key = f"{key}_min"
            max_key = f"{key}_max"
            sampled_value = _sample_normal_from_range(
                _parse_float(raw_template.get(min_key), float(default_value)),
                _parse_float(raw_template.get(max_key), float(default_value)),
                rng,
            )
            sampled[key] = int(round(sampled_value))
            continue

        if isinstance(default_value, float):
            min_key = f"{key}_min"
            max_key = f"{key}_max"
            sampled[key] = _sample_normal_from_range(
                _parse_float(raw_template.get(min_key), float(default_value)),
                _parse_float(raw_template.get(max_key), float(default_value)),
                rng,
            )
            continue

        sampled[key] = raw_template.get(key, default_value)

    # Ensure model receives at least one projected year.
    sampled["projection_years"] = max(1, int(sampled.get("projection_years", defaults["projection_years"])))
    return sampled


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Monte Carlo simulations from a range CSV template.")
    parser.add_argument("input_csv", help="Input Monte Carlo template CSV.")
    parser.add_argument(
        "--output",
        default="monte_carlo_results.csv",
        help="Output CSV path for Monte Carlo run results (default: monte_carlo_results.csv).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible sampling.",
    )
    args = parser.parse_args()

    input_path = Path(args.input_csv)
    output_path = Path(args.output)
    defaults = default_case_values()
    rng = random.Random(args.seed)

    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    output_rows: list[dict[str, object]] = []
    with input_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for template_idx, raw_template in enumerate(reader, start=1):
            template_case_name = (
                str(raw_template.get("case_name", defaults["case_name"])).strip() or f"template_{template_idx}"
            )
            number_of_runs = max(1, _parse_int(raw_template.get("number_of_runs"), 1000))

            for run_idx in range(1, number_of_runs + 1):
                sampled_case_raw = _build_sampled_case(raw_template, defaults, run_idx, rng)
                normalized_case = _normalize_case(sampled_case_raw, defaults)
                summary = _run_case(normalized_case)

                row: dict[str, object] = {
                    "template_case_name": template_case_name,
                    "run_index": run_idx,
                }
                for key, value in normalized_case.items():
                    row[f"input_{key}"] = value
                row.update(summary)
                output_rows.append(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_rows:
        fieldnames = list(output_rows[0].keys())
    else:
        fieldnames = ["template_case_name", "run_index", "case_name"]

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Processed {len(output_rows)} Monte Carlo run(s). Wrote results to: {output_path}")


if __name__ == "__main__":
    main()
