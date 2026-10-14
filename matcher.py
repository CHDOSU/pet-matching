"""사용자 생활환경·선호와 구조동물의 특성을 비교해 적합도 점수(0~100)를 계산한다."""
import re
from dataclasses import dataclass, field
from datetime import date

# specialMark(특이사항) 문장에서 성격·건강 태그를 뽑는 키워드 사전
TRAIT_KEYWORDS = {
    "활발": ["활발", "에너지", "산책을 매우", "사냥놀이", "장난감", "호기심"],
    "차분": ["차분", "조용", "얌전", "온순", "독립"],
    "친화": ["사람을 잘", "애교", "안기는", "골골", "따르"],
    "소심": ["겁", "낯", "경계", "숨어", "적응 시간"],
    "아이친화": ["아이들과"],
    "동물친화": ["다른 강아지", "다른 고양이"],
    "짖음": ["짖"],
    "치료필요": ["치료", "피부병", "양성", "구내염", "질병"],
    "훈련됨": ["배변 훈련", "화장실 잘"],
}


@dataclass
class UserProfile:
    species: str = "상관없음"          # 개 / 고양이 / 상관없음
    housing: str = "아파트"            # 원룸 / 아파트 / 단독주택
    walk_minutes: int = 30             # 하루 산책·놀이 가능 시간(분)
    alone_hours: int = 8               # 하루 집을 비우는 시간
    experience: bool = False           # 반려동물 키워본 경험
    has_kids: bool = False
    has_pets: bool = False
    size_pref: str = "상관없음"        # 소형 / 중형 / 대형 / 상관없음
    age_pref: str = "상관없음"         # 어린 / 성체 / 노령 / 상관없음
    region: str = "전체"
    wish_text: str = ""                # 원하는 성격 자유 서술
    care_ok: bool = False              # 치료가 필요한 아이도 괜찮은지


@dataclass
class Animal:
    raw: dict
    species: str
    weight: float
    age_years: int
    size: str
    age_group: str
    traits: set = field(default_factory=set)


def _num(text, default=0.0):
    m = re.search(r"\d+(\.\d+)?", text or "")
    return float(m.group()) if m else default


def parse_animal(raw):
    species = raw.get("upKindNm") or ("고양이" if "고양이" in raw.get("kindCd", "") else "개")
    weight = _num(raw.get("weight"), 5.0)
    birth = int(_num(raw.get("age"), date.today().year))
    age_years = max(0, date.today().year - birth)
    if species == "고양이":
        size = "소형"
    else:
        size = "소형" if weight < 7 else "중형" if weight < 15 else "대형"
    age_group = "어린" if age_years <= 1 else "성체" if age_years <= 7 else "노령"
    mark = raw.get("specialMark", "")
    traits = {t for t, kws in TRAIT_KEYWORDS.items() if any(k in mark for k in kws)}
    return Animal(raw, species, weight, age_years, size, age_group, traits)


def _bigrams(text):
    t = re.sub(r"\s+", "", text)
    return {t[i:i + 2] for i in range(len(t) - 1)}


def text_similarity(a, b):
    """한국어 형태소 분석기 없이 쓸 수 있는 글자 2-gram 자카드 유사도."""
    x, y = _bigrams(a), _bigrams(b)
    return len(x & y) / len(x | y) if x and y else 0.0


def score(user: UserProfile, a: Animal):
    """(점수, 이유 목록) 반환. 종이나 지역이 맞지 않으면 None."""
    if user.species != "상관없음" and a.species != user.species:
        return None
    if user.region != "전체" and user.region not in a.raw.get("careAddr", "") + a.raw.get("orgNm", ""):
        return None

    s, reasons = 50.0, []

    def add(points, why):
        nonlocal s
        s += points
        reasons.append(("👍 " if points > 0 else "⚠️ ") + why)

    # 1) 주거 형태 × 크기
    if user.housing == "원룸":
        if a.size == "대형":
            add(-20, "원룸에서 대형견은 공간이 부족할 수 있어요")
        elif a.size == "소형":
            add(8, "작은 공간에서도 지내기 좋은 크기예요")
    elif user.housing == "단독주택" and a.size == "대형":
        add(8, "마당·넓은 공간이 있어 대형견에게 좋아요")

    # 2) 선호 크기·나이
    if user.size_pref != "상관없음":
        add(10, f"원하시는 {a.size} 크기예요") if a.size == user.size_pref else add(-8, f"원하는 크기와 달라요({a.size})")
    if user.age_pref != "상관없음":
        add(8, f"원하시는 연령대({a.age_group})예요") if a.age_group == user.age_pref else add(-5, f"원하는 연령대와 달라요({a.age_group})")

    # 3) 활동량: 개는 산책 시간, 활발한 아이는 놀이 시간이 중요
    need = 20 if a.species == "고양이" else {"소형": 30, "중형": 50, "대형": 70}[a.size]
    if "활발" in a.traits:
        need += 20
    if user.walk_minutes >= need:
        add(10, f"하루 {user.walk_minutes}분이면 이 아이의 활동량을 채울 수 있어요")
    else:
        add(-min(20, (need - user.walk_minutes) // 3), f"하루 약 {need}분의 산책·놀이가 필요해요")

    # 4) 혼자 있는 시간
    if user.alone_hours >= 9:
        if a.species == "고양이" or "차분" in a.traits:
            add(8, "혼자 있는 시간에도 비교적 잘 지내는 편이에요")
        elif a.age_group == "어린" or "친화" in a.traits:
            add(-10, "어리거나 사람을 많이 따라서 오래 혼자 두면 힘들어해요")

    # 5) 경험·가족 구성
    if not user.experience:
        if "소심" in a.traits or "치료필요" in a.traits:
            add(-10, "처음 키우시는 분께는 적응·관리 난이도가 있어요")
        if "훈련됨" in a.traits or "차분" in a.traits:
            add(6, "초보 보호자도 함께하기 수월해요")
    if user.has_kids:
        add(10, "아이들과 잘 어울려요") if "아이친화" in a.traits else (add(-8, "겁이 많아 아이와 지내려면 적응이 필요해요") if "소심" in a.traits else None)
    if user.has_pets and "동물친화" in a.traits:
        add(8, "다른 동물과 잘 지내요")
    if user.housing in ("원룸", "아파트") and "짖음" in a.traits:
        add(-6, "짖음이 있어 공동주택에서는 훈련이 필요해요")
    if "치료필요" in a.traits:
        add(5, "치료가 필요한 아이에게 새 가족이 되어주실 수 있어요") if user.care_ok else add(-8, "치료·관리가 필요해요")

    # 6) 사람 친화도·중성화는 누구에게나 작은 가산점
    if "친화" in a.traits:
        add(4, "사람을 잘 따라요")
    if a.raw.get("neuterYn") == "Y":
        add(3, "중성화가 되어 있어요")

    # 7) 원하는 성격 자유 서술과의 텍스트 유사도
    if user.wish_text.strip():
        sim = text_similarity(user.wish_text, a.raw.get("specialMark", ""))
        if sim > 0.05:
            add(round(sim * 60), "원하시는 성격 설명과 특이사항이 비슷해요")

    return max(0, min(100, round(s))), reasons


def recommend(user: UserProfile, raw_animals, top_n=10):
    results = []
    for raw in raw_animals:
        a = parse_animal(raw)
        r = score(user, a)
        if r:
            results.append((r[0], a, r[1]))
    # 점수가 같으면 공고 마감이 빠른(입양이 더 급한) 아이를 먼저 보여준다
    results.sort(key=lambda x: (-x[0], x[1].raw.get("noticeEdt", "")))
    return results[:top_n]
