import streamlit as st
from datetime import datetime
import time

st.set_page_config(page_title="현재 시각", page_icon="🕐")

st.title("🕐 현재 날짜 & 시간")

placeholder = st.empty()

auto_refresh = st.toggle("실시간 업데이트", value=False)

while True:
    now = datetime.now()

    with placeholder.container():
        st.metric("📅 날짜", now.strftime("%Y년 %m월 %d일"))
        st.metric("⏰ 시간", now.strftime("%H:%M:%S"))
        st.caption(f"마지막 업데이트: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    if not auto_refresh:
        break

    time.sleep(1)
    st.rerun()
