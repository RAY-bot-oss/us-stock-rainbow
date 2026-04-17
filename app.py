import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# 1. 網頁配置與自定義 CSS (完全還原左圖看板質感)
st.set_page_config(page_title="財富彩虹橋-專業版", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .dashboard-container {
        background-color: #161b22; border: 1px solid #30363d;
        border-radius: 12px; padding: 15px 25px; display: flex; 
        justify-content: space-between; align-items: center; margin-bottom: 20px;
    }
    .db-item { text-align: center; flex: 1; border-right: 1px solid #333; }
    .db-item:last-child { border-right: none; }
    .db-label { font-size: 13px; color: #8b949e; margin-bottom: 4px; }
    .db-value { font-size: 20px; font-weight: bold; color: #ffffff; }
    .z-score-badge {
        background: rgba(255, 75, 75, 0.15); color: #ff4b4b; 
        padding: 8px 20px; border-radius: 8px; text-align: center;
        min-width: 80px; margin-right: 25px; border: 1px solid #ff4b4b;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 頂部輸入區 (整合美股/台股自動處理)
col_input, col_period = st.columns([4, 2])
with col_input:
    raw_ticker = st.text_input("輸入代碼 (例如: 00981A, AAPL, 2330)", "00981A").upper()
    # 自動補齊台股後綴
    if raw_ticker.isdigit() or raw_ticker.endswith('A') or raw_ticker.endswith('B'):
        ticker_input = f"{raw_ticker}.TW"
    else:
        ticker_input = raw_ticker

with col_period:
    period_label = st.selectbox("時間範圍", ["1Y (245天)", "3Y (735天)", "5Y (1225天)"], index=1)
    # 根據你提供的 JSON，3Y 對應的是 735 個交易日
    days_map = {"1Y (245天)": 245, "3Y (735天)": 735, "5Y (1225天)": 1225}
    target_days = days_map[period_label]

# 3. 數據獲取與對數回歸算法 (核心大腦)
@st.cache_data(ttl=3600)
def get_calibrated_data(symbol, days):
    try:
        # 抓取較長數據以確保 tail(days) 準確
        df = yf.Ticker(symbol).history(period="10y")
        if df.empty: return None, "找不到該標的數據"
        
        # 根據所選範圍切割數據
        df = df.tail(days).copy()
        
        # 執行與 Tomosware 一致的 Log 線性回歸
        df['X'] = np.arange(len(df))
        X_reg = df[['X']].values
        y_log = np.log(df['Close'].values)
        
        model = LinearRegression().fit(X_reg, y_log)
        df['Mid_Log'] = model.predict(X_reg)
        sigma = (y_log - df['Mid_Log']).std()
        
        # 年化報酬率計算
        slope = model.coef_[0]
        ann_return = (np.exp(slope * 252) - 1) * 100
        
        return (df, sigma, ann_return, symbol), None
    except Exception as e:
        return None, str(e)

res_data, err = get_calibrated_data(ticker_input, target_days)

if res_data:
    df, std, ann_r, final_ticker = res_data
    last_close = df['Close'].iloc[-1]
    last_log_mid = df['Mid_Log'].iloc[-1]
    curr_z = (np.log(last_close) - last_log_mid) / std
    
    # 名稱修正 (針對 00981A)
    display_name = "統一台灣高息優選基金" if "00981A" in final_ticker else final_ticker

    # 4. 頂部儀表板 (還原左圖五大指標)
    st.markdown(f"""
    <div class="dashboard-container">
        <div style="display:flex; align-items:center; flex: 2; border-right: 1px solid #333;">
            <div style="margin-right:20px;">
                <b style="font-size:22px;">{final_ticker.replace('.TW','')}</b><br>
                <span style="color:#8b949e; font-size:13px;">{display_name}</span>
            </div>
            <div class="z-score-badge">
                <div style="font-size:20px;">{curr_z:.2f}</div>
                <div style="font-size:10px; opacity:0.8;">{"+3σ" if curr_z > 3 else "Z-Score"}</div>
            </div>
        </div>
        <div class="db-item"><div class="db-label">收盤價</div><div class="db-value">{last_close:.2f}</div></div>
        <div class="db-item"><div class="db-label">年化報酬率</div><div class="db-value">{ann_r:.1f}%</div></div>
        <div class="db-item"><div class="db-label">交易日數</div><div class="db-value">{len(df)} / {target_days}</div></div>
        <div class="db-item"><div class="db-label">最後交易日</div><div class="db-value">{df.index[-1].strftime('%Y-%m-%d')}</div></div>
    </div>
    """, unsafe_allow_html=True)

    # 5. 繪製圖表 (強制平行直線與八點連動懸停)
    fig = go.Figure()

    # 彩虹線配置 (Sigma, 顏色, 標籤)
    line_configs = [
        (3, '#ff4b4b', '極度高估 (+3σ)'), (2, '#ff8c00', '高估 (+2σ)'), (1, '#ffd700', '偏高 (+1σ)'),
        (0, '#00e676', '中線 (Mid)'), (-1, '#2979ff', '偏低 (-1σ)'), (-2, '#aa00ff', '低估 (-2σ)'), (-3, '#651fff', '極度低估 (-3σ)')
    ]

    # A. 繪製半透明填充區
    fill_colors = ['rgba(255,75,75,0.08)', 'rgba(255,140,0,0.08)', 'rgba(255,215,0,0.04)', 'rgba(0,230,118,0.04)', 'rgba(41,121,255,0.08)', 'rgba(170,0,255,0.08)']
    for i in range(len(line_configs)-1):
        up = np.exp(df['Mid_Log'] + line_configs[i][0] * std)
        low = np.exp(df['Mid_Log'] + line_configs[i+1][0] * std)
        fig.add_trace(go.Scatter(x=df.index, y=up, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=df.index, y=low, fill='tonexty', fillcolor=fill_colors[i], line=dict(width=0), showlegend=False, hoverinfo='skip'))

    # B. 繪製 7 條實體平行線 (加上點亮效果)
    for s_val, color, label in line_configs:
        y_vals = np.exp(df['Mid_Log'] + s_val * std)
        fig.add_trace(go.Scatter(
            x=df.index, y=y_vals, name=label,
            mode='lines', line=dict(color=color, width=1.5),
            marker=dict(size=6, opacity=0), # 關鍵：markers 設為透明，在 x-unified 模式會自動出現
            hovertemplate=f"{label}: %{{y:.2f}}<extra></extra>"
        ))

    # C. 繪製收盤價線 (白色加粗置頂)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'], name="收盤價",
        mode='lines', line=dict(color='white', width=2.5),
        marker=dict(size=8, color='white', line=dict(width=2, color='white'), opacity=0),
        hovertemplate="收盤價: %{y:.2f}<extra></extra>"
    ))

    # D. 設定佈局：實現「八點連動」的秘訣
    fig.update_layout(
        template="plotly_dark", height=750, margin=dict(t=50, b=0, l=10, r=10),
        hovermode="x unified", # 這是出現八個小圓圈最關鍵的設定
        xaxis=dict(showgrid=False, rangeslider=dict(visible=True, thickness=0.04)),
        yaxis=dict(
            gridcolor='#23282e', side='right', 
            type='log', # 這是讓線條變完美直線的關鍵
            tickformat='.1f'
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # 確保所有 Trace 都在懸停時顯示 Marker
    fig.update_traces(hoveron='points', mode='lines+markers')

    st.plotly_chart(fig, use_container_width=True)

else:
    st.error(f"數據抓取失敗：{err}")