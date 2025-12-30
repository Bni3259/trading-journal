import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import datetime, date

# --- הגדרות דף ועיצוב יוקרתי ---
st.set_page_config(page_title="Elite Trade Journal", layout="wide", initial_sidebar_state="collapsed")

# הזרקת CSS להסתרת כל הממשק של GitHub/Streamlit ועיצוב כרטיסיות
st.markdown("""
    <style>
    /* הסתרת סרגלים ואייקונים של GitHub/Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* עיצוב רקע וכרטיסיות */
    .main { background-color: #050505; color: #e0e0e0; }
    .trade-card {
        background: linear-gradient(145deg, #111111, #1a1a1a);
        border: 1px solid #222;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 15px;
        border-right: 6px solid #4CAF50;
    }
    .loss-card { border-right: 6px solid #FF3366; }
    </style>
    """, unsafe_allow_html=True)

# --- חיבור נתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(ttl=0)
    if df is not None:
        df = df.dropna(how='all')
        # וידוא שכל עמודות המספרים הן אכן מספרים למניעת TypeError
        for col in ['Quantity', 'Entry_Price', 'Exit_Price', 'Profit_USD']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

try:
    df = load_data()
except:
    df = pd.DataFrame(columns=['ID', 'Ticker', 'Entry_Date', 'Entry_Time', 'Quantity', 'Entry_Price', 'Status', 'Exit_Date', 'Exit_Price', 'Conclusions', 'Profit_USD'])

# --- ממשק האפליקציה ---
st.markdown("<h1 style='color:#4CAF50;'>Trading <span style='color:white;'>PRO</span></h1>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["⚡ פוזיציות פעילות", "➕ פתיחת טרייד", "📊 היסטוריה"])

# טאב פתיחת טרייד
with tab2:
    with st.form("new_trade", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        tic = c1.text_input("טיקר").upper().strip()
        qty = c2.number_input("כמות", min_value=0.0, step=0.01)
        pri = c3.number_input("מחיר כניסה", min_value=0.0, step=0.01)
        if st.form_submit_button("בצע כניסה"):
            if tic and qty > 0:
                new_row = pd.DataFrame([{
                    'ID': len(df) + 1, 'Ticker': tic, 'Entry_Date': str(date.today()),
                    'Entry_Time': datetime.now().strftime("%H:%M"), 'Quantity': qty,
                    'Entry_Price': pri, 'Status': 'Open', 'Exit_Date': '', 'Exit_Price': 0,
                    'Conclusions': '', 'Profit_USD': 0
                }])
                conn.update(data=pd.concat([df, new_row], ignore_index=True))
                st.success("הטרייד נרשם בהצלחה!")
                st.rerun()

# טאב פוזיציות פעילות
with tab1:
    open_trades = df[df['Status'] == 'Open']
    if not open_trades.empty:
        tickers = open_trades['Ticker'].unique().tolist()
        try:
            live_data = yf.download(tickers, period="1d", interval="1m", progress=False)['Close']
            last_price = live_data.iloc[-1]
            
            for idx, row in open_trades.iterrows():
                cp = last_price[row['Ticker']] if len(tickers) > 1 else last_price
                # חישוב זהיר של רווח/הפסד
                pnl = (float(cp) - float(row['Entry_Price'])) * float(row['Quantity'])
                pct = (float(cp) / float(row['Entry_Price']) - 1) * 100 if row['Entry_Price'] != 0 else 0
                
                card_class = "trade-card" if pnl >= 0 else "trade-card loss-card"
                color = "#00ff88" if pnl >= 0 else "#ff3366"
                
                st.markdown(f"""
                    <div class="{card_class}">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-size:24px; font-weight:bold;">{row['Ticker']}</span>
                            <span style="color:{color}; font-size:20px; font-weight:bold;">{pct:+.2f}%</span>
                        </div>
                        <p style="margin:5px 0; color:#888;">Entry: ${row['Entry_Price']:.2f} | Live: ${cp:.2f}</p>
                        <h2 style="margin:0; color:{color};">${pnl:+,.2f}</h2>
                    </div>
                """, unsafe_allow_html=True)
                
                with st.expander("סגירת פוזיציה"):
                    ex_p = st.number_input("מחיר סגירה", key=f"e_{idx}", value=float(cp))
                    notes = st.text_area("מסקנות", key=f"n_{idx}")
                    if st.button("אשר סגירה סופית", key=f"b_{idx}"):
                        df.at[idx, 'Status'] = 'Closed'
                        df.at[idx, 'Exit_Date'] = str(date.today())
                        df.at[idx, 'Exit_Price'] = ex_p
                        df.at[idx, 'Conclusions'] = notes
                        df.at[idx, 'Profit_USD'] = (ex_p - float(row['Entry_Price'])) * float(row['Quantity'])
                        conn.update(data=df)
                        st.rerun()
        except Exception:
            st.warning("מתחבר לנתוני בורסה...")
    else:
        st.info("אין פוזיציות פתוחות כרגע.")

with tab3:
    st.dataframe(df[df['Status'] == 'Closed'], use_container_width=True)
