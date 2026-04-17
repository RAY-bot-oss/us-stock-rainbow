import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# 1. 網頁配置
st.set_page_config(page_title="財富彩虹橋-專業版", layout="wide")

# 完全模擬左圖的深色美學 CSS
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .dashboard-container {
        background-color: #161b22; border: 1px solid #30363d;
        border-radius: 12px; padding: 20px; display: flex; 
        justify-content: space-between; align-items: center; margin-bottom: 25px;
    }
    .db-item { text-align: center; flex: 1; border-right: 1px solid #30363d; }
    .db-item:last-child { border-right: none; }
    .db-label { font-size: 13px; color: #8b949e; margin-bottom: 5px; }
    .db-value { font-size: 20px; font-weight: bold; color: #ffffff; }
    .z-score-badge {
        background: #3d1a1a; color: #ff4b4b; padding: 10px 25px;
        border-radius: 8px; font-size: 26px; font-weight: bold; margin-right: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 頂部控制列
c1, c2 = st.columns([4, 2])
with c1:
    ticker_input = st.text_input("輸入代碼", "00981A.TW").upper()
with c2:
    period_label = st.selectbox("時間範圍", ["1Y", "3Y", "5Y", "10Y"], index=1)
    p_map = {"1Y": "252d", "3Y": "756d", "5Y": "1260d", "10Y": "2520d"}

# 3. 核心數據處理 (對數線性回歸)
@st.cache_data(ttl=3600)
def get_wealth_data(symbol, p_str):
    try:
        df = yf.Ticker(symbol).history(period=p_str)
        if df.empty: return None, "無數據"
        
        df['Idx'] = np.arange(len(df))
        X = df[['Idx']].values
        y_log = np.log(df['Close'].values)
        
        # 執行對數回歸
        model = LinearRegression().fit(X, y_log)
        df['Log_Mid'] = model.predict(X)
        log_std = (y_log - df['Log_Mid']).std()
        
        # 斜率推算年化報酬
        slope = model.coef_[0]
        ann_return = (np.exp(slope * 252) - 1) * 100
        
        return (df, log_std, ann_return), None
    except Exception as e:
        return None, str(e)

res, err = get_wealth_data(ticker_input, p_map[period_label])

if res:
    df, sigma, ann_r = res
    last_close = df['Close'].iloc[-1]
    last_log_mid = df['Log_Mid'].iloc[-1]
    z_score = (np.log(last_close) - last_log_mid) / sigma

    # 4. 頂部數據儀表板 (模擬左圖)
    st.markdown(f"""
    <div class="dashboard-container">
        <div style="display:flex; align-items:center; flex: 2; border-right: 1px solid #30363d;">
            <div style="margin-right:20px; padding-left: 10px;">
                <b style="font-size:22px;">{ticker_input}</b><br>
                <span style="color:#8b949e; font-size:13px;">統一台灣高息優選基金</span>
            </div>
            <div class="z-score-badge">{z_score:.2f}<br><span style="font-size:12px;">+3σ</span></div>
        </div>
        <div class="db-item"><div class="db-label">收盤價</div><div class="db-value">{last_close:.2f}</div></div>
        <div class="db-item"><div class="db-label">年化報酬率</div><div class="db-value">{ann_r:.1f}%</div></div>
        <div class="db-item"><div class="db-label">交易日數</div><div class="db-value">{len(df)} / 735</div></div>
        <div class="db-item"><div class="db-label">最後交易日</div><div class="db-value">{df.index[-1].strftime('%Y-%m-%d')}</div></div>
    </div>
    """, unsafe_allow_html=True)

    # 5. 繪製究極圖表
    fig = go.Figure()

    # 彩虹線配置
    configs = [
        (3, '#ff4b4b', '極度高估 (+3σ)'), (2, '#ff8c00', '高估 (+2σ)'), (1, '#ffd700', '偏高 (+1σ)'),
        (0, '#00e676', '中線 (Mid)'), (-1, '#2979ff', '偏低 (-1σ)'), (-2, '#aa00ff', '低估 (-2σ)'), (-3, '#651fff', '極度低估 (-3σ)')
    ]
    
    # 畫背景填充
    fill_colors = ['rgba(255,75,75,0.08)', 'rgba(255,140,0,0.08)', 'rgba(255,215,0,0.04)', 'rgba(0,230,118,0.04)', 'rgba(41,121,255,0.08)', 'rgba(170,0,255,0.08)']
    for i in range(len(configs)-1):
        up_val = np.exp(df['Log_Mid'] + configs[i][0] * sigma)
        low_val = np.exp(df['Log_Mid'] + configs[i+1][0] * sigma)
        fig.add_trace(go.Scatter(x=df.index, y=up_val, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=df.index, y=low_val, fill='tonexty', fillcolor=fill_colors[i], line=dict(width=0), showlegend=False, hoverinfo='skip'))

    # 畫七條實體彩虹線 + 設定 Marker
    for s_val, color, label in configs:
        y_val = np.exp(df['Log_Mid'] + s_val * sigma)
        fig.add_trace(go.Scatter(
            x=df.index, y=y_val, name=label,
            mode='lines', line=dict(color=color, width=1.5),
            marker=dict(size=6, opacity=0), # 關鍵：markers設為透明，x-unified模式會自動在懸停時點亮它
            hovertemplate=f"{label}: %{{y:.2f}}<extra></extra>"
        ))

    # 畫白色收盤價 (置頂)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'], name="收盤價",
        mode='lines', line=dict(color='white', width=2.5),
        marker=dict(size=8, color='white', opacity=0),
        hovertemplate="收盤價: %{y:.2f}<extra></extra>"
    ))

    # 6. 圖表 Layout 優化 (連動懸停與直線質感的關鍵)
    fig.update_layout(
        template="plotly_dark", height=750, margin=dict(t=30, b=0, l=10, r=10),
        hovermode="x unified", # 核心：產生垂直線並連動所有圓圈
        hoverlabel=dict(bgcolor="rgba(0,0,0,0.8)", font_size=13),
        xaxis=dict(showgrid=False, rangeslider=dict(visible=True, thickness=0.05)),
        yaxis=dict(
            gridcolor='#23282e', side='right', 
            type='log', # 核心：強制對數座標軸，確保平行直線
            tickformat='.1f'
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # 強制所有線條在懸停時顯示圓點
    fig.update_traces(hoveron='points')

    st.plotly_chart(fig, use_container_width=True)

else:
    st.error(f"數據抓取失敗：{err}")