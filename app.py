import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# 1. 網頁配置
st.set_page_config(page_title="財富彩虹橋-專業版", layout="wide")

# 專業深色 CSS
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .data-card {
        background-color: #161b22; border: 1px solid #30363d;
        border-radius: 10px; padding: 15px; text-align: center;
    }
    .metric-val { font-size: 24px; font-weight: bold; color: #ffffff; }
    .metric-label { font-size: 14px; color: #8b949e; }
    </style>
    """, unsafe_allow_html=True)

# 2. 頂部控制區
c1, c2, c3 = st.columns([3, 2, 1])
with c1:
    ticker_input = st.text_input("輸入代碼 (例如: 00981A.TW, NVDA)", "00981A.TW").upper()
with c2:
    period = st.selectbox("時間範圍", ["3y", "5y", "10y"], index=0)
with c3:
    is_log = st.checkbox("對數模式 (Log)", value=True)

# 3. 數據處理與回歸計算
@st.cache_data(ttl=3600)
def get_final_data(symbol, p_str):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period=p_str)
        if df.empty: return None, "找不到數據"
        
        # 線性回歸 (Log 空間)
        df['Idx'] = np.arange(len(df))
        X = df[['Idx']].values
        y_vals = np.log(df['Close'].values) if is_log else df['Close'].values
        
        model = LinearRegression().fit(X, y_vals)
        df['Mid_Log'] = model.predict(X)
        std = (y_vals - df['Mid_Log']).std()
        
        return (df, std), None
    except Exception as e:
        return None, str(e)

res, err = get_final_data(ticker_input, period)

if res:
    df, sigma = res
    
    # 轉換函數：將 Log 轉回原始價格
    def to_p(val): return np.exp(val) if is_log else val

    # 4. 繪製圖表
    fig = go.Figure()

    # 線條配置 (名稱, Sigma倍數, 顏色, 填充顏色)
    configs = [
        ('p3s', '極度高估 (+3σ)', 3, '#ff4b4b', 'rgba(255, 75, 75, 0.1)'),
        ('p2s', '高估 (+2σ)', 2, '#ff8c00', 'rgba(255, 140, 0, 0.1)'),
        ('p1s', '偏高 (+1σ)', 1, '#ffd700', 'rgba(255, 215, 0, 0.05)'),
        ('Mid', '趨勢中線 (Mid)', 0, '#00e676', 'rgba(0, 230, 118, 0.05)'),
        ('m1s', '偏低 (-1σ)', -1, '#2979ff', 'rgba(41, 121, 255, 0.1)'),
        ('m2s', '低估 (-2σ)', -2, '#aa00ff', 'rgba(170, 0, 255, 0.1)'),
        ('m3s', '極度低估 (-3σ)', -3, '#651fff', None)
    ]

    # A. 畫區間填充
    for i in range(len(configs)-1):
        upper = to_p(df['Mid_Log'] + configs[i][2] * sigma)
        lower = to_p(df['Mid_Log'] + configs[i+1][2] * sigma)
        fig.add_trace(go.Scatter(x=df.index, y=upper, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=df.index, y=lower, fill='tonexty', fillcolor=configs[i][4], line=dict(width=0), showlegend=False, hoverinfo='skip'))

    # B. 畫七條清晰的線條
    for key_name, label, s_val, color, _ in configs:
        y_data = to_p(df['Mid_Log'] + s_val * sigma)
        fig.add_trace(go.Scatter(
            x=df.index, y=y_data, name=label,
            mode='lines',
            line=dict(color=color, width=1),
            hovertemplate=f"{label}: %{{y:.2f}}<extra></extra>"
        ))

    # C. 畫收盤價線條 (最頂層)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'], name="收盤價",
        mode='lines+markers',
        line=dict(color='white', width=2),
        marker=dict(size=4, opacity=0), # 懸停時自動顯示
        hovertemplate="<b>日期: %{x|%Y-%m-%d}</b><br>收盤價: %{y:.2f}<extra></extra>"
    ))

    # D. 圖表版面設定 (關鍵：hovermode="x")
    fig.update_layout(
        template="plotly_dark", height=700, margin=dict(t=50, b=0, l=10, r=10),
        hovermode="x", # 觸發同一日期所有線條的點
        xaxis=dict(showgrid=False, rangeslider=dict(visible=True, thickness=0.05)),
        yaxis=dict(gridcolor='#23282e', side='right', type='log' if is_log else 'linear'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    # 5. 下方看板
    last_close = df['Close'].iloc[-1]
    last_log_mid = df['Mid_Log'].iloc[-1]
    z_score = (np.log(last_close) - last_log_mid) / sigma if is_log else (last_close - last_log_mid) / sigma
    
    col_a, col_b, col_c = st.columns(3)
    col_a.markdown(f'<div class="data-card"><div class="metric-label">當前收盤價</div><div class="metric-val">${last_close:.2f}</div></div>', unsafe_allow_html=True)
    col_b.markdown(f'<div class="data-card"><div class="metric-label">當前水位</div><div class="metric-val">{z_score:.2f} σ</div></div>', unsafe_allow_html=True)
    col_c.markdown(f'<div class="data-card"><div class="metric-label">標準差 (σ)</div><div class="metric-val">{sigma:.4f}</div></div>', unsafe_allow_html=True)

else:
    st.error(f"錯誤: {err}")