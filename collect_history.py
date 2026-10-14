"""과거 구조동물 기록 수집 → data/animals.csv

공공데이터포털 '구조동물 조회 서비스'(abandonmentPublic_v2)에서 기간을 한 달씩 나눠
모든 페이지를 받아오고, 처리가 끝난(종료(입양)·종료(자연사) 등) 기록만 CSV로 저장한다.

사용법:
    python collect_history.py --key 발급받은_일반인증키(Decoding) --start 20240101 --end 20250930
    (또는 환경변수 DATA_GO_KR_KEY 를 설정하고 --key 생략)
"""
import argparse
import csv
import os
import time
from datetime import date, datetime, timedelta

import requests

URL = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/abandonmentPublic_v2"
COLUMNS = ["desertionNo", "happenDt", "upKindNm", "kindNm", "colorCd", "age", "weight", "sexCd",
           "neuterYn", "specialMark", "careNm", "careAddr", "orgNm", "processState"]
ROWS = 1000  # 한 번에 받을 수 있는 최대 건수


def months(start, end):
    """[start, end] 기간을 한 달 단위 (시작, 끝) 문자열 쌍으로 나눈다."""
    cur = start
    while cur <= end:
        nxt = (cur.replace(day=1) + timedelta(days=32)).replace(day=1)
        yield cur.strftime("%Y%m%d"), min(nxt - timedelta(days=1), end).strftime("%Y%m%d")
        cur = nxt


def fetch_page(key, bgnde, endde, page, retries=3):
    params = {"serviceKey": key, "bgnde": bgnde, "endde": endde,
              "pageNo": page, "numOfRows": ROWS, "_type": "json"}
    for i in range(retries):
        try:
            res = requests.get(URL, params=params, timeout=30)
            res.raise_for_status()
            body = res.json()["response"]["body"]
            items = body.get("items") or {}
            item = items.get("item", []) if isinstance(items, dict) else []
            return (item if isinstance(item, list) else [item]), int(body.get("totalCount", 0))
        except (requests.RequestException, ValueError, KeyError) as e:
            if i == retries - 1:
                raise RuntimeError(f"{bgnde}~{endde} {page}페이지 실패: {e}\n응답: {res.text[:300] if 'res' in locals() else ''}")
            time.sleep(2 ** i)


def normalize(item):
    """v1 형식('[개] 믹스견')이 섞여 와도 v2 필드명으로 맞춘다."""
    if "upKindNm" not in item and "kindCd" in item:
        kind = item["kindCd"]
        item["upKindNm"] = "고양이" if "고양이" in kind else "개" if "[개]" in kind else "기타"
        item["kindNm"] = kind.split("]")[-1].strip()
    return {c: item.get(c, "") for c in COLUMNS}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("DATA_GO_KR_KEY"))
    ap.add_argument("--start", default=(date.today() - timedelta(days=365)).strftime("%Y%m%d"))
    ap.add_argument("--end", default=(date.today() - timedelta(days=30)).strftime("%Y%m%d"),
                    help="최근 한 달은 아직 보호 중인 경우가 많아 기본값에서 뺐다")
    ap.add_argument("--out", default="data/animals.csv")
    args = ap.parse_args()
    if not args.key:
        ap.error("--key 또는 환경변수 DATA_GO_KR_KEY 가 필요합니다")

    start, end = (datetime.strptime(d, "%Y%m%d").date() for d in (args.start, args.end))
    seen, rows = set(), []
    for bgnde, endde in months(start, end):
        page, total = 1, None
        while True:
            items, total = fetch_page(args.key, bgnde, endde, page)
            for it in items:
                if it.get("desertionNo") in seen:
                    continue
                seen.add(it.get("desertionNo"))
                if str(it.get("processState", "")).startswith("종료"):  # 결과가 정해진 기록만
                    rows.append(normalize(it))
            if page * ROWS >= total or not items:
                break
            page += 1
            time.sleep(0.2)
        print(f"{bgnde}~{endde}: 공고 {total}건, 누적 저장 {len(rows)}건")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    states = {}
    for r in rows:
        states[r["processState"]] = states.get(r["processState"], 0) + 1
    print(f"\n{args.out} 저장: {len(rows)}건")
    for s, n in sorted(states.items(), key=lambda x: -x[1]):
        print(f"  {s}: {n}건")


if __name__ == "__main__":
    main()
