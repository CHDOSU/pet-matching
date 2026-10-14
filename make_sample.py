"""샘플 데이터 생성기: 공공데이터포털 '구조동물 조회(abandonmentPublic_v2)' 응답과 같은 필드로 만든다."""
import json
import random

random.seed(42)

DOG_KINDS = ["믹스견", "진돗개", "푸들", "말티즈", "시츄", "포메라니안", "비글", "골든 리트리버", "웰시 코기", "치와와", "보더 콜리", "풍산개"]
CAT_KINDS = ["코리안 숏헤어", "페르시안", "러시안 블루", "터키시 앙고라", "스코티시 폴드", "먼치킨"]
DOG_WEIGHT = {"치와와": (1.5, 3), "말티즈": (2, 4), "포메라니안": (2, 4), "푸들": (3, 7), "시츄": (4, 7),
              "비글": (9, 13), "웰시 코기": (10, 14), "믹스견": (4, 22), "진돗개": (15, 22),
              "보더 콜리": (14, 20), "골든 리트리버": (25, 32), "풍산개": (22, 30)}
COLORS = ["흰색", "검정색", "갈색", "황색", "회색", "크림색", "흰색&갈색", "삼색", "치즈색", "고등어"]
REGIONS = [("서울특별시", ["강남구", "마포구", "노원구"]), ("경기도", ["수원시", "고양시", "용인시"]),
           ("인천광역시", ["남동구", "서구"]), ("부산광역시", ["해운대구", "사하구"]),
           ("대전광역시", ["유성구", "서구"]), ("대구광역시", ["수성구", "달서구"]), ("광주광역시", ["북구"])]
TRAITS = ["사람을 잘 따르고 애교가 많음", "온순하고 얌전함", "활발하고 에너지가 넘침", "겁이 많고 낯을 가림",
          "차분하고 조용함", "산책을 매우 좋아함", "아이들과 잘 어울림", "다른 강아지와 잘 지냄",
          "경계심이 있어 적응 시간 필요", "짖음이 다소 있음", "장난감 놀이를 좋아함", "독립적인 성격",
          "피부병 치료 중", "심장사상충 양성으로 치료 필요", "건강 양호", "배변 훈련 되어 있음",
          "안기는 것을 좋아함", "호기심이 많음"]
CAT_TRAITS = ["사람을 잘 따르고 골골송을 부름", "온순하고 얌전함", "활발하고 사냥놀이를 좋아함", "겁이 많고 숨어 있음",
              "차분하고 조용함", "다른 고양이와 잘 지냄", "독립적인 성격", "구내염 치료 중", "건강 양호",
              "화장실 잘 가림", "안기는 것을 좋아함", "호기심이 많음", "아이들과 잘 어울림"]


def make(i):
    is_cat = random.random() < 0.35
    kind = random.choice(CAT_KINDS if is_cat else DOG_KINDS)
    lo, hi = (2.5, 6) if is_cat else DOG_WEIGHT[kind]
    birth = random.choice([2026, 2025, 2025, 2024, 2023, 2022, 2021, 2019, 2017, 2016])
    weight = round(random.uniform(lo, hi) * (0.5 if birth == 2026 else 1), 1)
    sido, guns = random.choice(REGIONS)
    gun = random.choice(guns)
    traits = random.sample(CAT_TRAITS if is_cat else TRAITS, k=random.randint(2, 3))
    day = random.randint(1, 28)
    return {
        "desertionNo": f"4481{2026}{i:06d}",
        "happenDt": f"202609{day:02d}",
        "happenPlace": f"{gun} 인근",
        "upKindCd": "422400" if is_cat else "417000",
        "upKindNm": "고양이" if is_cat else "개",
        "kindNm": kind,
        "colorCd": random.choice(COLORS),
        "age": f"{birth}(년생)" if birth < 2026 else "2026(60일미만)(년생)",
        "weight": f"{weight}(Kg)",
        "noticeNo": f"{sido[:2]}-{gun}-2026-{i:05d}",
        "noticeSdt": f"202609{day:02d}",
        "noticeEdt": f"202610{min(day + 10, 28):02d}",
        "popfile1": "",
        "processState": "보호중",
        "sexCd": random.choice(["M", "F", "Q"]),
        "neuterYn": random.choice(["Y", "N", "U"]),
        "specialMark": ", ".join(traits),
        "careNm": f"{gun} 동물보호센터",
        "careTel": f"0{random.randint(2, 64)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}",
        "careAddr": f"{sido} {gun} 보호소로 {random.randint(1, 200)}",
        "orgNm": f"{sido} {gun}",
    }


if __name__ == "__main__":
    animals = [make(i) for i in range(1, 61)]
    with open("sample_animals.json", "w", encoding="utf-8") as f:
        json.dump(animals, f, ensure_ascii=False, indent=1)
    print(len(animals), "마리 생성")
