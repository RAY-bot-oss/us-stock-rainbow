import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import timedelta

# 1. 極致簡潔網頁配置
st.set_page_config(page_title="財富彩虹橋-Tomosware復刻版", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    /* 隱藏 streamlit 預設元件 */
    #MainMenu, footer, header {visibility: hidden;}
    .reportview-container .main .block-container{ padding-top: 1rem; }
    
    /* 看板樣式 (精簡版) */
    .dashboard-container {
        display: flex; gap: 30px; margin-bottom: 15px; align-items: center; 
        font-family: sans-serif;
    }
    .db-title { font-size: 28px; font-weight: bold; color: #ffffff; }
    .z-score-badge {
        background: rgba(255, 215, 0, 0.1); color: #ffd700; 
        padding: 5px 15px; border-radius: 6px; font-size: 16px; border: 1px solid #ffd700;
    }
    .db-info-item { font-size: 14px; color: #8b949e; }
    .db-info-value { color: #ffffff; font-weight: bold; margin-left: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 精簡輸入區
ticker_col, period_col = st.columns([1, 4])
with ticker_col:
    raw_ticker = st.text_input("輸入代碼", "00981A", label_visibility="collapsed").upper()
    if raw_ticker.isdigit() or raw_ticker.endswith('A'):
        ticker_input = f"{raw_ticker}.TW"
    else:
        ticker_input = raw_ticker
with period_col:
    # 預設為 3Y
    period_label = st.selectbox("範圍", ["1Y", "3Y", "5Y"], index=1, label_visibility="collapsed")
    days_map = {"1Y": 245, "3Y": 735, "5Y": 1225}
    target_days = days_map[period_label]

# 3. 核心大腦：對數回歸與未來預測生成 (實現直線)
@st.cache_data(ttl=3600)
def get_calibrated_forecast(symbol, days):
    try:
        # 下載歷史數據
        df_raw = yf.Ticker(symbol).history(period="10y")
        if df_raw.empty: return None, "找不到數據"
        df = df_raw.tail(days).copy()
        
        # 1. 計算歷史回歸 (使用對數)
        X_hist = np.arange(len(df)).reshape(-1, 1)
        y_log_hist = np.log(df['Close'].values)
        model = LinearRegression().fit(X_hist, y_log_hist)
        sigma = (y_log_hist - model.predict(X_hist)).std()
        
        slope = model.coef_[0]
        ann_return = (np.exp(slope * 252) - 1) * 100
        
        # 2. 生成未來預測時間軸 (對齊右圖延伸效果)
        forecast_days = 30 # 人工生成未來30天預測
        last_date = df.index[-1]
        forecast_dates = [last_date + timedelta(days=i) for i in range(1, forecast_days + 1)]
        
        # 合併時間軸
        total_dates = df.index.tolist() + forecast_dates
        # 生成總 X 軸編號 (用於計算回歸線)
        X_total = np.arange(len(total_dates)).reshape(-1, 1)
        y_log_total_mid = model.predict(X_total)
        
        # 3. 準備 Plotly 所需的數據 dataframe (包含歷史和預測)
        df_plot = pd.DataFrame(index=total_dates)
        # 收盤價 (未來部分為 NaN)
        df_plot['Close'] = df['Close'].reindex(total_dates)
        
        # 核心：直接存儲對數值 (Log Values)，這是 Plotly 畫直線的關鍵
        df_plot['Mid_Log'] = y_log_total_mid
        df_plot['P1s_Log'] = y_log_total_mid + 1 * sigma
        df_plot['P2s_Log'] = y_log_total_mid + 2 * sigma
        df_plot['P3s_Log'] = y_log_total_mid + 3 * sigma
        df_plot['M1s_Log'] = y_log_total_mid - 1 * sigma
        df_plot['M2s_Log'] = y_log_total_mid - 2 * sigma
        df_plot['M3s_Log'] = y_log_total_mid - 3 * sigma
        
        # Z-Score 計算
        curr_z = (y_log_hist[-1] - y_log_total_mid[len(df)-1]) / sigma
        
        return (df_plot, df.index, ann_return, symbol, curr_z), None
    except Exception as e:
        return None, str(e)

res_data, err = get_calibrated_forecast(ticker_input, target_days)

if res_data:
    df_plot, hist_index, ann_r, final_ticker, curr_z = res_data
    # 歷史最後一天價格
    last_close = df_plot['Close'].loc[hist_index[-1]]
    
    # 看板資訊 (對齊 Tomosware 樣式)
    st.markdown(f"""
    <div class="dashboard-container">
        <div class="db-title">{final_ticker.replace('.TW','')}</div>
        <div class="z-score-badge">Z-Score: {curr_z:.2f}</div>
        <div class="db-info-item">年化報酬: <span class="db-info-value">{ann_r:.1f}%</span></div>
        <div class="db-info-item">收盤價: <span class="db-info-value">{last_close:.2f}</span></div>
        <div class="db-info-item">範圍: <span class="db-info-value">{len(hist_index)} 天</span></div>
    </div>
    """, unsafe_allow_html=True)

    # 4. 繪製圖表：標準 Tomosware 極致直線風格
    fig = go.Figure()

    # 彩虹線配置 (Sigma 值, 顏色, 標籤)
    line_configs = [
        (3, '#ff4b4b', 'Over Valued (+3)'), (2, '#ff8c00', 'Over Valued (+2)'), (1, '#ffd700', 'Over Valued (+1)'),
        (0, '#00e676', 'Mid'), 
        (-1, '#2979ff', 'Under Valued (-1)'), (-2, '#aa00ff', 'Under Valued (-2)'), (-3, '#651fff', 'Under Valued (-3)')
    ]

    # A. 先繪製收盤價線 (白色，只畫到歷史數據，不延伸)
    # 這裡是關鍵：收盤價是實體價格，所以我們要對其取對數 `np.log(df_plot['Close'])`
    # 這樣它才能在對數座標 Y 軸上正確顯示
    fig.add_trace(go.Scatter(
        x=df_plot.index, y=np.log(df_plot['Close']), name="收盤價",
        mode='lines', line=dict(color='white', width=2.5),
        connectgaps=False, # 未來預測區段不連線
        hovertemplate="Price: %{y:.2f}"
    ))

    # B. 繪製 7 條標準差預測線段 (完美直線且彼此平行)
    log_cols = ['P3s_Log', 'P2s_Log', 'P1s_Log', 'Mid_Log', 'M1s_Log', 'M2s_Log', 'M3s_Log']
    
    for i, (s_val, color, label) in enumerate(line_configs):
        # 這裡是解決直線問題的核心：直接把 Log 值交給 Plotly
        fig.add_trace(go.Scatter(
            x=df_plot.index, y=df_plot[log_cols[i]],
            name=label, mode='lines',
            line=dict(color=color, width=1.3),
            hovertemplate=f"{label}: %{{y:.2f}}"
        ))

    # 5. 設定佈局：實現「價格偽裝」與「極致直線」
    
    # 關鍵：為了讓 Y 軸顯示價格而不是 Log 值，我們要定義刻度
    # 我們取價格的最大和最小值，生成實體價格刻度
    y_min_price = df_plot['Close'].min(skipna=True) * 0.9
    y_max_price = np.exp(df_plot['P3s_Log'].max()) * 1.1
    # 生成合理的實體價格刻度 (例如: 10, 15, 20, 25)
    tick_vals_price = np.linspace(y_min_price, y_max_price, 8).round(1)
    
    fig.update_layout(
        template="plotly_dark", height=750,
        # A. X 軸移除無用網格，對齊右圖
        xaxis=dict(showgrid=False), 
        
        # B. 關鍵：Y軸佈局
        yaxis=dict(
            side='right', gridcolor='#1e2228', 
            # 這裡是「價格偽裝」的秘訣：
            # 我們將 Y 軸設定為對數刻度，並手動定義 tickvals 和 ticktext
            type='log', # 告訴 Plotly，我給你的是 Log 值
            tickvals=np.log(tick_vals_price), # 告訴 Plotly，要在這些 Log 值的位置畫刻度
            ticktext=[str(v) for v in tick_vals_price], # 但刻度上要顯示實體價格
        ),
        
        # C. 移除 Rangeslider (滑塊)，對齊右圖
        xaxis_rangeslider_visible=False,
        # D. 懸停模式：x unified (八點連動)
        hovermode="x unified",
        margin=dict(t=10, b=10, l=10, r=60), # 縮小邊距
        
        # E. 圖例置於左上角，垂直排列
        legend=dict(
            orientation="v", yanchor="top", y=0.98, 
            xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0)"
        )
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.error(f"數據抓取失敗：{err}")