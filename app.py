import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import timedelta

# 1. 頁面極簡化配置
st.set_page_config(page_title="財富彩虹橋", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    #MainMenu, footer, header {visibility: hidden;}
    .dashboard-container {
        display: flex; gap: 30px; margin-bottom: 10px; align-items: center; padding: 10px 0;
    }
    .db-title { font-size: 28px; font-weight: bold; color: #ffffff; }
    .z-score-badge {
        background: rgba(255, 215, 0, 0.1); color: #ffd700; 
        padding: 5px 15px; border-radius: 6px; font-size: 18px; border: 1px solid #ffd700;
    }
    .db-info-item { font-size: 14px; color: #8b949e; }
    .db-info-value { color: #ffffff; font-weight: bold; margin-left: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 精簡輸入列
ticker_col, period_col = st.columns([1, 4])
with ticker_col:
    raw_ticker = st.text_input("輸入代碼", "00981A", label_visibility="collapsed").upper()
    ticker_input = f"{raw_ticker}.TW" if (raw_ticker.isdigit() or raw_ticker.endswith('A')) else raw_ticker
with period_col:
    period_label = st.selectbox("範圍", ["1Y", "3Y", "5Y"], index=1, label_visibility="collapsed")
    days_map = {"1Y": 245, "3Y": 735, "5Y": 1225}
    target_days = days_map[period_label]

# 3. 核心大腦：絕對直線對數回歸
@st.cache_data(ttl=3600)
def get_wealth_rainbow_data(symbol, days):
    try:
        stock = yf.Ticker(symbol)
        df_raw = stock.history(period="5y")
        if df_raw.empty: return None, "無數據"
        df = df_raw.tail(days).copy()
        
        # 建立時間索引
        X = np.arange(len(df)).reshape(-1, 1)
        y_log = np.log(df['Close'].values)
        
        # 線性回歸 (在 Log 空間內，這就是直線)
        model = LinearRegression().fit(X, y_log)
        sigma = (y_log - model.predict(X)).std()
        slope = model.coef_[0]
        
        # 預測未來 45 天 (讓線段延伸，不中斷)
        forecast_days = 45
        last_date = df.index[-1]
        future_dates = [last_date + timedelta(days=i) for i in range(1, forecast_days + 1)]
        total_dates = df.index.tolist() + future_dates
        
        # 計算總時間軸的 Log 線段
        X_total = np.arange(len(total_dates)).reshape(-1, 1)
        y_log_total = model.predict(X_total)
        
        ann_return = (np.exp(slope * 252) - 1) * 100
        curr_z = (y_log[-1] - y_log_total[len(df)-1]) / sigma
        
        return (total_dates, df['Close'], y_log_total, sigma, ann_return, curr_z), None
    except Exception as e:
        return None, str(e)

res, err = get_wealth_rainbow_data(ticker_input, target_days)

if res:
    dates, close_price, y_log_mid, sigma, ann_r, curr_z = res
    
    # 頂部看板 (復刻介面)
    st.markdown(f"""
    <div class="dashboard-container">
        <div class="db-title">{raw_ticker}</div>
        <div class="z-score-badge">Z-Score: {curr_z:.2f}</div>
        <div class="db-info-item">年化報酬: <span class="db-info-value">{ann_r:.1f}%</span></div>
        <div class="db-info-item">收盤價: <span class="db-info-value">{close_price.iloc[-1]:.2f}</span></div>
        <div class="db-info-item">資料天數: <span class="db-info-value">{len(close_price)}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # 4. 繪製圖表
    fig = go.Figure()

    # 彩虹線配置
    line_configs = [
        (3, '#ff4b4b', 'Over Valued (+3σ)'), (2, '#ff8c00', 'Over Valued (+2σ)'), (1, '#ffd700', 'Over Valued (+1σ)'),
        (0, '#00e676', 'Mid'),
        (-1, '#2979ff', 'Under Valued (-1σ)'), (-2, '#aa00ff', 'Under Valued (-2σ)'), (-3, '#651fff', 'Under Valued (-3σ)')
    ]

    # A. 畫收盤價 (只取有數據的部分)
    # 我們將 Y 軸數據保持為原始價格，但設定 Y 軸類型為 Log
    fig.add_trace(go.Scatter(
        x=close_price.index, y=close_price, name="收盤價",
        mode='lines', line=dict(color='white', width=2.5),
        hovertemplate="Price: %{y:.2f}"
    ))

    # B. 畫七條彩虹直線
    for s_val, color, label in line_configs:
        # 關鍵：這裡使用 np.exp 將 Log 空間預測轉回實體價格
        # 在 Log 座標軸下，這會呈現為完美的平行直線
        y_prices = np.exp(y_log_mid + s_val * sigma)
        fig.add_trace(go.Scatter(
            x=dates, y=y_prices, name=label,
            mode='lines', line=dict(color=color, width=1.3),
            hovertemplate=f"{label}: %{{y:.2f}}"
        ))

    # 5. 圖表 Layout 設定 (達成絕對平行的關鍵)
    fig.update_layout(
        template="plotly_dark", height=750,
        hovermode="x unified",
        margin=dict(t=10, b=10, l=10, r=60),
        xaxis=dict(showgrid=False, rangeslider_visible=False),
        yaxis=dict(
            type='log', # 這是靈魂：對數座標軸讓增長曲線變直線
            side='right', 
            gridcolor='#1e2228',
            tickformat='.1f',
            dtick=0.1 # 強制固定刻度間距，增加平行感
        ),
        legend=dict(
            orientation="v", yanchor="top", y=0.98, 
            xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0)"
        )
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.error(f"數據抓取失敗：{err}")