"""
scorer.py
─────────
점수 계산 순수 함수 모음. 외부 의존성 없음.

점수 기준:
  10점 — 두 팀 점수 모두 정확
   6점 — 한 팀 점수 + 승패 정확
   3점 — 한 팀 점수만 정확 (승패 틀림)
   1점 — 승패만 정확
   0점 — 모두 틀림
"""

import pandas as pd


def get_result(home: int, away: int) -> str:
    """홈승(H) / 무(D) / 원정승(A) 반환"""
    if home > away:
        return "H"
    elif home < away:
        return "A"
    return "D"


def calc_score(pred_home: int, pred_away: int,
               real_home: int, real_away: int) -> dict:
    """
    예측값 vs 실제 결과 비교 → {pts, label} 반환

    Args:
        pred_home: 모델이 예측한 홈팀 점수
        pred_away: 모델이 예측한 원정팀 점수
        real_home: 실제 홈팀 점수
        real_away: 실제 원정팀 점수
    """
    home_exact     = pred_home == real_home
    away_exact     = pred_away == real_away
    result_correct = get_result(pred_home, pred_away) == get_result(real_home, real_away)

    if home_exact and away_exact:
        return {"pts": 10, "label": "두 팀 모두 정확"}
    elif (home_exact or away_exact) and result_correct:
        return {"pts": 6,  "label": "한 팀 점수 + 승패"}
    elif home_exact or away_exact:
        return {"pts": 3,  "label": "한 팀 점수 (승패 틀림)"}
    elif result_correct:
        return {"pts": 1,  "label": "승패만 정확"}
    return {"pts": 0, "label": "모두 틀림"}


def calc_leaderboard(results: list[dict],
                     preds_df: pd.DataFrame) -> tuple[dict, list[dict]]:
    """
    전체 경기에 대해 모델별 누적 점수와 경기별 상세를 계산한다.

    Args:
        results:  fetch_results.fetch_finished_matches() 반환값
        preds_df: load_predictions() 반환값
                  columns: match_id, pred_home, pred_away, model

    Returns:
        scores:        {model: 누적 점수}
        match_details: results 각 항목에 model_results 딕셔너리 추가
                       model_results = {model: {pred_home, pred_away, pts, label}}
    """
    model_list = preds_df["model"].unique().tolist() if not preds_df.empty else []
    scores = {m: 0 for m in model_list}
    match_details = []

    for r in results:
        match_preds = preds_df[preds_df["match_id"] == r["match_id"]]
        model_results = {}

        for _, row in match_preds.iterrows():
            info = calc_score(
                int(row["pred_home"]), int(row["pred_away"]),
                r["home_score"], r["away_score"]
            )
            model = row["model"]
            scores[model] += info["pts"]
            model_results[model] = {
                "pred_home": int(row["pred_home"]),
                "pred_away": int(row["pred_away"]),
                **info,
            }

        match_details.append({**r, "model_results": model_results})

    return scores, match_details