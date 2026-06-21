"""
app.py — 2026 FIFA 월드컵 예측 모델 리더보드
"""

import base64
import os

import pandas as pd
import requests
import streamlit as st

from fetch_results import fetch_finished_matches
from scorer import calc_leaderboard

# ── 페이지 설정 ───────────────────────────────────────────────
st.set_page_config(
    page_title="⚽ 월드컵 모델 리더보드",
    page_icon="⚽",
    layout="wide",
)

# ── GitHub 설정 ──────────────────────────────────────────────
def get_github_config() -> tuple[str, str]:
    try:
        token = st.secrets["GITHUB_TOKEN"]
        repo  = st.secrets["GITHUB_REPO"]
    except Exception:
        token = os.environ.get("GITHUB_TOKEN", "")
        repo  = os.environ.get("GITHUB_REPO", "")
    return token, repo


def commit_csv_to_github(token: str, repo: str, filename: str, content: bytes, branch: str = "main") -> tuple[bool, str]:
    """predictions/{filename} 을 GitHub {branch}에 커밋(생성 또는 업데이트)."""
    path = f"predictions/{filename}"
    api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }

    # 기존 파일 SHA 조회 (업데이트 시 필요) — 브랜치 지정
    sha = None
    resp = requests.get(api_url, headers=headers, params={"ref": branch}, timeout=10)
    if resp.status_code == 200:
        sha = resp.json().get("sha")

    payload: dict = {
        "message": f"Upload {filename} via Streamlit",
        "content": base64.b64encode(content).decode(),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    put_resp = requests.put(api_url, headers=headers, json=payload, timeout=15)
    if put_resp.status_code in (200, 201):
        return True, ""
    return False, put_resp.json().get("message", "알 수 없는 오류")


# ── 모델 → CSV 경로 매핑 ─────────────────────────────────────
MODEL_FILES = {
    "XGBoost":      "predictions/xgboost.csv",
    "RandomForest": "predictions/random_forest.csv",
    "Poisson":      "predictions/poisson.csv",
    "MLP":          "predictions/mlp.csv",
    "LinearReg":    "predictions/linear_reg.csv",
}

MEDALS = ["🥇", "🥈", "🥉", "4위", "5위"]


# ── 데이터 로드 함수 ─────────────────────────────────────────
def get_api_key() -> str:
    try:
        return st.secrets["FOOTBALL_DATA_API_KEY"]
    except Exception:
        return os.environ.get("FOOTBALL_DATA_API_KEY", "")


@st.cache_data(ttl=300)  # 5분 캐시 — API 요청 횟수 절감
def load_results(api_key: str) -> list[dict]:
    return fetch_finished_matches(api_key)


@st.cache_data(ttl=60)   # 1분 캐시 — git push 후 빠르게 반영
def load_predictions() -> pd.DataFrame:
    """predictions/ 폴더의 모든 모델 CSV를 합쳐서 반환."""
    dfs = []
    for model, path in MODEL_FILES.items():
        if os.path.exists(path):
            df = pd.read_csv(path)
            df["model"] = model
            dfs.append(df)

    if not dfs:
        return pd.DataFrame(columns=["match_id", "pred_home", "pred_away", "model"])

    return pd.concat(dfs, ignore_index=True)


# ── 사이드바: CSV 업로드 ─────────────────────────────────────
with st.sidebar:
    st.header("예측 CSV 업로드")
    target_branch = st.text_input("브랜치", value="main", help="커밋할 브랜치명 (예: test, dev)")
    uploaded = st.file_uploader(
        "파일 선택",
        type="csv",
        help="파일명: xgboost.csv, poisson.csv 등",
    )

    if uploaded:
        filename = uploaded.name
        # 파일명으로 모델 자동 인식
        stem = os.path.splitext(filename)[0].lower().replace("_", "").replace("-", "")
        matched_model = next(
            (m for m in MODEL_FILES if m.lower().replace(" ", "") == stem or
             MODEL_FILES[m].split("/")[-1].replace(".csv", "").replace("_", "") == stem),
            None,
        )

        if matched_model:
            st.info(f"모델 인식: **{matched_model}**")
        else:
            st.warning(f"`{filename}` — 알 수 없는 모델명이지만 업로드는 가능합니다.")

        if st.button("GitHub에 업로드", type="primary"):
            gh_token, gh_repo = get_github_config()
            if not gh_token or not gh_repo:
                st.error("GITHUB_TOKEN / GITHUB_REPO 시크릿을 설정해주세요.")
            elif not target_branch.strip():
                st.error("브랜치명을 입력해주세요.")
            else:
                with st.spinner(f"`{target_branch}` 브랜치에 커밋 중..."):
                    ok, err = commit_csv_to_github(
                        gh_token, gh_repo, filename, uploaded.getvalue(), target_branch.strip()
                    )
                if ok:
                    st.success(f"`{filename}` → `{target_branch}` 업로드 완료!")
                    st.caption("Streamlit Cloud 재배포까지 약 30초 소요됩니다.")
                else:
                    st.error(f"업로드 실패: {err}")


# ── 메인 ─────────────────────────────────────────────────────
st.title("⚽ 2026 FIFA 월드컵 예측 모델 리더보드")

# 데이터 로드
api_key  = get_api_key()
results  = load_results(api_key)
preds_df = load_predictions()

# 데이터 소스 상태 표시
src_col1, src_col2, src_col3 = st.columns([1.2, 1.2, 5])
if results:
    src_col1.success(f"API 연결됨 · {len(results)}경기")
else:
    src_col1.error("API 연결 실패")

loaded_models = preds_df["model"].nunique() if not preds_df.empty else 0
if loaded_models > 0:
    src_col2.success(f"predictions/ · {loaded_models}개 모델")
else:
    src_col2.warning("예측값 없음")

# API 오류 시 조기 종료
if not results:
    st.warning("경기 데이터를 불러오지 못했어요. API 키를 확인해주세요.")
    with st.expander("설정 방법"):
        st.code(
            "# .streamlit/secrets.toml\n"
            'FOOTBALL_DATA_API_KEY = "여기에_키_입력"',
            language="toml",
        )
    st.stop()

# 점수 계산
scores, match_details = calc_leaderboard(results, preds_df)
ranked = sorted(scores.items(), key=lambda x: -x[1])

# ── 요약 지표 ─────────────────────────────────────────────────
m1, m2, m3 = st.columns(3)
m1.metric("완료된 경기", f"{len(results)}경기")
if ranked:
    m2.metric("1위 모델", ranked[0][0])
    m3.metric("1위 점수", f"{ranked[0][1]}점")
else:
    m2.metric("1위 모델", "—")
    m3.metric("1위 점수", "—")

st.divider()

# ── 리더보드 ─────────────────────────────────────────────────
st.markdown("## 🏆 리더보드")

if not ranked:
    st.info("predictions/ 폴더에 예측 CSV를 추가하면 리더보드가 표시돼요.")
else:
    max_score = ranked[0][1] if ranked[0][1] > 0 else 1

    for i, (model, score) in enumerate(ranked):
        col_rank, col_model, col_bar, col_score = st.columns([0.5, 1.8, 4, 1])
        col_rank.markdown(
            f"<p style='font-size:24px; margin:0;'>{MEDALS[i] if i < len(MEDALS) else f'{i+1}위'}</p>",
            unsafe_allow_html=True,
        )
        col_model.markdown(
            f"<p style='font-size:20px; font-weight:600; margin:8px 0;'>{model}</p>",
            unsafe_allow_html=True,
        )
        col_bar.markdown("<div style='margin-top:14px;'>", unsafe_allow_html=True)
        col_bar.progress(score / max_score)
        col_bar.markdown("</div>", unsafe_allow_html=True)
        col_score.markdown(
            f"<p style='font-size:20px; font-weight:600; margin:8px 0; text-align:right;'>{score}점</p>",
            unsafe_allow_html=True,
        )
        st.markdown("<div style='margin-bottom:6px;'></div>", unsafe_allow_html=True)

st.divider()

# ── 완료된 경기 상세 ─────────────────────────────────────────
st.subheader(f"완료된 경기 ({len(match_details)})")

for m in reversed(match_details):  # 최신순 정렬
    group_label = f"[{m['stage']} {m['group']}]" if m["group"] else f"[{m['stage']}]"
    header = f"{group_label}  {m['home']}  {m['home_score']} - {m['away_score']}  {m['away']}"

    with st.expander(header):
        if not m["model_results"]:
            st.caption("이 경기에 대한 예측값이 없어요.")
            continue

        # 모델별 예측 결과 테이블
        rows = []
        for model in MODEL_FILES:
            if model not in m["model_results"]:
                continue
            mr = m["model_results"][model]
            rows.append({
                "모델":     model,
                "예측":     f"{mr['pred_home']}-{mr['pred_away']}",
                "실제":     f"{m['home_score']}-{m['away_score']}",
                "획득 점수": mr["pts"],
                "근거":     mr["label"],
            })

        if rows:
            df_detail = (
                pd.DataFrame(rows)
                .sort_values("획득 점수", ascending=False)
                .reset_index(drop=True)
            )

            # 점수 컬럼 색상 하이라이트
            def highlight_pts(row):
                pts = row["획득 점수"]
                if pts == 10:
                    return ["background-color:#EAF3DE"] * len(row)
                elif pts >= 6:
                    return ["background-color:#FAEEDA"] * len(row)
                return [""] * len(row)

            st.dataframe(
                df_detail.style.apply(highlight_pts, axis=1),
                use_container_width=True,
                hide_index=True,
            )