import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# 1. 網頁配置：維持深色主題與寬版
st.set_page_config(page_title="財富彩虹-樂活五線譜", layout="wide")

# 套用 CSS 強化左側介面美觀
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; border: 1px solid #374151; }
    </style>
    """, unsafe_allow_html=True)

# 2. 側邊欄：保留你覺得不錯的介面
with st.sidebar:
    st.markdown("## 🌈 財富彩虹")
    market_type = st.radio("選擇市場", ["美股 (US)", "台股 (TW)"])
    ticker_input = st.text_input("輸入代碼", "AAPL").upper()
    period = st.selectbox("時間範圍", ["3y", "5y", "10y"], index=0)
    
    st.divider()
    if st.button("🔄 強制更新數據"):
        st.cache_data.clear()
        st.rerun()

    # 自動處理台股後綴
    ticker = ticker_input
    if market_type == "台股 (TW)" and not ticker_input.endswith(".TW"):
        ticker = f"{ticker_input}.TW"

# 3. 穩定版數據抓取函數
@st.cache_data(ttl=3600)
def get_rainbow_data_safe(symbol, period):
    try:
        # 呼叫 yfinance
        stock = yf.Ticker(symbol)
        df = stock.history(period=period)
        
        if df.empty or len(df) < 30:
            return None, "數據量不足或代碼無效"
        
        # 線性回歸計算
        df['Date_Index'] = np.arange(len(df))
        X = df[['Date_Index']].values
        y = df['Close'].values
        
        model = LinearRegression()
        model.fit(X, y)
        
        df['Trend'] = model.predict(X)
        std = (df['Close'] - df['Trend']).std()
        
        return (df, std), None
    except Exception as e:
        # 捕捉 YFRateLimitError 等錯誤
        return None, str(e)

# 4. 主畫面顯示邏輯
data_package, error_msg = get_rainbow_data_safe(ticker, period)

if data_package:
    df, std = data_package
    
    # 繪製圖表 (仿左圖專業深色風格)
    fig = go.Figure()

    # 五線譜層級
    layers = [
        (2, '極度高估 (+2σ)', 'rgba(255, 0, 0, 0.15)'),
        (1, '偏高 (+1σ)', 'rgba(255, 165, 0, 0.15)'),
        (0, '趨勢中線', 'rgba(0, 255, 0, 0.1)'),
        (-1, '偏低 (-1σ)', 'rgba(0, 0, 255, 0.15)'),
        (-2, '極度低估 (-2σ)', 'rgba(128, 0, 128, 0.15)')
    ]

    for i in range(len(layers)-1):
        upper = df['Trend'] + layers[i][0] * std
        lower = df['Trend'] + layers[i+1][0] * std
        fig.add_trace(go.Scatter(
            x=df.index, y=upper, mode='lines', line=dict(width=0), showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=lower, fill='tonexty', fillcolor=layers[i][2],
            line=dict(width=0), name=layers[i][1]
        ))

    # 實際股價
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'], name="收盤價",
        line=dict(color='#ffffff', width=2)
    ))

    fig.update_layout(
        template="plotly_dark", height=650,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(rangeslider=dict(visible=False), showgrid=False),
        yaxis=dict(gridcolor='#333', fixedrange=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)
    
    # 下方數據面板
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("當前股價", f"{df['Close'].iloc[-1]:.2f}")
    c2.metric("趨勢中線", f"{df['Trend'].iloc[-1]:.2f}")
    c3.metric("標準差 σ", f"{std:.2f}")
    c4.metric("乖離率", f"{((df['Close'].iloc[-1]/df['Trend'].iloc[-1])-1)*100:.2f}%")

else:
    # 顯示優雅的錯誤提示
    st.error("### 📉 數據獲取失敗")
    if "RateLimit" in str(error_msg):
        st.warning("Yahoo Finance 暫時限制了連線。這不是你的程式有問題，而是雲端 IP 被封鎖。")
        st.info("💡 解決方案：\n1. 點擊左側「強制更新數據」按鈕。\n2. 稍等 1-2 分鐘再試。\n3. 如果你是專業用戶，建議在本地電腦跑這段程式。")
    else:
        st.info(f"錯誤原因：{error_msg}")