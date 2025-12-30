import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import datetime, date

# --- הגדרות דף ועיצוב Elite ---
st.set_page_config(page_title="Pro Trading Journal", layout="wide", initial_sidebar_state="collapsed")

# הסתרת ממשק GitHub ועיצוב כרטיסיות
st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {visibility: hidden;}
    .main { background-color: #050505; color: #e0e0e0; }
    .trade-card {
        background: #111; border: 1px solid #222; border-radius: 12px;
        padding: 15px; margin-bottom: 10px; border-right: 5px solid #4caf50;
    }
    .loss-card { border-right: 5px solid #ff3366; }
    </style>
    """, unsafe_allow_html=True)

# --- חיבור נתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(ttl=0)
    if df is not None:
        df = df.dropna(how='all')
        # מניעת TypeError: הפיכת כל עמודות החישוב למספרים באופן כפוי
        for col in ['Quantity', 'Entry_Price', 'Exit_Price', 'Profit_USD']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    return pd.DataFrame()

try:
    df_journal = load_data()
except:
    df_journal = pd.DataFrame()

# --- ממשק ---
st.markdown("<h1>Trading <span style='color:#4caf50;'>Pro</span></h1>", unsafe_allow_html=True)
tab1, tab2 = st.tabs(["⚡ פוזיציות פעילות", "➕ הוספת טרייד"])

with tab2:
    with st.form("new_trade", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        tic = col1.text_input("טיקר").upper().strip()
        qty = col2.number_input("כמות", min_value=0.0, format="%.2f")
        pri = col3.number_input("מחיר כניסה", min_value=0.0, format="%.2f")
        if st.form_submit_button("פתח פוזיציה"):
            if tic and qty > 0:
                new_row = pd.DataFrame([{
                    'ID': len(df_journal) + 1, 'Ticker': tic, 'Entry_Date': str(date.today()),
                    'Entry_Time': datetime.now().strftime("%H:%M"), 'Quantity': qty,
                    'Entry_Price': pri, 'Status': 'Open', 'Exit_Date': '', 'Exit_Price': 0.0,
                    'Conclusions': '', 'Profit_USD': 0.0
                }])
                conn.update(data=pd.concat([df_journal, new_row], ignore_index=True))
                st.success("נשמר!")
                st.rerun()

with tab1:
    if not df_journal.empty and 'Status' in df_journal.columns:
        open_trades = df_journal[df_journal['Status'] == 'Open']
        if not open_trades.empty:
            tickers = open_trades['Ticker'].unique().tolist()
            try:
                live_data = yf.download(tickers, period="1d", interval="1m", progress=False)['Close']
                for idx, row in open_trades.iterrows():
                    cp = live_data[row['Ticker']].iloc[-1] if len(tickers) > 1 else live_data.iloc[-1]
                    # חישוב זהיר
                    pnl = (float(cp) - float(row['Entry_Price'])) * float(row['Quantity'])
                    color = "#00ff88" if pnl >= 0 else "#ff3366"
                    card_style = "trade-card" if pnl >= 0 else "trade-card loss-card"
                    
                    st.markdown(f"""<div class='{card_style}'>
                        <h3>{row['Ticker']} <span style='float:right; color:{color};'>${pnl:+,.2f}</span></h3>
                        <p style='margin:0; color:#888;'>כניסה: ${row['Entry_Price']:.2f} | נוכחי: ${float(cp):.2f}</p>
                    </div>""", unsafe_allow_html=True)
                    
                    if st.button(f"סגור {row['Ticker']}", key=idx):
                        df_journal.at[idx, 'Status'] = 'Closed'
                        df_journal.at[idx, 'Exit_Date'] = str(date.today())
                        df_journal.at[idx, 'Exit_Price'] = float(cp)
                        df_journal.at[idx, 'Profit_USD'] = pnl
                        conn.update(data=df_journal)
                        st.rerun()
            except: st.warning("ממתין לנתוני בורסה...")
        else: st.info("אין עסקאות פתוחות.")
    else: st.info("הגיליון ריק. הוסף עסקה בטאב השני.")
