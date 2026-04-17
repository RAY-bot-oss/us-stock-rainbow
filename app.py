import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# 1. 網頁配置
st.set_page_config(page_title="美股研究-樂活五線譜", layout="wide")

# 深色主題 CSS
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; border: 1px solid #374151; }
    </style>
    """, unsafe_allow_html=True)

# 2. 側邊欄：純美股設定
with st.sidebar:
    st.markdown("## 🇺🇸 美股研究中心")
    # 移除市場切換，直接輸入美股代碼
    ticker_input = st.text_input("輸入美股代碼", "AAPL").upper()
    period = st.selectbox("時間範圍", ["3y", "5y", "10y"], index=1)
    
    st.divider()
    if st.button("🔄 刷新數據"):
        st.cache_data.clear()
        st.rerun()

# 3. 數據抓取與線性回歸計算
@st.cache_data(ttl=3600)
def get_us_stock_data(symbol, period):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period=period)
        
        if df.empty or len(df) < 30:
            return None, "數據不足或代碼無效"
        
        # 線性回歸計算 (計算 Mid 趨勢線)
        df['Date_Index'] = np.arange(len(df))
        X = df[['Date_Index']].values
        y = df['Close'].values
        
        model = LinearRegression()
        model.fit(X, y)
        
        df['Trend'] = model.predict(X)
        std = (df['Close'] - df['Trend']).std()
        
        return (df, std), None
    except Exception as e:
        return None, str(e)

data_package, error_msg = get_us_stock_data(ticker_input, period)

if data_package:
    df, std = data_package
    
    # 4. 繪製圖表
    fig = go.Figure()

    # 五線譜層級
    layers = [
        (2, '極度高估 (+2σ)', 'rgba(255, 0, 0, 0.15)'),
        (1, '偏高 (+1σ)', 'rgba(255, 165, 0, 0.15)'),
        (0, '趨勢中線 (Mid)', 'rgba(0, 255, 0, 0.1)'),
        (-1, '偏低 (-1σ)', 'rgba(0, 0, 255, 0.15)'),
        (-2, '極度低估 (-2σ)', 'rgba(128, 0, 128, 0.15)')
    ]

    # 繪製背景層
    for i in range(len(layers)-1):
        upper = df['Trend'] + layers[i][0] * std
        lower = df['Trend'] + layers[i+1][0] * std
        fig.add_trace(go.Scatter(
            x=df.index, y=upper, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=lower, fill='tonexty', fillcolor=layers[i][2],
            line=dict(width=0), name=layers[i][1], hoverinfo='skip'
        ))

    # 5. 核心修改：設定收盤價線條的懸停資訊 (Hovertemplate)
    # 這裡我們自定義顯示內容：日期、Mid、收盤價
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['Close'], 
        name="實際收盤價",
        line=dict(color='#ffffff', width=2),
        customdata=df['Trend'], # 將 Mid 數據傳入 customdata 供 Tooltip 使用
        hovertemplate=(
            "<b>日期:</b> %{x|%Y-%m-%d}<br>" +
            "<b>Mid (趨勢中線):</b> %{customdata:.2f}<br>" +
            "<b>收盤價:</b> %{y:.2f}<br>" +
            "<extra></extra>" # 隱藏側邊標籤
        )
    ))

    # 圖表外觀優化
    fig.update_layout(
        template="plotly_dark", height=650,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(showgrid=False, title="Date"),
        yaxis=dict(gridcolor='#333', title="Price (USD)"),
        hovermode="x unified", # 讓懸停線垂直對齊所有數據點
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)
    
    # 下方數據儀表板
    c1, c2, c3 = st.columns(3)
    c1.metric("當前股價", f"${df['Close'].iloc[-1]:.2f}")
    c2.metric("Mid (趨勢中線)", f"${df['Trend'].iloc[-1]:.2f}")
    c3.metric("乖離率", f"{((df['Close'].iloc[-1]/df['Trend'].iloc[-1])-1)*100:.2f}%")

else:
    st.error(f"無法載入數據：{error_msg}")
    st.info("請檢查美股代號是否正確，或嘗試重新整理。")