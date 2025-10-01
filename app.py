import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Fuel Log Analyzer", layout="wide")

st.title("🔍 Bike Fuel Log Analyzer")

sheet_url = st.text_input("Enter Google Sheets link (view or edit link)", "")

def convert_gsheet_to_csv_url(url: str) -> str:
    # If URL is already export URL, just return
    if "export?format=csv" in url:
        return url
    # Replace /edit#gid= or /edit?usp=... etc.
    if "/edit" in url:
        return url.split("/edit")[0] + "/export?format=csv" + ("&" + url.split("export?format=csv&")[-1] if "gid=" in url else "")
    # If it has gid= but not edit
    if "gid=" in url:
        return url + "/export?format=csv"
    # fallback (might fail)
    return url

def load_data_from_gsheet(url: str) -> pd.DataFrame:
    csv_url = convert_gsheet_to_csv_url(url)
    df = pd.read_csv(csv_url)
    return df

if sheet_url:
    try:
        df = load_data_from_gsheet(sheet_url)
        st.subheader("📋 Raw Data")
        st.dataframe(df)

        # Validate columns
        expected_cols = {"Date", "Odometer", "Fuel_Litres", "Amount_Spent"}
        if not expected_cols.issubset(set(df.columns)):
            st.error(f"Missing required columns. Required: {expected_cols}. Found columns: {df.columns.tolist()}")
        else:
            # Parse date
            df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m", errors="coerce")
            if df["Date"].isna().any():
                st.warning("Some dates failed to parse — ensure Date column is in YYYY-MM format.")

            # Compute Distance
            df["Distance"] = df["Odometer"].diff().fillna(0)

            # Compute Mileage kmpl, avoiding division by zero
            df["Mileage_kmpl"] = df.apply(
                lambda row: round(row["Distance"] / row["Fuel_Litres"], 2) if row["Fuel_Litres"] and row["Fuel_Litres"] != 0 else 0,
                axis=1
            )

            # Month period
            df["Month"] = df["Date"].dt.to_period("M")

            # Monthly summary
            monthly = df.groupby("Month").agg(
                Total_Distance=("Distance", "sum"),
                Total_Fuel_Litres=("Fuel_Litres", "sum"),
                Total_Spent=("Amount_Spent", "sum"),
                Avg_Mileage=("Mileage_kmpl", "mean"),
                Best_Mileage=("Mileage_kmpl", "max"),
                Worst_Mileage=("Mileage_kmpl", "min"),
                Refills=("Fuel_Litres", "count"),
            ).reset_index()

            monthly["Overall_Mileage"] = (monthly["Total_Distance"] / monthly["Total_Fuel"]).round(2)

            st.subheader("📊 Monthly Summary")
            st.dataframe(monthly)

            # Download buttons
            csv_details = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download Detailed Log as CSV",
                data=csv_details,
                file_name="fuel_log_detailed.csv",
                mime="text/csv"
            )

            csv_monthly = monthly.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download Monthly Summary CSV",
                data=csv_monthly,
                file_name="fuel_log_monthly.csv",
                mime="text/csv"
            )

            # Plots
            st.subheader("📈 Mileage Trend")
            fig1, ax1 = plt.subplots()
            ax1.plot(monthly["Month"].astype(str), monthly["Overall_Mileage"], marker="o")
            ax1.set_xlabel("Month")
            ax1.set_ylabel("Mileage (km/l)")
            ax1.set_title("Overall Monthly Mileage")
            ax1.grid(True)
            st.pyplot(fig1)

            st.subheader("💰 Spending Trend")
            fig2, ax2 = plt.subplots()
            ax2.bar(monthly["Month"].astype(str), monthly["Total_Spent"])
            ax2.set_xlabel("Month")
            ax2.set_ylabel("Total Spent (₹)")
            ax2.set_title("Monthly Fuel Spend")
            ax2.grid(True)
            st.pyplot(fig2)

    except Exception as e:
        st.error(f"Failed to load or process data: {e}")

else:
    st.info("Please enter a Google Sheets link above.")
