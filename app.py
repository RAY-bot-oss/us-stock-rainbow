import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# 1. 網頁配置：深色主題與寬版
st.set_page_config(page_title="財富彩虹-雙棲版", layout="wide")

# 套用 CSS 讓介面變深色
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stTextInput > div > div > input { background-color: #262730; color: white; }
    </style>
    """, unsafe_allow_html=True)

# 2. 側邊欄：功能切換
with st.sidebar:
    st.title("🌈 財富彩虹")
    market_type = st.radio("選擇市場", ["美股 (US)", "台股 (TW)"])
    ticker_input = st.text_input("輸入代號", "AAPL" if market_type == "美股 (US)" else "2330")
    period = st.selectbox("時間範圍", ["3y", "5y", "10y"], index=0)

    if market_type == "台股 (TW)" and not ticker_input.endswith(".TW"):
        ticker = f"{ticker_input}.TW"
    else:
        ticker = ticker_input

# 3. 數據抓取與線性回歸計算
@st.cache_data(ttl=3600)
def get_rainbow_data(symbol, period):
    df = yf.Ticker(symbol).history(period=period)
    if df.empty: return None
    
    # 線性回歸計算
    df['Date_Index'] = np.arange(len(df))
    X = df[['Date_Index']].values
    y = df['Close'].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    # 趨勢中線 (Trend Line)
    df['Trend'] = model.predict(X)
    # 計算標準差
    std = (df['Close'] - df['Trend']).std()
    
    return df, std

data_result = get_rainbow_data(ticker, period)

if data_result:
    df, std = data_result
    
    # 4. 繪製專業彩虹圖
    fig = go.Figure()

    # 定義五線譜區間 (趨勢線 +- 1sigma, 2sigma)
    # 左圖通常有：+2σ(紅), +1σ(橘), 中線(綠), -1σ(藍), -2σ(紫)
    layers = [
        (2, '極度高估', 'rgba(255, 0, 0, 0.2)'),
        (1, '高估', 'rgba(255, 165, 0, 0.2)'),
        (0, '合理', 'rgba(0, 128, 0, 0.2)'),
        (-1, '低估', 'rgba(0, 0, 255, 0.2)'),
        (-2, '極度低估', 'rgba(75, 0, 130, 0.2)')
    ]

    # 繪製填滿區間
    for i in range(len(layers)-1):
        upper = df['Trend'] + layers[i][0] * std
        lower = df['Trend'] + layers[i+1][0] * std
        fig.add_trace(go.Scatter(
            x=df.index, y=upper, mode='lines', line=dict(width=0),
            showlegend=False, hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=lower, fill='tonexty', 
            fillcolor=layers[i][2], line=dict(width=0),
            name=layers[i][1]
        ))

    # 實際股價線
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'],
        name="收盤價", line=dict(color='white', width=1.5)
    ))

    # 圖表樣式調整 (仿左圖深色風格)
    fig.update_layout(
        template="plotly_dark",
        height=600,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#333'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)
    
    # 下方顯示數據資訊
    col1, col2, col3 = st.columns(3)
    col1.metric("當前收盤價", f"{df['Close'].iloc[-1]:.2f}")
    col2.metric("標準差 (σ)", f"{std:.2f}")
    col3.metric("資料天數", len(df))

else:
    st.error("找不到該股票數據，請重新確認代碼。")