import pandas as pd

# Load the yield data
df_3mo = pd.read_csv("./data/yield/DGS3MO.csv", parse_dates=["observation_date"])
df_5yr = pd.read_csv("./data/yield/DGS5.csv", parse_dates=["observation_date"])


# Merge on DATE
df_combined = pd.merge(df_3mo, df_5yr, on="observation_date", how="inner")

# Convert to numeric (some entries may be "ND" or empty)
df_combined["DGS3MO"] = pd.to_numeric(df_combined["DGS3MO"], errors="coerce")
df_combined["DGS5"] = pd.to_numeric(df_combined["DGS5"], errors="coerce")

# Drop rows with missing values
df_combined.dropna(inplace=True)

# Compute the spread: short-term minus long-term (can reverse if needed)
df_combined["SPREAD_3MO_5YR"] = df_combined["DGS3MO"] - df_combined["DGS5"]

# Daily and 3-day changes
df_combined["SPREAD_CHANGE_1D"] = df_combined["SPREAD_3MO_5YR"].diff(1)
df_combined["SPREAD_CHANGE_3D"] = df_combined["SPREAD_3MO_5YR"].diff(3)

# Save to CSV
df_combined.to_csv("./data/yield/yield_spread_3mo_5yr.csv", index=False)

print("✅ Saved combined spread file: yield_spread_3mo_5yr.csv")