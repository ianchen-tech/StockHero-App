import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data.database.db_manager import DatabaseManager
import os
from datetime import datetime, timedelta

def render():
    st.markdown("# 股票詳情 📈")
    
    # 初始化資料庫連接
    db = DatabaseManager(
        db_path=os.getenv('DB_PATH', 'StockHero.db'),
        bucket_name=os.getenv('BUCKET_NAME', 'stock-hero')
    )
    db.connect()
    
    try:
        # 搜尋框
        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            stock_id = st.text_input("請輸入股票代碼", placeholder="例如: 2330")
        
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
                
                # 日期選擇器
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input(
                        "開始日期",
                        value=max_date - timedelta(days=90),
                        min_value=min_date,
                        max_value=max_date
                    )
                with col2:
                    end_date = st.date_input(
                        "結束日期",
                        value=max_date,
                        min_value=min_date,
                        max_value=max_date
                    )
                
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
                        vertical_spacing=0.05,
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
                            increasing_line_color='red',     # 漲的顏色設為紅色
                            decreasing_line_color='lightgreen',   # 跌的顏色設為綠色
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
                    colors = ['lightcoral' if x >= 0 else 'lightgreen' for x in result['change_percent']]
                    
                    # 成交量圖
                    fig.add_trace(
                        go.Bar(
                            x=result['date'],
                            y=result['trade_volume'],
                            name='成交量',
                            marker_color=colors  # 設定bar顏色
                        ),
                        row=2, col=1
                    )
                    
                    # 更新版面設置
                    fig.update_layout(
                        title=f'{stock_id} 股價走勢圖',
                        yaxis_title='股價',
                        yaxis2_title='成交量',
                        xaxis_rangeslider_visible=True,  # 啟用下方的範圍選擇器
                        height=800,
                        # 添加游標線設置
                        hovermode='x unified',
                        hoverdistance=1,
                        spikedistance=1000,
                        # 設置x軸的參考線和日期格式
                        xaxis=dict(
                            showspikes=True,
                            spikesnap='cursor',
                            spikemode='across',
                            spikethickness=1,
                            spikedash='solid',
                            spikecolor='gray',
                            rangeslider=dict(visible=True),  # 啟用範圍選擇器
                            hoverformat='%Y/%m/%d'  # 設定游標顯示的日期格式為 YYYY/MM/DD
                        ),
                        # 設置y軸的參考線
                        yaxis=dict(
                            showspikes=True,
                            spikesnap='cursor',
                            spikemode='across',
                            spikethickness=1,
                            spikedash='solid',
                            spikecolor='gray'
                        )
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
                    
                else:
                    st.warning("找不到該股票的資料")
    
    finally:
        # 關閉資料庫連接
        db.close()