# 5. 繪製圖表 (強化視覺線條與七點連動懸停)
fig = go.Figure()

# 定義彩虹層級的名稱與顏色
# 順序：+3s, +2s, +1s, Mid, -1s, -2s, -3s
line_configs = [
    ('p3s', '極度高估 (+3σ)', 'rgba(255, 0, 0, 1)', 'rgba(255, 0, 0, 0.1)'),
    ('p2s', '高估 (+2σ)', 'rgba(255, 165, 0, 1)', 'rgba(255, 165, 0, 0.1)'),
    ('p1s', '偏高 (+1σ)', 'rgba(255, 255, 0, 1)', 'rgba(255, 255, 0, 0.05)'),
    ('Mid', '趨勢中線 (Mid)', 'rgba(0, 255, 0, 1)', 'rgba(0, 255, 0, 0.05)'),
    ('m1s', '偏低 (-1σ)', 'rgba(0, 0, 255, 1)', 'rgba(0, 0, 255, 0.1)'),
    ('m2s', '低估 (-2σ)', 'rgba(128, 0, 128, 1)', 'rgba(128, 0, 128, 0.1)'),
    ('m3s', '極度低估 (-3σ)', 'rgba(75, 0, 130, 1)', None)
]

# A. 先畫區間填滿 (為了讓填滿在線條下面)
for i in range(len(line_configs) - 1):
    up_key = line_configs[i][0]
    low_key = line_configs[i+1][0]
    fill_col = line_configs[i][3]
    
    fig.add_trace(go.Scatter(
        x=df.index, y=get_y(df[up_key]), mode='lines', 
        line=dict(width=0), showlegend=False, hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=get_y(df[low_key]), fill='tonexty', 
        fillcolor=fill_col, line=dict(width=0), showlegend=False, hoverinfo='skip'
    ))

# B. 再畫「七條邊界線」 (這能解決模糊感，產生清晰的線條)
for key, name, color, _ in line_configs:
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=get_y(df[key]),
        name=name,
        mode='lines',
        line=dict(color=color, width=1), # 這裡設定線條顏色與寬度
        hovertemplate=f"{name}: %{{y:.2f}}<extra></extra>"
    ))

# C. 最後畫收盤價 (白色加粗，並置於最頂層)
fig.add_trace(go.Scatter(
    x=df.index, 
    y=df['Close'], 
    name="收盤價",
    mode='lines+markers',
    marker=dict(size=4, color='white', opacity=0), # 平時隱藏圓點，懸停才出現
    line=dict(color='white', width=2.5),
    hovertemplate="<b>日期: %{x}</b><br>收盤價: %{y:.2f}<extra></extra>"
))

# 6. 圖表版面設定 (關鍵在於 hovermode='x')
fig.update_layout(
    template="plotly_dark",
    height=650,
    margin=dict(t=50, b=0, l=10, r=10),
    hovermode="x", # 關鍵：滑鼠指到 X 軸某點，會觸發該點所有線條的圓圈與數值
    xaxis=dict(
        showgrid=False, 
        rangeslider=dict(visible=True, thickness=0.04),
        spikemode="across", spikethickness=1, spikedash="dot", spikecolor="#999" # 垂直輔助線
    ),
    yaxis=dict(
        gridcolor='#23282e', 
        side='right', 
        type='log' if is_log else 'linear',
        fixedrange=False
    ),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)