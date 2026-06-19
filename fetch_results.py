"""
fetch_results.py
────────────────
football-data.org API에서 완료된 월드컵 경기 결과를 가져온다.
Streamlit 의존성 없음 → 터미널에서 단독 실행 가능.

단독 실행:
    export FOOTBALL_DATA_API_KEY="your_key"
    python fetch_results.py
"""

import os
import sys
import requests

API_URL = "https://api.football-data.org/v4/competitions/WC/matches"

STAGE_KR = {
    "GROUP_STAGE":   "조별",
    "LAST_32":       "32강",
    "LAST_16":       "16강",
    "QUARTER_FINALS":"8강",
    "SEMI_FINALS":   "4강",
    "THIRD_PLACE":   "3/4위",
    "FINAL":         "결승",
}


def fetch_finished_matches(api_key: str) -> list[dict]:
    """
    FINISHED 상태인 경기만 필터링해서 반환한다.

    Returns:
        [
            {
                "match_id":   537358,
                "stage":      "조별",
                "group":      "F",
                "home":       "Sweden",
                "away":       "Tunisia",
                "home_score": 5,
                "away_score": 1,
            },
            ...
        ]
        API 오류 시 빈 리스트 반환.
    """
    if not api_key:
        print("[fetch_results] API 키가 없어요. secrets.toml 또는 환경변수를 확인하세요.")
        return []

    try:
        res = requests.get(
            API_URL,
            headers={"X-Auth-Token": api_key},
            timeout=10,
        )
        res.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[fetch_results] API 요청 실패: {e}")
        return []

    matches = res.json().get("matches", [])

    return [
        {
            "match_id":   m["id"],
            "stage":      STAGE_KR.get(m["stage"], m["stage"]),
            "group":      (m.get("group") or "").replace("GROUP_", ""),
            "home":       m["homeTeam"]["name"],
            "away":       m["awayTeam"]["name"],
            "home_score": m["score"]["fullTime"]["home"],
            "away_score": m["score"]["fullTime"]["away"],
        }
        for m in matches
        if m["status"] == "FINISHED"
        and m["score"]["fullTime"]["home"] is not None
    ]


if __name__ == "__main__":
    key = os.environ.get("FOOTBALL_DATA_API_KEY", "")
    results = fetch_finished_matches(key)

    if not results:
        print("완료된 경기가 없거나 API 오류가 발생했어요.")
        sys.exit(1)

    print(f"완료된 경기: {len(results)}개\n")
    for r in results:
        label = f"[{r['stage']} {r['group']}]" if r["group"] else f"[{r['stage']}]"
        print(f"{label:12} {r['home']:20} {r['home_score']}-{r['away_score']} {r['away']}")