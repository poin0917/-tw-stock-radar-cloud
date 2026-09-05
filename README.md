# 台股高勝率雷達｜雲端全自動版

## 架構
GitHub 儲存程式與每日結果
↓
GitHub Actions 每個交易日 07:07（Asia/Taipei）自動執行 scanner.py
↓
結果寫入 data/latest.json / latest.csv
↓
Streamlit Community Cloud 顯示最新結果

## 部署步驟

### 1. 建立 GitHub Repository
例如：
tw-stock-radar-cloud

把本資料夾所有檔案上傳到 repository 根目錄。

注意 `.github/workflows/daily_scan.yml` 也必須一起上傳。

### 2. 先測試 GitHub Actions
GitHub Repository：
Actions → Daily Stock Scan → Run workflow

成功後應出現：
data/latest.json
data/latest.csv

### 3. 部署 Streamlit
進入：
https://share.streamlit.io

登入 GitHub。

Create app → Yup, I have an app

選擇：
Repository：你的 tw-stock-radar-cloud
Branch：main
Main file path：app.py

Deploy。

完成後會取得：
https://xxxxx.streamlit.app

這個網址直接用 iPhone Safari 開即可。

## 自動掃描時間
目前 workflow 設為台北時間每日 07:07，週一～週五。

如果希望改成收盤後 14:30：
把 daily_scan.yml 改為：

cron: "30 14 * * 1-5"
timezone: "Asia/Taipei"

## 為什麼用 07:07 而不是 07:00
GitHub 官方提醒每小時整點可能因排程高負載而延遲，所以刻意避開整點。

## 重要
Yahoo Finance 為免費行情來源，可能有限流或延遲。
歷史回測不代表未來獲利保證。
