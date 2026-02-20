"""Streamlit dashboard for visualizing Monte Carlo result distributions."""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for name in candidates:
        if name in df.columns:
            return name
    return None


def _histogram(data: pd.DataFrame, column: str, title: str, bin_spec: alt.Bin) -> alt.Chart:
    return (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=alt.X(f"{column}:Q", bin=bin_spec, title=title),
            y=alt.Y("count():Q", title="Runs"),
            tooltip=[
                alt.Tooltip("count():Q", title="Runs"),
            ],
        )
        .properties(title=title)
    )


def main() -> None:
    st.set_page_config(page_title="Monte Carlo Results Dashboard", page_icon="$", layout="wide")
    st.title("Monte Carlo Results Dashboard")
    st.write("Load a Monte Carlo results CSV and visualize final net worth distributions.")

    with st.sidebar:
        st.header("Data Source")
        uploaded_file = st.file_uploader("Upload Monte Carlo results CSV", type=["csv"])
        csv_path = st.text_input("...or CSV file path", value="monte_carlo_results.csv")
        bins = st.slider("Histogram bins", min_value=10, max_value=120, value=40, step=5)

    df: pd.DataFrame | None = None
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
    elif csv_path.strip():
        path = Path(csv_path.strip())
        if path.exists():
            df = pd.read_csv(path)
        else:
            st.info(f"CSV not found at: {path}")
            return
    else:
        st.info("Upload a CSV or provide a file path.")
        return

    projected_col = _find_column(
        df,
        ["projected_net_worth_final", "Projected net worth (final year)", "projected_net_worth"],
    )
    liquid_col = _find_column(
        df,
        ["liquid_net_worth_final", "Liquid net worth (final year)", "liquid_net_worth"],
    )

    missing = []
    if projected_col is None:
        missing.append("projected_net_worth_final")
    if liquid_col is None:
        missing.append("liquid_net_worth_final")

    if missing:
        st.error(
            "Missing required columns: "
            + ", ".join(missing)
            + ".\n\nAvailable columns:\n"
            + ", ".join(df.columns.astype(str))
        )
        return

    plot_df = df.copy()
    plot_df[projected_col] = pd.to_numeric(plot_df[projected_col], errors="coerce")
    plot_df[liquid_col] = pd.to_numeric(plot_df[liquid_col], errors="coerce")
    plot_df = plot_df.dropna(subset=[projected_col, liquid_col])

    if plot_df.empty:
        st.error("No numeric rows available for projected/liquid net worth columns.")
        return

    bin_spec = alt.Bin(maxbins=bins)

    col1, col2 = st.columns(2)
    with col1:
        st.altair_chart(
            _histogram(plot_df, projected_col, "Projected Net Worth (Final Year)", bin_spec),
            use_container_width=True,
        )
        st.caption(
            f"Mean: ${plot_df[projected_col].mean():,.0f} | "
            f"Median: ${plot_df[projected_col].median():,.0f}"
        )

    with col2:
        st.altair_chart(
            _histogram(plot_df, liquid_col, "Liquid Net Worth (Final Year)", bin_spec),
            use_container_width=True,
        )
        st.caption(
            f"Mean: ${plot_df[liquid_col].mean():,.0f} | "
            f"Median: ${plot_df[liquid_col].median():,.0f}"
        )

    st.caption(f"Rows used: {len(plot_df):,}")


if __name__ == "__main__":
    main()
