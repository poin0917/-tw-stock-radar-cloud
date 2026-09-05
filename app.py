
import streamlit as st
import pandas as pd
import json
from pathlib import Path

st.set_page_config(page_title="台股高勝率雷達｜雲端版", page_icon="📈", layout="wide")

DATA = Path(__file__).parent / "data" / "latest.json"
CSV = Path(__file__).parent / "data" / "latest.csv"

st.title("📈 台股高勝率雷達｜雲端版")
st.caption("雲端自動更新｜每日精選約 10 檔｜iPhone Safari 直接開")

if not DATA.exists():
    st.warning("目前尚未產生雲端掃描結果。請到 GitHub Actions 手動執行一次 Daily Stock Scan。")
    st.stop()

payload = json.loads(DATA.read_text(encoding="utf-8"))
results = payload.get("results", [])

c1,c2,c3,c4 = st.columns(4)
c1.metric("最新更新", payload.get("generated_at","-"))
c2.metric("分析完成", payload.get("analyzed_count",0))
c3.metric("通過品質門檻", payload.get("quality_count",0))
c4.metric("今日精選", len(results))

if not results:
    st.info("今日沒有符合品質門檻的標的，不硬湊10檔。")
else:
    st.subheader("🔥 今日精選")

    for i,x in enumerate(results,1):
        win = f"{x['win_rate']}%" if x.get("win_rate") is not None else "樣本不足"
        st.markdown(f"""
### #{i}　{x['code']} {x['name']}｜{x['grade']}
**評分：{x['score']}/100｜收盤：{x['close']}**

進場區：**{x['entry_low']} ~ {x['entry_high']}**  
停損：**{x['stop']}**｜壓力：**{x['resistance']}**  
回測勝率：**{win}**｜樣本：**{x['signals']} 次**｜平均報酬：**{x['avg_return'] if x['avg_return'] is not None else '-'}%**  
日K：**{x['daily_score']}分**｜60分K：**{x['score_60m']}分**
""")

        with st.expander("查看入選理由與風險"):
            st.markdown("**入選理由**")
            for r in x.get("reasons",[]):
                st.write("✓",r)
            st.markdown("**風險提醒**")
            for r in x.get("risks",[]):
                st.write("•",r)

    table = pd.DataFrame([{
        "排名": i+1,
        "代號": x["code"],
        "名稱": x["name"],
        "市場": x["market"],
        "評分": x["score"],
        "等級": x["grade"],
        "收盤": x["close"],
        "進場低": x["entry_low"],
        "進場高": x["entry_high"],
        "停損": x["stop"],
        "壓力": x["resistance"],
        "回測勝率%": x["win_rate"],
        "樣本": x["signals"],
        "平均報酬%": x["avg_return"],
        "日K": x["daily_score"],
        "60分K": x["score_60m"],
    } for i,x in enumerate(results)])

    st.subheader("📋 排行榜")
    st.dataframe(table,use_container_width=True,hide_index=True)

    if CSV.exists():
        st.download_button(
            "📥 下載最新精選 CSV",
            CSV.read_bytes(),
            file_name="最新精選10檔.csv",
            mime="text/csv"
        )

st.markdown("---")
st.caption("歷史回測勝率不代表未來獲利保證；此工具僅供研究與技術分析。")
