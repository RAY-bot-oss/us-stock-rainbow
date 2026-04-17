import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime

# 1. 網頁配置
st.set_page_config(page_title="財富彩虹橋-究極版", layout="wide")

# 專業深色美學 CSS (模擬左圖風格)
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .data-card-container {
        display: flex; justify-content: space-around;
        background-color: #161b22; border: 1px solid #30363d;
        border-radius: 12px; padding: 20px; margin-bottom: 20px;
    }
    .data-item { text-align: center; border-right: 1px solid #30363d; padding: 0 20px; }
    .data-item:last-child { border-right: none; }
    .metric-val { font-size: 22px; font-weight: bold; color: #ffffff; display: block; }
    .metric-label { font-size: 13px; color: #8b949e; }
    .z-score-box { background: #3d1a1a; color: #ff4b4b; padding: 10px 20px; border-radius: 8px; font-size: 24px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. 頂部輸入區
c_input, c_period = st.columns([4, 2])
with c_input:
    ticker_input = st.text_input("輸入代碼", "00981A.TW").upper()
with c_period:
    period = st.selectbox("時間範圍", ["3y", "5y", "10y"], index=0)

# 3. 數據計算
@st.cache_data(ttl=3600)
def get_pro_data(symbol, p_str):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period=p_str)
        if df.empty: return None, "無數據"
        
        # 準備回歸數據
        df['Idx'] = np.arange(len(df))
        X = df[['Idx']].values
        y_log = np.log(df['Close'].values)
        
        # 計算線性回歸
        model = LinearRegression().fit(X, y_log)
        df['Log_Mid'] = model.predict(X)
        log_std = (y_log - df['Log_Mid']).std()
        
        # 斜率推算年化報酬率
        slope = model.coef_[0]
        ann_return = (np.exp(slope * 252) - 1) * 100
        
        return (df, log_std, ann_return), None
    except Exception as e:
        return None, str(e)

res, err = get_pro_data(ticker_input, period)

if res:
    df, sigma, ann_r = res
    last_close = df['Close'].iloc[-1]
    last_idx = df['Idx'].iloc[-1]
    z_score = (np.log(last_close) - df['Log_Mid'].iloc[-1]) / sigma

    # 4. 頂部數據看板 (完全模仿左圖)
    st.markdown(f"""
    <div class="data-card-container">
        <div style="display:flex; align-items:center;">
            <div style="margin-right:20px;">
                <b style="font-size:24px;">{ticker_input}</b><br>
                <span style="color:#8b949e; font-size:14px;">對數回歸分析</span>
            </div>
            <div class="z-score-box">{z_score:.2f}<br><span style="font-size:12px;">σ</span></div>
        </div>
        <div class="data-item"><span class="metric-label">收盤價</span><span class="metric-val">{last_close:.2f}</span></div>
        <div class="data-item"><span class="metric-label">年化報酬率</span><span class="metric-val">{ann_r:.1f}%</span></div>
        <div class="data-item"><span class="metric-label">交易日數</span><span class="metric-val">{len(df)} / 735</span></div>
        <div class="data-item"><span class="metric-label">最後交易日</span><span class="metric-val">{df.index[-1].strftime('%Y-%m-%d')}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # 5. 繪製究極圖表
    fig = go.Figure()

    # 彩虹設定
    configs = [
        (3, '#ff4b4b', '極度高估 (+3σ)'), (2, '#ff8c00', '高估 (+2σ)'), (1, '#ffd700', '偏高 (+1σ)'),
        (0, '#00e676', '中線 (Mid)'), (-1, '#2979ff', '偏低 (-1σ)'), (-2, '#aa00ff', '低估 (-2σ)'), (-3, '#651fff', '極度低估 (-3σ)')
    ]

    # 繪製填充 (放在底層)
    fill_colors = ['rgba(255,75,75,0.1)', 'rgba(255,140,0,0.1)', 'rgba(255,215,0,0.05)', 'rgba(0,230,118,0.05)', 'rgba(41,121,255,0.1)', 'rgba(170,0,255,0.1)']
    for i in range(len(configs)-1):
        upper = np.exp(df['Log_Mid'] + configs[i][0] * sigma)
        lower = np.exp(df['Log_Mid'] + configs[i+1][0] * sigma)
        fig.add_trace(go.Scatter(x=df.index, y=upper, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=df.index, y=lower, fill='tonexty', fillcolor=fill_colors[i], line=dict(width=0), showlegend=False, hoverinfo='skip'))

    # 繪製七條「實體邊界線」並設定 Marker
    for s_val, color, label in configs:
        y_val = np.exp(df['Log_Mid'] + s_val * sigma)
        fig.add_trace(go.Scatter(
            x=df.index, y=y_val, name=label,
            mode='lines',
            line=dict(color=color, width=1.5),
            # 關鍵設定：markers 只有在懸停時透過 hovermode 觸發
            marker=dict(size=6, symbol='circle', opacity=0), 
            hovertemplate=f"{label}: %{{y:.2f}}<extra></extra>"
        ))

    # 繪製收盤價 (最頂層)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'], name="收盤價",
        mode='lines',
        line=dict(color='white', width=2.5),
        marker=dict(size=8, color='white', line=dict(width=2, color='white'), opacity=0),
        hovertemplate="日期: %{x}<br>收盤價: %{y:.2f}<extra></extra>"
    ))

    # 6. 圖表 Layout 優化 (連動懸停的核心)
    fig.update_layout(
        template="plotly_dark", height=750, margin=dict(t=30, b=0, l=10, r=10),
        hovermode="x unified", # 核心：顯示同一日期所有數據的點與標籤
        xaxis=dict(showgrid=False, rangeslider=dict(visible=True, thickness=0.05)),
        yaxis=dict(
            gridcolor='#23282e', side='right', 
            type='log', # 核心：強制對數座標軸，線條會變完美直線
            tickformat='.1f'
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # 懸停時的線條與點樣式微調
    fig.update_traces(hoveron='points', mode='lines+markers')

    st.plotly_chart(fig, use_container_width=True)

else:
    st.error(f"數據抓取失敗：{err}")