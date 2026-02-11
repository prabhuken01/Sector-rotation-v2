import pandas as pd

from indicators import calculate_rsi, calculate_adx


def main():
    csv_path = r"C:\Users\Admin\Downloads\NSE_ASHOKLEY, 60.csv"
    df = pd.read_csv(csv_path)

    # Normalize column names
    cols = {c.lower(): c for c in df.columns}
    open_col = cols.get("open")
    high_col = cols.get("high")
    low_col = cols.get("low")
    close_col = cols.get("close")

    price_df = df[[open_col, high_col, low_col, close_col]].copy()
    price_df.columns = ["Open", "High", "Low", "Close"]

    # Compute RSI and ADX using our functions
    rsi_our = calculate_rsi(price_df)
    adx_our, plus_di_our, minus_di_our, di_spread_our = calculate_adx(price_df)

    # Align lengths
    rsi_ref = df["RSI"]
    adx_ref = df["ADX"]

    combined = pd.DataFrame(
        {
            "RSI_ref": rsi_ref,
            "RSI_our": rsi_our,
            "ADX_ref": adx_ref,
            "ADX_our": adx_our,
        }
    )

    # Drop initial NaNs
    combined = combined.dropna()

    print("Rows compared:", len(combined))
    print("RSI mean abs diff:", (combined["RSI_ref"] - combined["RSI_our"]).abs().mean())
    print("RSI max abs diff:", (combined["RSI_ref"] - combined["RSI_our"]).abs().max())
    print("ADX mean abs diff:", (combined["ADX_ref"] - combined["ADX_our"]).abs().mean())
    print("ADX max abs diff:", (combined["ADX_ref"] - combined["ADX_our"]).abs().max())

    # Ignore first 100 rows to focus on steady-state differences
    subset = combined.iloc[100:]
    print("\nSubset (ignoring first 100 rows):")
    print("Rows (subset):", len(subset))
    print(
        "RSI mean abs diff (subset):",
        (subset["RSI_ref"] - subset["RSI_our"]).abs().mean(),
    )
    print(
        "RSI max abs diff (subset):",
        (subset["RSI_ref"] - subset["RSI_our"]).abs().max(),
    )
    print(
        "ADX mean abs diff (subset):",
        (subset["ADX_ref"] - subset["ADX_our"]).abs().mean(),
    )
    print(
        "ADX max abs diff (subset):",
        (subset["ADX_ref"] - subset["ADX_our"]).abs().max(),
    )

    print("\nSample comparison (first 10 rows):")
    print(combined.head(10))


if __name__ == "__main__":
    main()

