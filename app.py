import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import datetime, date

# --- הגדרות עיצוב וצבעים ---
st.set_page_config(page_title="Pro Trade Journal", layout="wide")

# הזרקת CSS לעיצוב הממשק
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #3e4259; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #4CAF50; color: white; }
    .trade-card { background-color: #1e2130; padding: 20px; border-radius: 15px; margin-bottom: 10px; border-left: 5px solid #4CAF50; }
    .loss-card { border-left: 5px solid #FF4B4B; }
    h1, h2, h3 { color: #ffffff; }
    </style>
    """, unsafe_allow_status_code=True)

# --- חיבור לגוגל שיטס ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(ttl=0).dropna(how='all')

def save_data(df):
    conn.update(data=df)

try:
    df = load_data()
except:
    df = pd.DataFrame(columns=['ID', 'Ticker', 'Entry_Date', 'Entry_Time', 'Quantity', 'Entry_Price', 'Status', 'Exit_Date', 'Exit_Price', 'Conclusions', 'Profit_USD'])

# --- סרגל צד (Sidebar) מעוצב ---
with st.sidebar:
    st.title("📊 ביצועים")
    initial_balance = st.number_input("הון התחלתי ($)", value=10000.0)
    
    # חישובי רווח/הפסד שבועי וחודשי
    df['Entry_Date_DT'] = pd.to_datetime(df['Entry_Date'])
    today = pd.Timestamp.now()
    
    weekly_df = df[(df['Status'] == 'Closed') & (df['Entry_Date_DT'] >= (today - pd.Timedelta(days=7)))]
    monthly_df = df[(df['Status'] == 'Closed') & (df['Entry_Date_DT'] >= (today - pd.Timedelta(days=30)))]
    
    st.metric("רווח שבועי", f"${weekly_df['Profit_USD'].astype(float).sum():,.2f}", delta_color="normal")
    st.metric("רווח חודשי", f"${monthly_df['Profit_USD'].astype(float).sum():,.2f}")
    
    st.divider()
    st.write("📂 **פירוט עסקאות אחרונות**")
    for _, r in df.tail(5).iterrows():
        color = "🟢" if float(r['Profit_USD']) >= 0 else "🔴"
        st.write(f"{color} {r['Ticker']} | {r['Profit_USD']}$")

# --- גוף האפליקציה ---
st.title("🚀 Pro Trading Dashboard")

tab1, tab2, tab3 = st.tabs(["⚡ פוזיציות פתוחות", "📝 הזנת טרייד", "📈 היסטוריה וגרפים"])

# טאב 2: הזנה
with tab2:
    with st.container():
        st.subheader("פרטי כניסה")
        with st.form("new_trade", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            t = col1.text_input("טיקר (Ticker)").upper()
            q = col2.number_input("כמות", min_value=0.01)
            p = col3.number_input("מחיר כניסה ($)", min_value=0.01)
            
            col4, col5 = st.columns(2)
            d = col4.date_input("תאריך", value=date.today())
            tm = col5.time_input("שעה", value=datetime.now().time())
            
            if st.form_submit_button("פתח פוזיציה"):
                new_row = pd.DataFrame([{
                    'ID': len(df) + 1, 'Ticker': t, 'Entry_Date': str(d),
                    'Entry_Time': str(tm), 'Quantity': q, 'Entry_Price': p,
                    'Status': 'Open', 'Exit_Date': '', 'Exit_Price': 0,
                    'Conclusions': '', 'Profit_USD': 0
                }])
                save_data(pd.concat([df, new_row], ignore_index=True))
                st.rerun()

# טאב 1: פוזיציות פתוחות
with tab1:
    open_trades = df[df['Status'] == 'Open']
    if not open_trades.empty:
        tickers = open_trades['Ticker'].unique().tolist()
        live_prices = yf.download(tickers, period="1d", interval="1m", progress=False)['Close'].iloc[-1]
        
        for idx, row in open_trades.iterrows():
            curr_p = live_prices[row['Ticker']] if len(tickers) > 1 else live_prices
            pnl_usd = (float(curr_p) - float(row['Entry_Price'])) * float(row['Quantity'])
            pnl_pct = (float(curr_p) / float(row['Entry_Price']) - 1) * 100
            
            style_class = "trade-card" if pnl_usd >= 0 else "trade-card loss-card"
            
            st.markdown(f"""
                <div class="{style_class}">
                    <h3>{row['Ticker']} <span style='font-size:15px; color:#aaa;'>({row['Quantity']} מניות)</span></h3>
                    <p>כניסה: ${row['Entry_Price']} | נוכחי: ${curr_p:.2f}</p>
                </div>
                """, unsafe_allow_status_code=True)
            
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("רווח/הפסד $", f"${pnl_usd:.2f}")
            col_m2.metric("רווח/הפסד %", f"{pnl_pct:.2f}%")
            
            with st.popover("✅ סגור טרייד"):
                exit_val = st.number_input("מחיר יציאה סופי", key=f"v_{idx}", value=float(curr_p))
                conc = st.text_area("מסקנות מהטרייד", key=f"c_{idx}")
                if st.button("אשר סגירה", key=f"b_{idx}"):
                    df.at[idx, 'Status'] = 'Closed'
                    df.at[idx, 'Exit_Date'] = str(date.today())
                    df.at[idx, 'Exit_Price'] = exit_val
                    df.at[idx, 'Conclusions'] = conc
                    df.at[idx, 'Profit_USD'] = (exit_val - float(row['Entry_Price'])) * float(row['Quantity'])
                    save_data(df)
                    st.rerun()
    else:
        st.info("אין עסקאות פתוחות כרגע. זמן לצוד הזדמנויות!")

# טאב 3: היסטוריה
with tab3:
    closed = df[df['Status'] == 'Closed'].copy()
    if not closed.empty:
        st.subheader("סיכום ביצועים")
        closed['Account_Curve'] = initial_balance + closed['Profit_USD'].astype(float).cumsum()
        st.line_chart(closed.set_index('Exit_Date')['Account_Curve'])
        
        st.write("📝 **יומן עסקאות מפורט**")
        st.dataframe(closed[['Ticker', 'Entry_Date', 'Exit_Price', 'Profit_USD', 'Conclusions']], use_container_width=True)
                               
