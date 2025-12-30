import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import datetime, date

# --- הגדרות דף ועיצוב אגרסיבי ---
st.set_page_config(page_title="Elite Trade Journal", layout="wide", initial_sidebar_state="collapsed")

# הזרקת CSS מטורף לעיצוב אפליקציה אמיתית
st.markdown("""
    <style>
    /* הסתרת אלמנטים של Streamlit ו-GitHub */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* עיצוב כללי - Dark Mode Fintech */
    .main { background-color: #050505; color: #e0e0e0; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #0a0a0a; border-right: 1px solid #1e1e1e; }
    
    /* כרטיסיות טריידים */
    .trade-card {
        background: linear-gradient(145deg, #111111, #1a1a1a);
        border: 1px solid #222;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    .profit-border { border-right: 6px solid #00ff88; }
    .loss-border { border-right: 6px solid #ff3366; }
    
    /* כותרות וטקסט */
    h1, h2, h3 { font-weight: 700; letter-spacing: -0.5px; }
    .metric-label { color: #888; font-size: 14px; text-transform: uppercase; }
    .metric-value { font-size: 24px; font-weight: bold; color: #fff; }
    
    /* כפתורים */
    .stButton>button {
        background: linear-gradient(90deg, #2e7d32, #4caf50);
        color: white; border: none; border-radius: 8px; font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(76,175,80,0.4); }
    </style>
    """, unsafe_allow_html=True)

# --- חיבור נתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(ttl=0).dropna(how='all')

def save_data(df):
    conn.update(data=df)

try:
    df = load_data()
except:
    df = pd.DataFrame(columns=['ID', 'Ticker', 'Entry_Date', 'Entry_Time', 'Quantity', 'Entry_Price', 'Status', 'Exit_Date', 'Exit_Price', 'Conclusions', 'Profit_USD'])

# --- סרגל צד מעוצב ---
with st.sidebar:
    st.markdown("<h2 style='text-align:center;'>DASHBOARD</h2>", unsafe_allow_html=True)
    initial_balance = st.number_input("ACCOUNT SIZE ($)", value=10000.0)
    
    # חישובים מהירים
    closed_trades = df[df['Status'] == 'Closed'].copy()
    if not closed_trades.empty:
        closed_trades['Profit_USD'] = pd.to_numeric(closed_trades['Profit_USD'])
        net_profit = closed_trades['Profit_USD'].sum()
        win_rate = (len(closed_trades[closed_trades['Profit_USD'] > 0]) / len(closed_trades)) * 100
        
        st.markdown(f"""
        <div style='background:#111; padding:15px; border-radius:10px; border:1px solid #222;'>
            <p class='metric-label'>Win Rate</p>
            <p class='metric-value'>{win_rate:.1f}%</p>
            <p class='metric-label'>Net Profit</p>
            <p class='metric-value' style='color:#00ff88;'>${net_profit:,.2f}</p>
        </div>
        """, unsafe_allow_html=True)

# --- ממשק ראשי ---
st.markdown("<h1 style='font-size: 40px;'>Trading <span style='color:#4caf50;'>Pro</span></h1>", unsafe_allow_html=True)

t1, t2, t3 = st.tabs(["⚡ ACTIVE", "➕ NEW TRADE", "📊 ANALYTICS"])

with t2:
    st.markdown("### ENTER NEW POSITION")
    with st.form("pro_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1: tic = st.text_input("SYMBOL").upper()
        with col2: qty = st.number_input("QTY", min_value=0.01)
        with col3: pri = st.number_input("ENTRY PRICE", min_value=0.01)
        
        if st.form_submit_button("EXECUTE ORDER"):
            if tic:
                new_row = pd.DataFrame([{
                    'ID': len(df) + 1, 'Ticker': tic, 'Entry_Date': str(date.today()),
                    'Entry_Time': datetime.now().strftime("%H:%M"), 'Quantity': qty,
                    'Entry_Price': pri, 'Status': 'Open', 'Exit_Date': '', 'Exit_Price': 0,
                    'Conclusions': '', 'Profit_USD': 0
                }])
                save_data(pd.concat([df, new_row], ignore_index=True))
                st.rerun()

with t1:
    open_trades = df[df['Status'] == 'Open']
    if not open_trades.empty:
        tickers = open_trades['Ticker'].unique().tolist()
        live_prices = yf.download(tickers, period="1d", interval="1m", progress=False)['Close'].iloc[-1]
        
        for idx, row in open_trades.iterrows():
            cp = live_prices[row['Ticker']] if len(tickers) > 1 else live_prices
            pnl = (float(cp) - float(row['Entry_Price'])) * float(row['Quantity'])
            pct = (float(cp) / float(row['Entry_Price']) - 1) * 100
            
            border_class = "profit-border" if pnl >= 0 else "loss-border"
            pnl_color = "#00ff88" if pnl >= 0 else "#ff3366"
            
            st.markdown(f"""
                <div class="trade-card {border_class}">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:24px; font-weight:bold;">{row['Ticker']}</span>
                        <span style="color:{pnl_color}; font-size:22px; font-weight:bold;">{pct:+.2f}%</span>
                    </div>
                    <p style="color:#888;">Qty: {row['Quantity']} | Entry: ${row['Entry_Price']:.2f} | Current: ${cp:.2f}</p>
                    <p style="font-size:18px;">P&L: <span style="color:{pnl_color}; font-weight:bold;">${pnl:+,.2f}</span></p>
                </div>
            """, unsafe_allow_html=True)
            
            with st.expander("CLOSE POSITION"):
                ex_p = st.number_input("Exit Price", key=f"e_{idx}", value=float(cp))
                con = st.text_area("Trading Notes", key=f"n_{idx}")
                if st.button("CONFIRM EXIT", key=f"b_{idx}"):
                    df.at[idx, 'Status'] = 'Closed'
                    df.at[idx, 'Exit_Date'] = str(date.today())
                    df.at[idx, 'Exit_Price'] = ex_p
                    df.at[idx, 'Conclusions'] = con
                    df.at[idx, 'Profit_USD'] = (ex_p - float(row['Entry_Price'])) * float(row['Quantity'])
                    save_data(df)
                    st.rerun()
    else:
        st.markdown("<p style='text-align:center; color:#666; padding:50px;'>No active positions. Find your next setup!</p>", unsafe_allow_html=True)

with t3:
    if not closed_trades.empty:
        st.markdown("### ACCOUNT GROWTH")
        closed_trades['Equity'] = initial_balance + closed_trades['Profit_USD'].cumsum()
        st.line_chart(closed_trades.set_index('Exit_Date')['Equity'])
        
        st.markdown("### TRADE LOG")
        st.dataframe(closed_trades[['Ticker', 'Entry_Date', 'Profit_USD', 'Conclusions']].style.background_gradient(subset=['Profit_USD'], cmap='RdYlGn'))
