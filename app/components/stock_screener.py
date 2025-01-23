import streamlit as st
import pandas as pd
from data.database.db_manager import DatabaseManager
import os
import json
from config.logger import setup_logging

# 設置 logger
logger = setup_logging()

def create_condition_card(condition_name, condition_key, state):
    """
    創建條件選擇卡片
    Args:
        condition_name: 條件名稱
        condition_key: 條件的鍵值
        state: 狀態字典
    """
    card_html = f"""
        <div style="
            padding: 1rem;
            border-radius: 10px;
            background-color: #f0f2f6;
            margin: 0.5rem 0;
            transition: all 0.3s;
            border: 1px solid #e0e0e0;
            ">
            <p style="margin-bottom: 0.5rem;">{condition_name}</p>
        </div>
    """
    # 從狀態中獲取條件的選中狀態
    default_value = state.get(f'condition_{condition_key}', False)
    
    is_selected = st.checkbox(
        condition_name,
        value=default_value,
        key=condition_key,
        help=f"點擊勾選"
    )
    
    # 更新狀態
    state[f'condition_{condition_key}'] = is_selected
    
    return is_selected

def render(state=None):
    """
    渲染股票篩選器
    Args:
        state: 用於保存篩選器狀態的字典
    """
    if state is None:
        state = {}

    # 使用容器來組織內容
    with st.container():
        # 主標題使用更醒目的樣式
        st.title(" 💎 股票篩選器")
        st.markdown("---")  # 分隔線
    
    # 初始化資料庫連接
    db_manager = DatabaseManager(
        db_path=os.getenv('DB_PATH', 'StockHero.db'),
        bucket_name=os.getenv('BUCKET_NAME', 'ian-line-bot-files')
    )
    db_manager.connect()

    try:
        # 從資料庫獲取所有股票資料
        query = """
            SELECT 
                si.stock_id,
                si.stock_name,
                si.industry,
                si.conditions
            FROM stock_info si
            WHERE si.conditions IS NOT NULL
        """
        results = db_manager.conn.execute(query).fetchdf()
        
        # 將 conditions 欄位從 JSON 字串轉換為 Python 字典
        results['conditions'] = results['conditions'].apply(
            lambda x: json.loads(x) if isinstance(x, str) else x
        )
        
        # 定義篩選條件分類
        condition_categories = {
            "站上相關": {
                "above_ma5": "站上 5 日線",
                "above_ma10": "站上 10 日線",
                "above_ma20": "站上 20 日線",
                "above_ma60": "站上 60 日線"
            },
            "成交量相關": {
                "volume_increase": "成交量大於前日兩倍"
            }
        }

        # 獲取所有條件的 key
        all_condition_keys = [key for category in condition_categories.values() for key in category.keys()]

        # 使用容器來組織篩選條件區域
        with st.container():
            st.header("選擇條件")
            
            # 添加全選/全不選按鈕（所有條件）
            col1, col2 = st.columns(2)
            with col1:
                if st.button("全部選取", key="select_all_conditions"):
                    for key in all_condition_keys:
                        state[f'condition_{key}'] = True
            with col2:
                if st.button("全部取消", key="deselect_all_conditions"):
                    for key in all_condition_keys:
                        state[f'condition_{key}'] = False
            
            selected_conditions = []
            
            # 使用 tabs 來組織不同類別的條件
            tabs = st.tabs(condition_categories.keys())
            
            for tab, (category, conditions) in zip(tabs, condition_categories.items()):
                with tab:
                    # 使用 columns 來創建網格布局
                    num_columns = 2  # 每行顯示的條件數
                    conditions_list = list(conditions.items())
                    
                    for i in range(0, len(conditions_list), num_columns):
                        cols = st.columns(num_columns)
                        for j in range(num_columns):
                            if i + j < len(conditions_list):
                                condition_key, condition_name = conditions_list[i + j]
                                with cols[j]:
                                    if create_condition_card(condition_name, condition_key, state):
                                        selected_conditions.append(condition_key)
            
            # 添加分隔線
            st.markdown("---")

        # 篩選股票
        filtered_stocks = results.copy()
            
        # 根據選定的條件進行篩選
        if selected_conditions:
            for condition in selected_conditions:
                mask = filtered_stocks['conditions'].apply(
                    lambda x: isinstance(x, dict) and x.get(condition, False) == True
                )
                filtered_stocks = filtered_stocks[mask]

        # 顯示篩選結果
        if not filtered_stocks.empty:
            with st.container():
                st.header("篩選結果")
                
                # 在顯示表格前顯示符合條件的股票數量
                st.markdown(f"🎯 共找到 **{len(filtered_stocks)}** 檔符合條件的股票")
                
                # 使用 columns 來並排放置產業別選擇和股票代號搜尋
                col1, col2 = st.columns(2)
                
                with col1:
                    # 獲取所有唯一的產業別並添加"全部"選項
                    industries = ['全部'] + sorted(filtered_stocks['industry'].unique().tolist())
                    
                    # 從狀態中讀取之前選擇的產業別，如果沒有則使用預設值
                    default_industry_index = industries.index(state.get('selected_industry', '全部')) if state.get('selected_industry') in industries else 0
                    
                    # 產業別選擇
                    selected_industry = st.selectbox(
                        "選擇產業別",
                        options=industries,
                        index=default_industry_index,
                        key="industry_selector"
                    )
                    # 更新狀態
                    state['selected_industry'] = selected_industry
                
                with col2:
                    # 從狀態中讀取之前的搜尋文字
                    default_search = state.get('stock_id_search', '')
                    
                    # 股票代號搜尋
                    stock_id_search = st.text_input(
                        "輸入股票代號",
                        value=default_search,
                        placeholder="例如: 2330",
                        help="可輸入完整或部分股票代號進行搜尋",
                        key="stock_search"
                    ).strip()
                    # 更新狀態
                    state['stock_id_search'] = stock_id_search
                
                # 準備顯示資料
                display_df = pd.DataFrame()
                
                # 根據選擇的產業別和股票代號篩選
                display_data = filtered_stocks
                
                if selected_industry != '全部':
                    display_data = display_data[display_data['industry'] == selected_industry]
                
                if stock_id_search:
                    display_data = display_data[display_data['stock_id'].str.contains(stock_id_search, case=False)]
                
                display_df['產業別'] = display_data['industry']
                display_df['股票代號'] = display_data['stock_id']
                display_df['股票名稱'] = display_data['stock_name']
                
                # 為每個條件創建欄位
                all_conditions = {k: v for d in condition_categories.values() for k, v in d.items()}
                for condition_key, condition_name in all_conditions.items():
                    display_df[condition_name] = display_data['conditions'].apply(
                        lambda x: '✓' if isinstance(x, dict) and x.get(condition_key, False) else ''
                    )
                
                # 先按產業別排序，再按股票代號排序
                display_df = display_df.sort_values(['產業別', '股票代號'])
                
                # 使用 streamlit 的自動調整大小功能顯示表格
                st.dataframe(
                    display_df,
                    use_container_width=True,  # 使用容器寬度
                    hide_index=True  # 隱藏索引列
                )
        else:
            if selected_conditions:
                st.warning("⚠️ 沒有股票符合所選條件")
            else:
                # 使用更友善的提示訊息
                st.info("💡 請在上方選擇至少一個篩選條件來開始篩選股票")

    except Exception as e:
        logger.error(f"股票篩選器發生錯誤: {str(e)}")
        st.error(f"❌ 載入資料時發生錯誤: {str(e)}")
    
    finally:
        db_manager.close()

if __name__ == "__main__":
    render()