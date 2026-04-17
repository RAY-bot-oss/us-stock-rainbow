import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

# 網頁標題
st.set_page_config(page_title="美股彩虹圖工具")
st.title("🌈 美股估值彩虹圖生成器")

# 使用者輸入代號
ticker_input = st.text_input("請輸入美股代號 (例如: TSLA, NVDA, AAPL)", "AAPL")

if ticker_input:
    with st.spinner('數據計算中...'):
        ticker = yf.Ticker(ticker_input)
        df = ticker.history(period="5y")
        
        # 獲取基礎數據
        eps = ticker.info.get('trailingEps', 0)
        
        if eps > 0:
            # 簡單彩虹倍數範例
            multipliers = [15, 20, 25, 30, 35, 40]
            colors = ['#1a9850', '#91cf60', '#d9ef8b', '#fee08b', '#fc8d59', '#d73027']
            
            fig = go.Figure()
            for i in range(len(multipliers) - 1):
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=[eps * multipliers[i+1]] * len(df),
                    fill='tonexty' if i > 0 else 'tozeroy',
                    mode='none',
                    name=f"區間 {multipliers[i]}-{multipliers[i+1]}x",
                    fillcolor=colors[i],
                    opacity=0.4
                ))
            
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name="股價", line=dict(color='black')))
            
            # 在網頁顯示圖表
            st.plotly_chart(fig, use_container_width=True)
            st.success(f"目前 {ticker_input} 的每股盈餘 (EPS) 為: {eps}")
        else:
            st.error("暫時無法獲取該股票的盈餘數據，可能該公司目前處於虧損狀態。")