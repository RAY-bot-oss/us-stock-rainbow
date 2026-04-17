import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# 1. 網頁配置與美化 CSS
st.set_page_config(page_title="財富彩虹-專業版", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .data-card {
        background-color: #161b22; border: 1px solid #30363d;
        border-radius: 10px; padding: 15px; text-align: center;
    }
    .metric-val { font-size: 26px; font-weight: bold; color: #ffffff; }
    .metric-label { font-size: 14px; color: #8b949e; margin-bottom: 5px;}
    .highlight-box { background: rgba(31, 119, 180, 0.2); border: 1px solid #1f77b4; border-radius: 5px; padding: 2px 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 頂部控制列
c_title, c_input, c_period, c_btn = st.columns([2, 3, 2, 1])
with c_title:
    st.subheader("🌈 財富彩虹")
with c_input:
    ticker_input = st.text_input("輸入代碼", "AAPL", label_visibility="collapsed").upper()
with c_period:
    period_map = {"1Y": "252d", "3Y": "756d", "5Y": "1260d", "10Y": "2520d"}
    p_choice = st.selectbox("範圍", list(period_map.keys()), index=1, label_visibility="collapsed")
with c_btn:
    if st.button("🔄 刷新"):
        st.cache_data.clear()
        st.rerun()

# 3. 核心算法：破解後的 Log 回歸
@st.cache_data(ttl=3600)
def get_wealth_rainbow_data(symbol):
    try:
        df = yf.Ticker(symbol).history(period="10y") # 抓多一點備用
        if df.empty: return None, "無數據"
        df = df.tail(int(period_map[p_choice].replace('d',''))) # 根據選擇切分數據
        
        # --- 破解公式開始 ---
        df['Day_Index'] = np.arange(len(df))
        X = df[['Day_Index']].values
        y_log = np.log(df['Close'].values) # 關鍵：取對數
        
        model = LinearRegression().fit(X, y_log)
        df['Log_Mid'] = model.predict(X)
        log_std = (y_log - df['Log_Mid']).std()
        
        # 回還到原始股價座標
        df['Mid'] = np.exp(df['Log_Mid'])
        df['p3s'] = np.exp(df['Log_Mid'] + 3 * log_std)
        df['p2s'] = np.exp(df['Log_Mid'] + 2 * log_std)
        df['p1s'] = np.exp(df['Log_Mid'] + 1 * log_std)
        df['m1s'] = np.exp(df['Log_Mid'] - 1 * log_std)
        df['m2s'] = np.exp(df['Log_Mid'] - 2 * log_std)
        df['m3s'] = np.exp(df['Log_Mid'] - 3 * log_std)
        
        # 計算 Z-Score
        last_log_price = np.log(df['Close'].iloc[-1])
        last_log_mid = df['Log_Mid'].iloc[-1]
        z_score = (last_log_price - last_log_mid) / log_std
        
        return (df, z_score, log_std), None
    except Exception as e:
        return None, str(e)

data_pack, err = get_wealth_rainbow_data(ticker_input)

if data_pack:
    df, z, sigma = data_pack
    curr_p = df['Close'].iloc[-1]
    
    # 4. 頂部數據看板 (模仿右圖)
    st.write("") # 間隔
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f'<div class="data-card"><div class="metric-label">{ticker_input}</div><div class="metric-val">${curr_p:.2f}</div></div>', unsafe_allow_html=True)
    with m2:
        color = "#ff4b4b" if z > 1 else "#3dd56d" if z < -1 else "#ffffff"
        st.markdown(f'<div class="data-card"><div class="metric-label">當前水位</div><div class="metric-val" style="color:{color}">{z:.2f} σ</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="data-card"><div class="metric-label">對數標準差</div><div class="metric-val">{sigma:.4f}</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="data-card"><div class="metric-label">最後交易日</div><div class="metric-val">{df.index[-1].strftime("%Y-%m-%d")}</div></div>', unsafe_allow_html=True)

    # 5. 繪製圖表 (強化互動)
    fig = go.Figure()
    
    # 彩虹區間顏色
    colors = {
        'p3': 'rgba(255, 0, 0, 0.15)',    # 極度高估
        'p2': 'rgba(255, 165, 0, 0.15)',  # 高估
        'p1': 'rgba(255, 255, 0, 0.1)',   # 偏高
        'mid': 'rgba(0, 255, 0, 0.1)',    # 合理
        'm1': 'rgba(0, 0, 255, 0.15)',    # 偏低
        'm2': 'rgba(128, 0, 128, 0.15)'   # 低估
    }

    # 繪製各層
    bands = [('p3s','p2s','p3'), ('p2s','p1s','p2'), ('p1s','Mid','p1'), ('Mid','m1s','mid'), ('m1s','m2s','m1'), ('m2s','m3s','m2')]
    for up, low, col in bands:
        fig.add_trace(go.Scatter(x=df.index, y=df[up], mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=df.index, y=df[low], fill='tonexty', fillcolor=colors[col], line=dict(width=0), showlegend=False, hoverinfo='skip'))

    # 收盤價主線 + 垂直對齊 Hover
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'], name="收盤價",
        line=dict(color='white', width=2),
        customdata=df['Mid'],
        hovertemplate="<b>日期:</b> %{x|%Y-%m-%d}<br><b>Mid:</b> %{customdata:.2f}<br><b>收盤價:</b> %{y:.2f}<extra></extra>"
    ))

    fig.update_layout(
        template="plotly_dark", height=650, margin=dict(t=30, b=0, l=10, r=10),
        hovermode="x unified",
        xaxis=dict(showgrid=False, rangeslider=dict(visible=True, thickness=0.05)),
        yaxis=dict(gridcolor='#333', side='right', type='log' if st.toggle("Log 模式", True) else 'linear'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.error(f"數據加載失敗: {err}")