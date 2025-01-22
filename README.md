# StockHero-App

---
Folder structure：

```
StockHero/
├── app/                        # Streamlit 主目錄
│   ├── pages/                  # 介面目錄
│   ├── components/             # 頁面組件
│   │   ├── stock_detail.py     # 個股資訊與技術圖
│   │   ├── stock_screener.py   # 個股推薦
│   │   └── institutional.py    # 法人買賣趨勢
│   └── main.py                 # Streamlit 主程式
├── data/                       # 資料處理相關
│   ├── database/               # 資料庫相關
│   │   ├── db_manager.py       # 資料庫管理
│   │   └── models.py           # 資料模型定義
├── config/                     # 設定檔
│   ├── config.py               # 一般設定
│   └── logger.py               # logging 設置
├── utils/                      # 通用工具函數目錄
├── tests/                      # 測試檔案
├── notebook/                   # 筆記
├── Dockerfile                  # Docker 設定
└── README.md                   # 專案說明
```