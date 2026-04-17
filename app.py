import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# 1. 網頁配置
st.set_page_config(page_title="財富彩虹-破解優化版", layout="wide")

# 套用 JSON 中的專業深色美學
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .data-card {
        background-color: #161b22; border: 1px solid #30363d;
        border-radius: 8px; padding: 12px; text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-val { font-size: 24px; font-weight: 600; color: #58a6ff; }
    .metric-label { font-size: 13px; color: #8b949e; }
    </style>
    """, unsafe_allow_html=True)

# 2. 頂部輸入區
col1, col2, col3 = st.columns([3, 2, 1])
with col1:
    ticker_input = st.text_input("輸入代碼 (例如: NVDA, 2330.TW)", "NVDA").upper()
with col2:
    period = st.selectbox("計算週期", ["3y", "5y", "10y"], index=0)
with col3:
    is_log = st.checkbox("對數模式 (Log)", value=True)

# 3. 核心算法 (整合 JSON 中的回歸邏輯)
@st.cache_data(ttl=3600)
def get_optimized_data(symbol, period_str):
    try:
        df = yf.Ticker(symbol).history(period=period_str)
        if df.empty: return None, "無數據"
        
        df['Day_Index'] = np.arange(len(df))
        X = df[['Day_Index']].values
        # 根據 JSON 邏輯，使用對數股價進行回歸
        y = np.log(df['Close'].values) if is_log else df['Close'].values
        
        model = LinearRegression().fit(X, y)
        df['Pred'] = model.predict(X)
        std = (y - df['Pred']).std()
        
        # --- 計算年化報酬率 (從斜率推算) ---
        # 假設一年有 252 個交易日
        slope = model.coef_[0]
        if is_log:
            ann_return = (np.exp(slope * 252) - 1) * 100
        else:
            ann_return = (slope * 252 / df['Close'].mean()) * 100
            
        return (df, std, ann_return), None
    except Exception as e:
        return None, str(e)

res, err = get_optimized_data(ticker_input, period)

if res:
    df, sigma, ann_r = res
    curr_close = df['Close'].iloc[-1]
    last_pred = df['Pred'].iloc[-1]
    
    # 計算 Z-Score
    curr_y = np.log(curr_close) if is_log else curr_close
    z_score = (curr_y - last_pred) / sigma

    # 4. 頂部看板 (模仿專業金融介面)
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f'<div class="data-card"><div class="metric-label">當前收盤價</div><div class="metric-val">${curr_close:.2f}</div></div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="data-card"><div class="metric-label">當前水位 (Z-Score)</div><div class="metric-val">{z_score:.2f} σ</div></div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="data-card"><div class="metric-label">預估年化報酬率</div><div class="metric-val">{ann_r:.1f}%</div></div>', unsafe_allow_html=True)
    m4.markdown(f'<div class="data-card"><div class="metric-label">標準差 (σ)</div><div class="metric-val">{sigma:.4f}</div></div>', unsafe_allow_html=True)

    # 5. 繪圖 (專業漸層配色)
    fig = go.Figure()
    
    def get_y(val): return np.exp(val) if is_log else val

    # 定義彩虹層 (使用 JSON 風格的高透明度配色)
    layers = [
        (3, 2, 'rgba(255, 0, 0, 0.12)'),      # 極度高估
        (2, 1, 'rgba(255, 165, 0, 0.12)'),    # 高估
        (1, 0, 'rgba(255, 255, 0, 0.08)'),    # 偏高
        (0, -1, 'rgba(0, 255, 0, 0.08)'),     # 合理
        (-1, -2, 'rgba(0, 0, 255, 0.12)'),    # 偏低
        (-2, -3, 'rgba(128, 0, 128, 0.12)')   # 低估
    ]

    for up_sig, low_sig, color in layers:
        fig.add_trace(go.Scatter(
            x=df.index, y=get_y(df['Pred'] + up_sig * sigma),
            mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=get_y(df['Pred'] + low_sig * sigma),
            fill='tonexty', fillcolor=color, line=dict(width=0), showlegend=False
        ))

    # 主股價線條
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'], name="Price",
        line=dict(color='#ffffff', width=1.8),
        hovertemplate="日期: %{x}<br>價格: %{y:.2f}<extra></extra>"
    ))

    fig.update_layout(
        template="plotly_dark", height=600, margin=dict(t=20, b=0),
        hovermode="x unified",
        xaxis=dict(showgrid=False, rangeslider=dict(visible=True, thickness=0.04)),
        yaxis=dict(gridcolor='#23282e', side='right', type='log' if is_log else 'linear')
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.error(f"無法載入：{err}")