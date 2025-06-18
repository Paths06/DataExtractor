import os
import pandas as pd
import PyPDF2
import matplotlib.pyplot as plt
import streamlit as st
from io import BytesIO
from difflib import get_close_matches

st.set_page_config(page_title="Fund Data Extractor", layout="wide")
st.title("📊 Fund Performance Data Extractor")

# ---------- 1. Upload Files ----------
uploaded_files = st.file_uploader(
    "Upload PDF or Excel files", type=["pdf", "xlsx"], accept_multiple_files=True
)

# ---------- 2. Fuzzy column matcher ----------
def match_column(possible_names, available_columns):
    for name in possible_names:
        match = get_close_matches(name.lower(), available_columns, n=1, cutoff=0.6)
        if match:
            return match[0]
    return None

# ---------- 3. PDF Parser ----------
def extract_pdf_data(file):
    reader = PyPDF2.PdfReader(file)
    text = "\n".join([page.extract_text() for page in reader.pages])
    lines = text.split("\n")
    data = []
    for line in lines:
        if "|" in line and "Fund Name" not in line and "---" not in line:
            parts = [x.strip() for x in line.split("|")]
            try:
                fund_name = parts[0]
                ret = float(parts[1].replace('%', '')) / 100
                aum = float(parts[2])
                strategy = parts[3]
                data.append({
                    "fund_name": fund_name,
                    "return": ret,
                    "aum": aum,
                    "strategy": strategy
                })
            except Exception as e:
                st.warning(f"Could not parse line: {line} — {e}")
    return pd.DataFrame(data)

# ---------- 4. Excel Parser ----------
def extract_excel_data(file):
    df = pd.read_excel(file)
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    cols = list(df.columns)

    fund_col = match_column(["fund_name", "fund"], cols)
    ret_col = match_column(["weekly_return_(%)", "weekly_return", "return", "performance"], cols)
    aum_col = match_column(["aum", "aum_(m_usd)", "net_assets", "assets"], cols)
    strat_col = match_column(["strategy", "strat", "approach"], cols)

    if not all([fund_col, ret_col, strat_col]):
        raise ValueError(f"Missing required columns: fund={fund_col}, return={ret_col}, strategy={strat_col}")

    df["return"] = df[ret_col].astype(float) / 100
    df["fund_name"] = df[fund_col]
    df["strategy"] = df[strat_col]
    df["aum"] = df[aum_col] if aum_col else None

    return df[["fund_name", "return", "aum", "strategy"]]

# ---------- 5. Main Execution ----------
all_data = []

if uploaded_files:
    for file in uploaded_files:
        try:
            if file.name.endswith(".pdf"):
                df = extract_pdf_data(file)
            elif file.name.endswith(".xlsx"):
                df = extract_excel_data(file)
            else:
                continue
            all_data.append(df)
        except Exception as e:
            st.error(f"Error processing {file.name}: {e}")

# ---------- 6. Visualization ----------
if all_data:
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df["net_return_usd"] = combined_df["return"] * combined_df["aum"]

    st.subheader("🔹 Combined Data Preview")
    st.dataframe(combined_df.tail(10))

    # Average Return by Fund
    st.subheader("📈 Average Return by Fund")
    avg_returns = combined_df.groupby("fund_name")["return"].mean()
    st.bar_chart(avg_returns)

    # AUM by Strategy
    st.subheader("📊 Total AUM by Strategy")
    aum_by_strategy = combined_df.dropna(subset=["aum"]).groupby("strategy")["aum"].sum()
    st.bar_chart(aum_by_strategy)

    # Average Return by Strategy
    st.subheader("📈 Average Return by Strategy")
    avg_ret_by_strategy = combined_df.groupby("strategy")["return"].mean()
    st.bar_chart(avg_ret_by_strategy)

    # Download options
    st.subheader("📤 Download Combined Data")
    excel_buffer = BytesIO()
    combined_df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    st.download_button("Download Excel", excel_buffer, file_name="combined_fund_report.xlsx")
else:
    st.info("Upload PDF or Excel files to extract and visualize data.")
