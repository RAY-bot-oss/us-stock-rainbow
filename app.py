import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# 1. 網頁配置與基礎 CSS (簡潔風)
st.set_page_config(page_title="財富彩虹橋", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .dashboard-container {
        display: flex; gap: 20px; margin-bottom: 20px; align-items: center;
    }
    .db-title { font-size: 24px; font-weight: bold; color: #ffffff; }
    .z-score-badge {
        background: rgba(255, 215, 0, 0.1); color: #ffd700; 
        padding: 5px 15px; border-radius: 6px; font-size: 16px; border: 1px solid #ffd700;
    }
    .db-info { font-size: 14px; color: #8b949e; }
    </style>
    """, unsafe_allow_html=True)

# 2. 輸入與時間範圍選擇 (簡潔佈局)
col_input, col_period = st.columns([4, 2])
with col_input:
    raw_ticker = st.text_input("輸入代碼", "00981A").upper()
    if raw_ticker.isdigit() or raw_ticker.endswith('A'):
        ticker_input = f"{raw_ticker}.TW"
    else:
        ticker_input = raw_ticker

with col_period:
    period_label = st.selectbox("時間範圍", ["1Y", "3Y", "5Y"], index=1)
    days_map = {"1Y": 245, "3Y": 735, "5Y": 1225}
    target_days = days_map[period_label]

# 3. 核心大腦：對數線性回歸 (精確計算)
@st.cache_data(ttl=3600)
def get_calibrated_data(symbol, days):
    try:
        # 下載較長數據以切割精確日數
        df_raw = yf.Ticker(symbol).history(period="10y")
        if df_raw.empty: return None, "找不到數據"
        
        # 只取最後所需的日數 (對齊 trade_days_used)
        df = df_raw.tail(days).copy()
        
        # 執行 Log 線性回歸
        df['X'] = np.arange(len(df))
        X_reg = df[['X']].values
        y_log = np.log(df['Close'].values)
        
        model = LinearRegression().fit(X_reg, y_log)
        df['Mid_Log'] = model.predict(X_reg)
        sigma = (y_log - df['Mid_Log']).std()
        
        # 計算 Z-Score
        last_close = df['Close'].iloc[-1]
        last_log_mid = df['Mid_Log'].iloc[-1]
        curr_z = (np.log(last_close) - last_log_mid) / sigma
        
        # 報酬率
        slope = model.coef_[0]
        ann_return = (np.exp(slope * 252) - 1) * 100
        
        return (df, sigma, ann_return, symbol, curr_z), None
    except Exception as e:
        return None, str(e)

res_data, err = get_calibrated_data(ticker_input, target_days)

if res_data:
    df, std, ann_r, final_ticker, curr_z = res_data
    last_close = df['Close'].iloc[-1]
    
    # 看板資訊
    st.markdown(f"""
    <div class="dashboard-container">
        <div class="db-title">{final_ticker.replace('.TW','')}</div>
        <div class="z-score-badge">Z-Score: {curr_z:.2f}</div>
        <div class="db-info">
            年化報酬: {ann_r:.1f}% | 收盤價: {last_close:.2f} | 交易日數: {len(df)} 天
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 4. 繪製圖表：標準 Tomosware 簡潔直線風格
    fig = go.Figure()

    # 彩虹線配置 (Sigma 值, 顏色, 標籤)
    line_configs = [
        (3, '#ff4b4b', 'Over Valued (+3)'), (2, '#ff8c00', 'Over Valued (+2)'), (1, '#ffd700', 'Over Valued (+1)'),
        (0, '#00e676', 'Mid'), 
        (-1, '#2979ff', 'Under Valued (-1)'), (-2, '#aa00ff', 'Under Valued (-2)'), (-3, '#651fff', 'Under Valued (-3)')
    ]

    # A. 先繪製收盤價線 (白色加粗，置於底層)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'], name="收盤價",
        mode='lines', line=dict(color='white', width=2),
        hovertemplate="Price: %{y:.2f}"
    ))

    # B. 繪製 7 條標準差線段 (完美直線且平行)
    for s_val, color, label in line_configs:
        # 這裡是關鍵：我們只畫線，完全不加填充區 (fill='none')
        # Plotly 會自動處理 yaxis type='log'，讓對數回歸線在視覺上變直線
        fig.add_trace(go.Scatter(
            x=df.index, y=np.exp(df['Mid_Log'] + s_val * std),
            name=label, mode='lines',
            line=dict(color=color, width=1.2),
            hovertemplate=f"{label}: %{{y:.2f}}"
        ))

    # 5. 設定佈局：實現「極致簡潔」與「直線感」
    fig.update_layout(
        template="plotly_dark", height=700,
        # A. 關鍵：Y軸設為對數 (Log Axis)，這是讓斜率呈現筆直線段的唯一方法
        yaxis=dict(
            type='log', gridcolor='#1e2228', side='right', # 網格淡色
            tickformat='.1f', dtick=np.log10(last_close) / 10 # 自動計算刻度
        ),
        xaxis=dict(showgrid=False), # X軸移除網格
        
        # B. 移除 Rangeslider (滑塊)，對齊右圖
        # C. 懸停模式：x unified (八點連動)
        hovermode="x unified",
        margin=dict(t=10, b=10, l=10, r=60), # 縮小邊距
        
        # D. 圖例置於左上角，垂直排列
        legend=dict(
            orientation="v", yanchor="top", y=0.98, 
            xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0)"
        )
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.error(f"數據抓取失敗：{err}")