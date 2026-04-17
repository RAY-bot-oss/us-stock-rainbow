import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# 1. 配置與專業 CSS
st.set_page_config(page_title="財富彩虹-美股版", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    /* 頂部數據卡片 */
    .data-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    .metric-val { font-size: 24px; font-weight: bold; color: #ffffff; }
    .metric-label { font-size: 14px; color: #8b949e; }
    </style>
    """, unsafe_allow_html=True)

# 2. 頂部控制區 (取代側邊欄，模仿右圖)
col_input, col_period, col_refresh = st.columns([4, 2, 1])
with col_input:
    ticker_input = st.text_input("輸入美股代碼 (例如: NVDA, TSLA)", "TSLA").upper()
with col_period:
    period = st.selectbox("時間範圍", ["3y", "5y", "10y"], index=0)
with col_refresh:
    if st.button("🔄 刷新"):
        st.cache_data.clear()
        st.rerun()

# 3. 數據計算函數
@st.cache_data(ttl=3600)
def get_advanced_data(symbol, period):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period=period)
        if df.empty: return None, "無數據"
        
        # 線性回歸
        df['Date_Index'] = np.arange(len(df))
        X = df[['Date_Index']].values
        y = df['Close'].values
        model = LinearRegression().fit(X, y)
        df['Mid'] = model.predict(X)
        std = (df['Close'] - df['Mid']).std()
        
        # 各線段計算
        df['p2s'] = df['Mid'] + 2 * std
        df['p1s'] = df['Mid'] + 1 * std
        df['m1s'] = df['Mid'] - 1 * std
        df['m2s'] = df['Mid'] - 2 * std
        
        return (df, std, stock.info), None
    except Exception as e:
        return None, str(e)

result, error = get_advanced_data(ticker_input, period)

if result:
    df, std, info = result
    curr_price = df['Close'].iloc[-1]
    curr_mid = df['Mid'].iloc[-1]
    bias = (curr_price / curr_mid - 1) * 100
    
    # 4. 頂部數據看板 (模仿右圖資訊列)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="data-card"><div class="metric-label">{ticker_input}</div><div class="metric-val">${curr_price:.2f}</div></div>', unsafe_allow_html=True)
    with c2:
        # 乖離水位顯示
        level = "合理"
        if bias > 20: level = "極度高估"
        elif bias > 10: level = "高估"
        elif bias < -20: level = "極度低估"
        st.markdown(f'<div class="data-card"><div class="metric-label">當前水位</div><div class="metric-val">{bias:.1f}% ({level})</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="data-card"><div class="metric-label">標準差 (σ)</div><div class="metric-val">{std:.2f}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="data-card"><div class="metric-label">最後交易日</div><div class="metric-val">{df.index[-1].strftime("%Y-%m-%d")}</div></div>', unsafe_allow_html=True)

    # 5. 繪製圖表 (強化 Hover 與垂直線)
    fig = go.Figure()

    # 彩虹區間
    colors = ['rgba(255,0,0,0.1)', 'rgba(255,165,0,0.1)', 'rgba(0,255,0,0.05)', 'rgba(0,0,255,0.1)', 'rgba(128,0,128,0.1)']
    bounds = [('p2s', 'p1s'), ('p1s', 'Mid'), ('Mid', 'm1s'), ('m1s', 'm2s')]
    
    for i, (up, low) in enumerate(bounds):
        fig.add_trace(go.Scatter(x=df.index, y=df[up], mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=df.index, y=df[low], fill='tonexty', fillcolor=colors[i], line=dict(width=0), showlegend=False, hoverinfo='skip'))

    # 收盤價線條 (加入 Hover Template)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'],
        name="收盤價",
        line=dict(color='white', width=2),
        hovertemplate="<b>日期:</b> %{x|%Y-%m-%d}<br><b>收盤價:</b> %{y:.2f}<br><b>Mid:</b> %{customdata:.2f}<extra></extra>",
        customdata=df['Mid']
    ))

    # 配置
    fig.update_layout(
        template="plotly_dark", height=600,
        hovermode="x unified", # 關鍵：這會產生垂直對齊線
        xaxis=dict(showgrid=False, rangeslider=dict(visible=True)), # 加入下方的時間滑塊
        yaxis=dict(gridcolor='#333', side='right'), # 坐標軸放右邊更專業
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.error(f"錯誤: {error}")