import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import hmac
from pathlib import Path
from dotenv import load_dotenv
from app.components import stock_screener, stock_detail
from config.logger import setup_logging

# 設置 logger
logger = setup_logging()

# 載入 .env 檔案
load_dotenv()

# 設置頁面配置
st.set_page_config(
    page_title="Stock Hero",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化 session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'home'

if 'stock_detail_state' not in st.session_state:
    st.session_state.stock_detail_state = {}
if 'stock_screener_state' not in st.session_state:
    st.session_state.stock_screener_state = {}

def check_password():
    """檢查密碼是否正確"""
    def password_entered():
        """驗證輸入的密碼"""
        if hmac.compare_digest(st.session_state["password"], os.getenv('PASSWORD')):
            st.session_state.authenticated = True
            logger.info("登入成功")
            del st.session_state["password"]
        else:
            st.session_state.authenticated = False
            st.error("❌ 密碼錯誤")

    if not st.session_state.authenticated:
        st.markdown("# 歡迎使用 Stock Hero 📈")
        st.write("請輸入密碼進行登入")
        st.text_input(
            "密碼", 
            type="password", 
            key="password",
            on_change=password_entered
        )
        return False
    return True

# 主要應用邏輯
if check_password():
    # 側邊欄
    with st.sidebar:
        st.markdown("### 功能選單")
        
        # 使用選單來切換頁面
        previous_page = st.session_state.current_page  # 保存切換前的頁面
        page = st.selectbox(
            "選擇功能",
            options=['首頁', '股票詳情', '股票篩選器', '法人動向'],
            key='page_selector'
        )
        
        # 根據選擇更新當前頁面
        if page == '首頁':
            st.session_state.current_page = 'home'
        elif page == '股票詳情':
            st.session_state.current_page = 'stock_detail'
        elif page == '股票篩選器':
            st.session_state.current_page = 'stock_screener'
        elif page == '法人動向':
            st.session_state.current_page = 'institutional'
        
        # 登出按鈕
        if st.button("登出"):
            st.session_state.authenticated = False
            st.rerun()
    
    # 根據當前頁面顯示相應的內容
    if st.session_state.current_page == 'home':
        st.markdown("# Stock Hero 📈")
        st.markdown("""
        ### 歡迎 👋
        
        請從左側選單選擇功能：
        
        - 📈 **股票詳情**：查看個股詳細資訊            
        - 💎 **股票篩選器**：依照條件篩選股票
        - 👥 **法人動向**：查看個股法人買賣超趨勢
        """)
    elif st.session_state.current_page == 'stock_detail':
        stock_detail.render(state=st.session_state.stock_detail_state)
    elif st.session_state.current_page == 'stock_screener':
        stock_screener.render(state=st.session_state.stock_screener_state)
