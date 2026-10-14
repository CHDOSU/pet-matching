"""외부 데이터: 구조동물 API(현재 공고 실시간) + 보호센터 API(연락처·위치).

환경변수 DATA_GO_KR_KEY(또는 화면에서 입력한 키)가 있으면 공공데이터포털을 호출하고,
없거나 실패하면 같은 형식의 샘플 파일을 쓴다.
"""
import json
import os
from datetime import date, timedelta
from pathlib import Path

import requests

BASE = "https://apis.data.go.kr/1543061"
ANIMAL_URL = f"{BASE}/abandonmentPublicService_v2/abandonmentPublic_v2"
SHELTER_URL = f"{BASE}/animalShelterSrvc_v2/shelterInfo_v2"
HERE = Path(__file__).parent


def _items(url, params):
    res = requests.get(url, params={**params, "_type": "json"}, timeout=15)
    res.raise_for_status()
    items = res.json()["response"]["body"]["items"]
    if not items:
        return []
    item = items["item"]
    return item if isinstance(item, list) else [item]


def _key(service_key):
    return service_key or os.environ.get("DATA_GO_KR_KEY")


def load_animals(service_key=None, days=30, rows=500):
    """보호 중인 구조동물 목록과 출처 설명."""
    key = _key(service_key)
    if key:
        try:
            animals = _items(ANIMAL_URL, {
                "serviceKey": key, "state": "protect", "pageNo": 1, "numOfRows": rows,
                "bgnde": (date.today() - timedelta(days=days)).strftime("%Y%m%d"),
                "endde": date.today().strftime("%Y%m%d"),
            })
            if animals:
                return animals, f"구조동물 API 실시간 ({len(animals)}마리)"
        except Exception as e:
            return _json("sample_animals.json"), f"구조동물 API 호출 실패({e.__class__.__name__}), 샘플 사용"
    return _json("sample_animals.json"), "샘플 데이터 (API 키 없음)"


def load_shelters(service_key=None):
    """보호센터 이름 → {연락처, 주소, 위도·경도, 운영시간} 사전."""
    key = _key(service_key)
    shelters = None
    if key:
        try:
            shelters = _items(SHELTER_URL, {"serviceKey": key, "pageNo": 1, "numOfRows": 1000})
        except Exception:
            shelters = None
    shelters = shelters or _json("data/sample_shelters.json")
    return {s["careNm"]: s for s in shelters}


def _json(rel):
    with open(HERE / rel, encoding="utf-8") as f:
        return json.load(f)
