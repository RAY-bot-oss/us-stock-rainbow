import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# 1. 網頁基礎配置
st.set_page_config(page_title="財富彩虹橋-專業版", layout="wide")

# 專業深色美學 CSS
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

# 2. 頂部控制列
c1, c2, c3 = st.columns([3, 2, 1])
with c1:
    # 預設改為你正在研究的 00981A
    ticker_input = st.text_input("輸入代碼", "00981A.TW").upper()
with c2:
    period = st.selectbox("時間範圍", ["3y", "5y", "10y"], index=0)
with c3:
    is_log = st.checkbox("對數模式 (Log)", value=True)

# 3. 穩定數據抓取與計算 (加入更強的快取機制)
@st.cache_data(ttl=86400) # 快取一天，避免頻繁請求被 Yahoo 封鎖
def get_stock_data_final(symbol, p_str):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period=p_str)
        if df.empty: return None, "找不到該股票數據"
        
        # 線性回歸 (對數空間計算)
        df['Idx'] = np.arange(len(df))
        X = df[['Idx']].values
        y_vals = np.log(df['Close'].values) if is_log else df['Close'].values
        
        model = LinearRegression().fit(X, y_vals)
        df['Mid_Log'] = model.predict(X)
        std = (y_vals - df['Mid_Log']).std()
        
        # 推算斜率產生的年化報酬率
        slope = model.coef_[0]
        ann_return = (np.exp(slope * 252) - 1) * 100 if is_log else (slope * 252 / df['Close'].mean()) * 100
        
        return (df, std, ann_return), None
    except Exception as e:
        return None, str(e)

data_res, error_msg = get_stock_data_final(ticker_input, period)

if data_res:
    df, sigma, ann_r = data_res
    
    def to_p(val): return np.exp(val) if is_log else val

    # 4. 繪製專業圖表
    fig = go.Figure()

    # 線條與填充設定
    configs = [
        ('p3s', '極度高估 (+3σ)', 3, '#ff4b4b', 'rgba(255, 75, 75, 0.1)'),
        ('p2s', '高估 (+2σ)', 2, '#ff8c00', 'rgba(255, 140, 0, 0.1)'),
        ('p1s', '偏高 (+1σ)', 1, '#ffd700', 'rgba(255, 215, 0, 0.05)'),
        ('Mid', '趨勢中線 (Mid)', 0, '#00e676', 'rgba(0, 230, 118, 0.05)'),
        ('m1s', '偏低 (-1σ)', -1, '#2979ff', 'rgba(41, 121, 255, 0.1)'),
        ('m2s', '低估 (-2σ)', -2, '#aa00ff', 'rgba(170, 0, 255, 0.1)'),
        ('m3s', '極度低估 (-3σ)', -3, '#651fff', None)
    ]

    # A. 畫背景填充
    for i in range(len(configs)-1):
        upper = to_p(df['Mid_Log'] + configs[i][2] * sigma)
        lower = to_p(df['Mid_Log'] + configs[i+1][2] * sigma)
        fig.add_trace(go.Scatter(x=df.index, y=upper, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=df.index, y=lower, fill='tonexty', fillcolor=configs[i][4], line=dict(width=0), showlegend=False, hoverinfo='skip'))

    # B. 畫七條實體彩虹線 (讓線條清晰可見)
    for _, label, s_val, color, _ in configs:
        fig.add_trace(go.Scatter(
            x=df.index, y=to_p(df['Mid_Log'] + s_val * sigma),
            name=label, mode='lines',
            line=dict(color=color, width=1.2),
            marker=dict(size=6), # 設定 Marker 樣式但預設不顯示
            hovertemplate=f"{label}: %{{y:.2f}}<extra></extra>"
        ))

    # C. 畫收盤價 (白色加粗，置頂)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'], name="收盤價",
        mode='lines+markers',
        line=dict(color='white', width=2.5),
        marker=dict(size=7, color='white', opacity=0), # 懸停時自動出現白點
        hovertemplate="<b>日期: %{x|%Y-%m-%d}</b><br>收盤價: %{y:.2f}<extra></extra>"
    ))

    # D. 設定佈局：實現左圖的連動懸停
    fig.update_layout(
        template="plotly_dark", height=700, margin=dict(t=50, b=0, l=10, r=10),
        hovermode="x", # 關鍵：滑鼠滑過 X 軸某點，顯示所有 Trace 的點
        xaxis=dict(showgrid=False, rangeslider=dict(visible=True, thickness=0.05)),
        yaxis=dict(gridcolor='#23282e', side='right', type='log' if is_log else 'linear'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    # 5. 下方數據面板
    last_close = df['Close'].iloc[-1]
    last_log_mid = df['Mid_Log'].iloc[-1]
    curr_z = (np.log(last_close) - last_log_mid) / sigma if is_log else (last_close - last_log_mid) / sigma
    
    ma1, ma2, ma3, ma4 = st.columns(4)
    ma1.markdown(f'<div class="data-card"><div class="metric-label">當前收盤價</div><div class="metric-val">${last_close:.2f}</div></div>', unsafe_allow_html=True)
    ma2.markdown(f'<div class="data-card"><div class="metric-label">當前水位</div><div class="metric-val">{curr_z:.2f} σ</div></div>', unsafe_allow_html=True)
    ma3.markdown(f'<div class="data-card"><div class="metric-label">年化報酬率</div><div class="metric-val">{ann_r:.1f}%</div></div>', unsafe_allow_html=True)
    ma4.markdown(f'<div class="data-card"><div class="metric-label">標準差 (σ)</div><div class="metric-val">{sigma:.4f}</div></div>', unsafe_allow_html=True)

else:
    # 當被 Yahoo 封鎖時顯示的提示
    st.error("📉 數據連線暫時中斷")
    if "Too Many Requests" in error_msg or "Rate limit" in error_msg:
        st.warning("Yahoo Finance 暫時限制了伺服器的存取頻率。")
        st.info("💡 **別擔心，這不是程式問題！** 請嘗試以下動作：\n1. 稍等 1-5 分鐘後重新整理。\n2. 點擊右下角 'Manage app' -> 'Reboot App' 嘗試更換伺服器 IP。")
    else:
        st.info(f"系統訊息：{error_msg}")