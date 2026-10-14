"""추천 엔진: 필터 + 점수 계산.

최종 점수 = 생활환경 적합도(matcher) × (1 - w) + 입양 시급도 × w  (+ 거리 보정)
입양 시급도는 학습된 모델이 예측한 입양 가능성이 낮을수록 높다. 비슷하게 잘 맞는 아이라면
입양되기 어려운 아이를 먼저 보여주자는 취지이며, w 는 화면에서 조절한다.
"""
import math
from datetime import date
from pathlib import Path

import joblib
import pandas as pd

from matcher import parse_animal, score
from preprocess import FEATURES_CAT, FEATURES_NUM, featurize

MODEL_PATH = Path(__file__).with_name("models") / "adoption_model.joblib"
CENTER = {"서울특별시": (37.56, 126.98), "경기도": (37.41, 127.25), "인천광역시": (37.45, 126.70),
          "부산광역시": (35.18, 129.07), "대전광역시": (36.35, 127.38), "대구광역시": (35.87, 128.60),
          "광주광역시": (35.16, 126.85), "울산광역시": (35.54, 129.31), "세종특별자치시": (36.48, 127.29),
          "강원특별자치도": (37.88, 127.73), "충청북도": (36.64, 127.49), "충청남도": (36.66, 126.67),
          "전북특별자치도": (35.82, 127.15), "전라남도": (34.82, 126.46), "경상북도": (36.58, 128.51),
          "경상남도": (35.24, 128.69), "제주특별자치도": (33.50, 126.53)}


def load_model():
    return joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None


def adoption_prob(model, raw_animals):
    if model is None or not raw_animals:
        return [0.5] * len(raw_animals)
    df = pd.DataFrame(raw_animals)
    for col in ["upKindNm", "weight", "age", "sexCd", "neuterYn", "kindNm", "careAddr", "specialMark"]:
        if col not in df:
            df[col] = None
    X = featurize(df, ref_year=date.today().year)[FEATURES_CAT + FEATURES_NUM]
    return model.predict_proba(X)[:, 1].tolist()


def km(a, b):
    (la1, lo1), (la2, lo2) = a, b
    dx = (lo2 - lo1) * 88.0 * math.cos(math.radians((la1 + la2) / 2)) / 0.99
    dy = (la2 - la1) * 111.0
    return math.hypot(dx, dy)


def recommend(user, raw_animals, shelters, model, urgency_weight=0.2, home=None, top_n=10):
    probs = adoption_prob(model, raw_animals)
    results = []
    for raw, p in zip(raw_animals, probs):
        a = parse_animal(raw)
        r = score(user, a)
        if not r:
            continue
        fit, reasons = r
        shelter = shelters.get(raw.get("careNm"), {})
        dist = None
        if home in CENTER and shelter.get("lat"):
            dist = km(CENTER[home], (float(shelter["lat"]), float(shelter["lng"])))
            if dist > 150:
                fit -= 8
                reasons.append(f"⚠️ 보호소까지 약 {dist:.0f}km로 방문이 멀어요")
            elif dist < 30:
                fit += 4
                reasons.append(f"👍 보호소가 가까워요 (약 {dist:.0f}km)")
        urgency = (1 - p) * 100
        final = round((1 - urgency_weight) * max(0, min(100, fit)) + urgency_weight * urgency)
        results.append({"score": final, "fit": max(0, min(100, fit)), "prob": p, "animal": a,
                        "reasons": reasons, "shelter": shelter, "distance": dist})
    results.sort(key=lambda d: (-d["score"], d["animal"].raw.get("noticeEdt", "")))
    return results[:top_n]
