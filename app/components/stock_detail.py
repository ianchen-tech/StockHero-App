import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data.database.db_manager import DatabaseManager
import os
from datetime import datetime, timedelta


def render(state=None):
    if state is None:
        state = {}
        
    st.markdown("# 📈 股票詳情")
    
    # 初始化資料庫連接
    db = DatabaseManager(
        db_path=os.getenv('DB_PATH', 'StockHero.db'),
        bucket_name=os.getenv('BUCKET_NAME', 'ian-line-bot-files')
    )
    db.connect()
    
    try:
        # 定義股票代碼更新的回調函數
        def on_stock_id_change():
            new_stock_id = st.session_state.stock_id_input
            state['stock_id'] = new_stock_id
            # 清除日期選擇的狀態，因為新的股票可能有不同的日期範圍
            state.pop('start_date', None)
            state.pop('end_date', None)

        # 搜尋框
        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            stock_id = st.text_input(
                "請輸入股票代碼",
                value=state.get('stock_id', ''),
                placeholder="例如: 2330",
                key="stock_id_input",
                on_change=on_stock_id_change
            )
        
        if stock_id:
            # 取得該股票的最早和最晚交易日期
            date_range_query = """
                SELECT MIN(date) as min_date, MAX(date) as max_date
                FROM stock_daily
                WHERE stock_id = ?
            """
            date_range = db.conn.execute(date_range_query, [stock_id]).fetchdf()
            
            if not date_range.empty:
                # 直接使用 Timestamp 對象
                min_date = date_range['min_date'].iloc[0]
                max_date = date_range['max_date'].iloc[0]
                
                # 將 Timestamp 轉換為 datetime.date 對象
                min_date = min_date.date()
                max_date = max_date.date()
                
                # 定義日期更新的回調函數
                def on_start_date_change():
                    state['start_date'] = st.session_state.start_date_input

                def on_end_date_change():
                    state['end_date'] = st.session_state.end_date_input
                
                # 從狀態中讀取之前的日期，如果沒有則使用預設值
                default_start = max_date - timedelta(days=90)
                default_end = max_date
                
                # 日期選擇器
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input(
                        "開始日期",
                        value=state.get('start_date', default_start),
                        min_value=min_date,
                        max_value=max_date,
                        key="start_date_input",
                        on_change=on_start_date_change
                    )
                    
                with col2:
                    end_date = st.date_input(
                        "結束日期",
                        value=state.get('end_date', default_end),
                        min_value=min_date,
                        max_value=max_date,
                        key="end_date_input",
                        on_change=on_end_date_change
                    )
                    # 更新狀態
                    state['end_date'] = end_date
                
                # 查詢股票資料
                query = """
                    SELECT *
                    FROM stock_daily
                    WHERE stock_id = ?
                    AND date BETWEEN ? AND ?
                    ORDER BY date DESC
                """
                result = db.conn.execute(query, [stock_id, start_date, end_date]).fetchdf()
                
                if not result.empty:
                    # 將資料轉換為正確的時間順序
                    result = result.sort_values('date')
                    
                    # 建立 K 線圖
                    fig = make_subplots(
                        rows=2, 
                        cols=1,
                        shared_xaxes=True,
                        vertical_spacing=0.2,
                        row_heights=[0.7, 0.3]
                    )
                    
                    # K線圖
                    fig.add_trace(
                        go.Candlestick(
                            x=result['date'],
                            open=result['opening_price'],
                            high=result['highest_price'],
                            low=result['lowest_price'],
                            close=result['closing_price'],
                            name='',
                            text=[f'開盤: {open}<br>最高: {high}<br>最低: {low}<br>收盤: {close}<br>量: {volume:,}' 
                                  for open, high, low, close, volume in zip(
                                      result['opening_price'],
                                      result['highest_price'],
                                      result['lowest_price'],
                                      result['closing_price'],
                                      result['trade_volume']
                                  )],
                            hoverinfo='text+name',
                            increasing_line_color='red',
                            decreasing_line_color='lightgreen',
                        ),
                        row=1, col=1
                    )
                    
                    # 均線
                    for ma, color in [('ma5', 'orange'), ('ma10', 'blue'), 
                                    ('ma20', 'purple'), ('ma60', 'green')]:
                        fig.add_trace(
                            go.Scatter(
                                x=result['date'],
                                y=result[ma],
                                name=ma.upper(),
                                line=dict(color=color)
                            ),
                            row=1, col=1
                        )
                    
                    # 根據漲跌設定成交量顏色
                    colors = []
                    for change in result['change_percent']:
                        if change > 0:
                            colors.append('lightcoral')
                        elif change < 0:
                            colors.append('lightgreen')
                        else:
                            colors.append('gold')
                    
                    # 成交量圖
                    fig.add_trace(
                        go.Bar(
                            x=result['date'],
                            y=result['trade_volume'],
                            name='成交量',
                            marker_color=colors,
                            opacity=0.7,
                            hovertemplate='成交量: %{y:,}<extra></extra>'
                        ),
                        row=2, col=1
                    )
                    
                    # 更新版面設置
                    fig.update_layout(
                        title=f'{stock_id} 股價走勢圖',
                        yaxis_title='股價',
                        yaxis2_title='成交量',
                        xaxis_rangeslider_visible=True,
                        height=800,
                        hovermode='x unified',
                        hoverdistance=1,
                        spikedistance=1000,
                        xaxis=dict(
                            showspikes=True,
                            spikesnap='data',
                            spikemode='across',
                            spikethickness=1,
                            spikedash='solid',
                            spikecolor='gray',
                            rangeslider=dict(visible=True),
                            hoverformat='%Y/%m/%d',
                            fixedrange=True  # 鎖定 X 軸縮放
                        ),
                        xaxis2=dict(
                            hoverformat='%Y/%m/%d',
                            fixedrange=True  # 鎖定第二個 X 軸縮放
                        ),
                        yaxis=dict(
                            showspikes=True,
                            spikesnap='cursor',
                            spikemode='across',
                            spikethickness=1,
                            spikedash='solid',
                            spikecolor='gray',
                            fixedrange=True  # 鎖定 Y 軸縮放
                        ),
                        yaxis2=dict(
                            fixedrange=True  # 鎖定第二個 Y 軸縮放
                        ),
                        dragmode=False  # 禁用拖曳
                    )
                    
                    # 顯示圖表
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # 顯示基本資料
                    info_query = """
                        SELECT * 
                        FROM stock_info 
                        WHERE stock_id = ?
                    """
                    stock_info = db.conn.execute(info_query, [stock_id]).fetchdf()
                    
                    if not stock_info.empty:
                        st.markdown("### 股票基本資料")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("股票名稱", stock_info['stock_name'].iloc[0])
                        with col2:
                            st.metric("產業別", stock_info['industry'].iloc[0])
                        with col3:
                            st.metric("市場別", stock_info['market_type'].iloc[0])
                    
                    # 顯示最近交易數據
                    st.markdown("### 最近交易數據")
                    latest_data = result.iloc[-1]
                    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
                    
                    with metrics_col1:
                        st.metric("收盤價", 
                                 f"{latest_data['closing_price']:.2f}", 
                                 f"{latest_data['change_percent']:.2f}%",
                                 delta_color="inverse")
                    with metrics_col2:
                        st.metric("成交量", f"{latest_data['trade_volume']:,}")
                    with metrics_col3:
                        st.metric("開盤價", f"{latest_data['opening_price']:.2f}")
                    with metrics_col4:
                        st.metric("成交筆數", f"{latest_data['transaction_count']:,}")
                    
                    st.markdown("###")

                    # 新增表格顯示
                    st.markdown("### 歷史交易數據")
                    
                    # 選擇要顯示的欄位並重新命名
                    display_columns = {
                        'date': '日期',
                        'opening_price': '開盤價',
                        'highest_price': '最高價',
                        'lowest_price': '最低價',
                        'closing_price': '收盤價',
                        'trade_volume': '成交量',
                        'transaction_count': '成交筆數',
                        'change_percent': '漲跌幅(%)',
                        'ma5': '5日均線',
                        'ma10': '10日均線',
                        'ma20': '20日均線',
                        'ma60': '60日均線'
                    }
                    
                    # 準備顯示用的資料框
                    display_df = result[display_columns.keys()].copy()
                    
                    # 依日期降序排序
                    display_df = display_df.sort_values('date', ascending=False)
                    
                    # 重新命名欄位
                    display_df.columns = display_columns.values()
                    
                    # 格式化數值
                    display_df['日期'] = display_df['日期'].dt.strftime('%Y-%m-%d')
                    display_df['成交量'] = display_df['成交量'].apply(lambda x: f"{x:,}")
                    display_df['成交筆數'] = display_df['成交筆數'].apply(lambda x: f"{x:,}")
                    for col in ['開盤價', '最高價', '最低價', '收盤價', '5日均線', '10日均線', '20日均線', '60日均線']:
                        display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}")
                    display_df['漲跌幅(%)'] = display_df['漲跌幅(%)'].apply(lambda x: f"{x:.2f}")
                    
                    # 顯示表格
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        height=400,
                        hide_index=True
                    )
                    
                else:
                    st.warning("找不到該股票的資料")
    
    finally:
        # 關閉資料庫連接
        db.close()