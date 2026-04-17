import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

# 網頁基本設定
st.set_page_config(page_title="美股彩虹圖工具", layout="wide")
st.title("🌈 美股估值彩虹圖 (v2.0 新版)")

# 使用 Streamlit 快取，避免頻繁請求
@st.cache_data(ttl=3600)
def get_data_v2(ticker_symbol):
    # 根據 yfinance 新版建議：直接呼叫，不自定義 Session
    ticker = yf.Ticker(ticker_symbol)
    
    # 獲取股價
    df = ticker.history(period="5y")
    
    # 獲取 EPS
    try:
        # 注意：有些股票可能抓不到 info，我們做個保護
        val = ticker.info
        eps = val.get('trailingEps', 0)
    except:
        eps = 0
        
    return df, eps

ticker_input = st.text_input("輸入美股代號 (例如: AAPL, TSLA, NVDA):", "AAPL").upper()

if ticker_input:
    with st.spinner('正在與 Yahoo Finance 通訊...'):
        df, eps = get_data_v2(ticker_input)
    
    if df.empty:
        st.error("❌ 無法取得股價數據。")
        st.info("💡 提示：如果代號正確卻沒資料，可能是 Yahoo 暫時封鎖了 Streamlit Cloud 的 IP。")
    elif eps <= 0:
        st.warning(f"⚠️ 已取得股價，但無法取得 {ticker_input} 的 EPS 資料（可能公司虧損中）。")
        # 即使沒 EPS，我們還是把股價圖畫出來
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name="實際股價", line=dict(color='black')))
        st.plotly_chart(fig, use_container_width=True)
    else:
        # 繪製彩虹圖
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
                name=f"{labels[i]} ({multipliers[i]}x-{multipliers[i+1]}x)",
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
        st.success(f"✅ 成功載入！{ticker_input} 目前 Trailing EPS: ${eps}")