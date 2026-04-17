import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import requests

# 網頁設定
st.set_page_config(page_title="美股彩虹圖工具", layout="wide")
st.title("🌈 美股估值彩虹圖生成器 (防封鎖版)")

# 設定快取，減少對 Yahoo 的請求頻率
@st.cache_data(ttl=3600)
def get_data_safe(ticker_symbol):
    # 建立一個 session 並偽裝 User-Agent，降低被封鎖機率
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    ticker = yf.Ticker(ticker_symbol, session=session)
    
    # 抓取 5 年歷史股價
    df = ticker.history(period="5y")
    
    # 嘗試獲取 EPS，如果被封鎖則會回傳 0
    try:
        eps = ticker.info.get('trailingEps', 0)
    except:
        eps = 0
        
    return df, eps

ticker_input = st.text_input("輸入美股代號 (如: AAPL, TSLA, MSFT):", "AAPL").upper()

if ticker_input:
    with st.spinner(f'正在嘗試獲取 {ticker_input} 的數據...'):
        df, eps = get_data_safe(ticker_input)
    
    if df.empty:
        st.error("❌ 抓不到股價數據。這通常是 Yahoo Finance 暫時封鎖了 Cloud 伺服器的 IP。")
        st.info("💡 建議：請過 5 分鐘後再重新整理網頁，或是點擊右下角 'Manage app' -> 'Reboot App' 試試看換個 IP。")
    elif eps <= 0:
        st.warning(f"⚠️ 抓到了股價，但無法獲取 {ticker_input} 的 EPS (盈餘) 資料。這可能是因為公司虧損或 Yahoo 限制了詳細資料。")
    else:
        # 繪圖邏輯
        multipliers = [15, 20, 25, 30, 35, 40]
        colors = ['#1a9850', '#91cf60', '#d9ef8b', '#fee08b', '#fc8d59', '#d73027']
        labels = ['極度低估', '低估', '合理', '偏高', '高估']

        fig = go.Figure()
        for i in range(len(multipliers) - 1):
            fig.add_trace(go.Scatter(
                x=df.index,
                y=[eps * multipliers[i+1]] * len(df),
                fill='tonexty' if i > 0 else 'tozeroy',
                mode='none',
                name=f"{labels[i]} ({multipliers[i]}-{multipliers[i+1]}x)",
                fillcolor=colors[i],
                opacity=0.3
            ))

        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name="實際股價", line=dict(color='black', width=2)))
        
        fig.update_layout(
            hovermode="x unified",
            xaxis_title="日期",
            yaxis_title="價格 (USD)",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)
        st.success(f"目前 {ticker_input} 的每股盈餘 (EPS) 為: ${eps}")