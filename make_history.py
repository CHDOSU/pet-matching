"""과거 구조동물 기록(animals.csv, 5,897건)과 보호센터 샘플을 만든다.

실제 animals.csv 가 있으면 data/animals.csv 를 그 파일로 바꾸기만 하면 된다.
필드는 구조동물 조회 API 응답과 같고, processState 에 처리 결과(종료(입양) 등)가 들어 있다.
"""
import csv
import json
import math
import random

from make_sample import CAT_KINDS, CAT_TRAITS, COLORS, DOG_KINDS, DOG_WEIGHT, REGIONS, TRAITS

random.seed(7)
N = 5897
CENTER = {"서울특별시": (37.56, 126.98), "경기도": (37.41, 127.25), "인천광역시": (37.45, 126.70),
          "부산광역시": (35.18, 129.07), "대전광역시": (36.35, 127.38), "대구광역시": (35.87, 128.60),
          "광주광역시": (35.16, 126.85)}
POPULAR = {"푸들", "말티즈", "포메라니안", "웰시 코기", "골든 리트리버", "러시안 블루", "스코티시 폴드", "먼치킨", "페르시안"}


def record(i):
    is_cat = random.random() < 0.3
    kind = random.choice(CAT_KINDS if is_cat else DOG_KINDS + ["믹스견"] * 6)
    lo, hi = (2.5, 6) if is_cat else DOG_WEIGHT[kind]
    year = random.choice([2023, 2024, 2025])
    month = random.randint(1, 12)
    age = random.choices([0, 1, 2, 3, 5, 7, 9, 12], weights=[25, 15, 12, 10, 12, 9, 9, 8])[0]
    weight = round(random.uniform(lo, hi) * (0.5 if age == 0 else 1), 1)
    sido, guns = random.choice(REGIONS)
    gun = random.choice(guns)
    traits = random.sample(CAT_TRAITS if is_cat else TRAITS, k=random.randint(2, 3))
    mark = ", ".join(traits)
    neuter = random.choice(["Y", "N", "U"])

    # 입양 확률: 어릴수록, 작을수록, 인기 품종·친화적·중성화·수도권일수록 높고 치료 필요·노령은 낮다
    size = "소형" if is_cat or weight < 7 else "중형" if weight < 15 else "대형"
    z = -0.4 + {0: 1.3, 1: 0.8, 2: 0.4, 3: 0.2, 5: -0.2, 7: -0.6, 9: -1.1, 12: -1.6}[age]
    z += {"소형": 0.5, "중형": -0.1, "대형": -0.7}[size] + (0.7 if kind in POPULAR else 0)
    z += 0.4 if any(k in mark for k in ["사람을 잘", "애교", "안기는", "아이들과"]) else 0
    z -= 0.9 if "치료" in mark else 0
    z -= 0.4 if any(k in mark for k in ["겁", "경계", "짖음"]) else 0
    z += 0.3 if neuter == "Y" else 0
    z += 0.3 if sido in ("서울특별시", "경기도") else 0
    z += random.gauss(0, 0.6)
    p = 1 / (1 + math.exp(-z))
    r = random.random()
    if r < 0.08:
        state = "종료(반환)"
    elif random.random() < p:
        state = "종료(입양)"
    else:
        state = random.choices(["종료(자연사)", "종료(안락사)", "종료(기증)", "종료(방사)"], weights=[45, 35, 12, 8])[0]
    return {
        "desertionNo": f"4481{year}{i:07d}", "happenDt": f"{year}{month:02d}{random.randint(1, 28):02d}",
        "upKindNm": "고양이" if is_cat else "개", "kindNm": kind, "colorCd": random.choice(COLORS),
        "age": f"{year - age}(년생)", "weight": f"{weight}(Kg)", "sexCd": random.choice(["M", "F", "Q"]),
        "neuterYn": neuter, "specialMark": mark, "careNm": f"{gun} 동물보호센터",
        "careAddr": f"{sido} {gun} 보호소로 {random.randint(1, 200)}", "orgNm": f"{sido} {gun}",
        "processState": state,
    }


def shelters():
    out = []
    for sido, guns in REGIONS:
        lat, lng = CENTER[sido]
        for gun in guns:
            out.append({
                "careNm": f"{gun} 동물보호센터", "orgNm": f"{sido} {gun}", "divisionNm": "법인",
                "careAddr": f"{sido} {gun} 보호소로 1", "careTel": f"0{random.randint(2, 64)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}",
                "lat": round(lat + random.uniform(-0.12, 0.12), 5), "lng": round(lng + random.uniform(-0.12, 0.12), 5),
                "weekOprStime": "09:00", "weekOprEttime": "18:00", "closeDay": "매주 월요일",
                "saveTrgtAnimal": "개+고양이",
            })
    return out


if __name__ == "__main__":
    rows = [record(i) for i in range(1, N + 1)]
    with open("data/animals.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    with open("data/sample_shelters.json", "w", encoding="utf-8") as f:
        json.dump(shelters(), f, ensure_ascii=False, indent=1)
    print(N, "건 기록,", len(shelters()), "개 보호센터 생성")
