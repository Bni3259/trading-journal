import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, date
import os

# --- הגדרות דף ---
st.set_page_config(page_title="יומן עסקאות אישי", layout="wide")

# --- ניהול קובץ נתונים (CSV מקומי) ---
DB_FILE = "trading_journal.csv"

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        df['Entry_Date'] = pd.to_datetime(df['Entry_Date']).dt.date
        return df
    return pd.DataFrame(columns=['ID', 'Ticker', 'Entry_Date', 'Entry_Time', 'Quantity', 'Entry_Price', 'Status', 'Exit_Date', 'Exit_Price', 'Conclusions', 'Profit_USD'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

if 'journal' not in st.session_state:
    st.session_state.journal = load_data()

# --- סרגל צד ---
st.sidebar.header("💰 ניהול חשבון")
initial_balance = st.sidebar.number_input("הפקדה התחלתית ($)", value=10000.0)

df_all = st.session_state.journal
df_closed = df_all[df_all['Status'] == 'Closed'].copy()

if not df_closed.empty:
    df_closed['Entry_Date'] = pd.to_datetime(df_closed['Entry_Date'])
    today = pd.Timestamp.now()
    weekly = df_closed[df_closed['Entry_Date'] >= (today - timedelta(days=7))]['Profit_USD'].sum()
    monthly = df_closed[df_closed['Entry_Date'] >= (today - timedelta(days=30))]['Profit_USD'].sum()
    st.sidebar.metric("רווח שבועי", f"${weekly:,.2f}")
    st.sidebar.metric("רווח חודשי", f"${monthly:,.2f}")

# --- ממשק ראשי ---
st.title("📈 יומן עסקאות חכם")

tab1, tab2, tab3 = st.tabs(["⚡ פוזיציות פתוחות", "➕ הזנת עסקה", "📊 היסטוריה וגרף"])

with tab2:
    with st.form("new_trade"):
        c1, c2, c3 = st.columns(3)
        t_ticker = c1.text_input("טיקר").upper().strip()
        t_qty = c2.number_input("כמות", min_value=0.01)
        t_price = c3.number_input("מחיר כניסה", min_value=0.01)
        if st.form_submit_button("שמור עסקה", use_container_width=True):
            if t_ticker:
                new_row = pd.DataFrame([{
                    'ID': len(st.session_state.journal) + 1, 'Ticker': t_ticker,
                    'Entry_Date': date.today(), 'Entry_Time': datetime.now().strftime("%H:%M"),
                    'Quantity': t_qty, 'Entry_Price': t_price, 'Status': 'Open',
                    'Exit_Date': '', 'Exit_Price': 0, 'Conclusions': '', 'Profit_USD': 0
                }])
                st.session_state.journal = pd.concat([st.session_state.journal, new_row], ignore_index=True)
                save_data(st.session_state.journal)
                st.success("נשמר!")
                st.rerun()

with tab1:
    open_trades = st.session_state.journal[st.session_state.journal['Status'] == 'Open']
    if not open_trades.empty:
        tickers = open_trades['Ticker'].unique().tolist()
        prices = yf.download(tickers, period="1d", interval="1m", progress=False)['Close'].iloc[-1]
        for idx, row in open_trades.iterrows():
            curr_p = prices[row['Ticker']] if len(tickers) > 1 else prices
            pnl_usd = (curr_p - row['Entry_Price']) * row['Quantity']
            pnl_pct = (curr_p / row['Entry_Price'] - 1) * 100
            with st.container(border=True):
                col_i, col_f = st.columns([3, 2])
                col_i.write(f"**{row['Ticker']}** | כניסה: ${row['Entry_Price']}")
                col_i.metric("P&L בזמן אמת", f"${pnl_usd:.2f}", f"{pnl_pct:.2f}%")
                with col_f.popover("סגור"):
                    exit_p = st.number_input("מחיר יציאה", key=f"ex_{idx}")
                    notes = st.text_area("מסקנות", key=f"no_{idx}")
                    if st.button("אשר", key=f"bt_{idx}"):
                        st.session_state.journal.at[idx, 'Status'] = 'Closed'
                        st.session_state.journal.at[idx, 'Exit_Date'] = date.today()
                        st.session_state.journal.at[idx, 'Exit_Price'] = exit_p
                        st.session_state.journal.at[idx, 'Conclusions'] = notes
                        st.session_state.journal.at[idx, 'Profit_USD'] = (exit_p - row['Entry_Price']) * row['Quantity']
                        save_data(st.session_state.journal)
                        st.rerun()

with tab3:
    if not df_closed.empty:
        df_closed = df_closed.sort_values('Exit_Date')
        df_closed['Equity'] = initial_balance + df_closed['Profit_USD'].cumsum()
        st.line_chart(df_closed.set_index('Exit_Date')['Equity'])
        st.dataframe(df_closed[['Ticker', 'Profit_USD', 'Conclusions']], use_container_width=True)
