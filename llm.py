"""LLM API: 자연어 조건 → 매칭 조건 변환, 추천 동물 소개 요약.

ANTHROPIC_API_KEY 가 있으면 Claude API를 쓰고, 없거나 실패하면 규칙 기반으로 대신한다
(그래서 키 없이도 화면은 똑같이 동작한다).
"""
import json
import os
import re

MODEL = "claude-opus-5-5"

CONDITION_SCHEMA = {
    "type": "object",
    "properties": {
        "species": {"type": "string", "enum": ["상관없음", "개", "고양이"]},
        "housing": {"type": "string", "enum": ["원룸", "아파트", "단독주택"]},
        "walk_minutes": {"type": "integer"},
        "alone_hours": {"type": "integer"},
        "experience": {"type": "boolean"},
        "has_kids": {"type": "boolean"},
        "has_pets": {"type": "boolean"},
        "size_pref": {"type": "string", "enum": ["상관없음", "소형", "중형", "대형"]},
        "age_pref": {"type": "string", "enum": ["상관없음", "어린", "성체", "노령"]},
        "region": {"type": "string"},
        "wish_text": {"type": "string"},
    },
    "required": ["species", "housing", "walk_minutes", "alone_hours", "experience", "has_kids",
                 "has_pets", "size_pref", "age_pref", "region", "wish_text"],
    "additionalProperties": False,
}


def _client():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
        return anthropic.Anthropic()
    except ImportError:
        return None


def _ask(prompt, schema=None, max_tokens=2000):
    client = _client()
    if client is None:
        return None
    output_config = {"effort": "low"}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    try:
        res = client.beta.messages.create(
            model=MODEL, max_tokens=max_tokens, output_config=output_config,
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            messages=[{"role": "user", "content": prompt}],
        )
        if res.stop_reason == "refusal":
            return None
        return next(b.text for b in res.content if b.type == "text")
    except Exception:
        return None


def parse_conditions(text, regions):
    """자연어 → UserProfile 필드 사전. (결과, 'LLM'|'규칙') 반환."""
    out = _ask(
        "유기동물 입양을 원하는 사용자의 설명을 매칭 조건으로 바꿔 주세요. 언급되지 않은 항목은 기본값"
        "(상관없음, 아파트, 산책 30분, 혼자 8시간, false, 지역 '전체')을 쓰세요. "
        f"region 은 {['전체'] + regions} 중 하나, wish_text 에는 원하는 성격만 짧게 적으세요.\n\n설명: {text}",
        schema=CONDITION_SCHEMA)
    if out:
        try:
            cond = json.loads(out)
            if cond.get("region") not in regions:
                cond["region"] = "전체"
            return cond, "LLM"
        except json.JSONDecodeError:
            pass
    return rule_parse(text, regions), "규칙"


def rule_parse(text, regions):
    t = text
    c = {"species": "상관없음", "housing": "아파트", "walk_minutes": 30, "alone_hours": 8,
         "experience": False, "has_kids": False, "has_pets": False, "size_pref": "상관없음",
         "age_pref": "상관없음", "region": "전체", "wish_text": ""}
    if "고양이" in t or "냥" in t:
        c["species"] = "고양이"
    elif any(k in t for k in ["강아지", "개를", "개 ", "멍멍", "반려견"]):
        c["species"] = "개"
    if "원룸" in t or "오피스텔" in t:
        c["housing"] = "원룸"
    elif "주택" in t or "마당" in t:
        c["housing"] = "단독주택"
    if m := re.search(r"산책[^\d]{0,10}(\d+)\s*(분|시간)", t):
        c["walk_minutes"] = int(m.group(1)) * (60 if m.group(2) == "시간" else 1)
    if m := re.search(r"(\d+)\s*시간[^\d]{0,10}(혼자|비|집에 없|출근|외출)", t) or re.search(r"(혼자|비우|출근|외출)[^\d]{0,10}(\d+)\s*시간", t):
        c["alone_hours"] = int(next(g for g in m.groups() if g.isdigit()))
    if any(k in t for k in ["키워본", "키워 본", "경험 있", "키웠"]) and not any(k in t for k in ["처음", "없어"]):
        c["experience"] = True
    # "얌전한 아이" 처럼 동물을 가리키는 '아이'와 구분한다
    c["has_kids"] = bool(re.search(r"아이\s*(둘|하나|셋|한\s*명|두\s*명)|아이가 있|아이들과 (살|함께)|자녀|아기가|초등학생|유치원", t))
    c["has_pets"] = any(k in t for k in ["키우고 있", "다른 강아지", "다른 고양이", "둘째"])
    if any(k in t for k in ["소형", "작은"]):
        c["size_pref"] = "소형"
    elif "중형" in t:
        c["size_pref"] = "중형"
    elif any(k in t for k in ["대형", "큰 "]):
        c["size_pref"] = "대형"
    if any(k in t for k in ["새끼", "어린", "아기 강아지", "아기 고양이"]):
        c["age_pref"] = "어린"
    elif any(k in t for k in ["노령", "나이 든", "노견", "노묘"]):
        c["age_pref"] = "노령"
    elif "성견" in t or "성묘" in t:
        c["age_pref"] = "성체"
    for r in regions:
        if r[:2] in t:
            c["region"] = r
    wish = [w for w in ["얌전", "차분", "조용", "활발", "애교", "사람을 잘 따르", "독립", "순한", "온순"] if w in t]
    c["wish_text"] = " ".join(wish)
    return c


def summarize(animal_raw, reasons, prob):
    """추천 동물 소개 2~3문장. (글, 'LLM'|'규칙')"""
    info = {k: animal_raw.get(k) for k in ["upKindNm", "kindNm", "age", "weight", "sexCd", "neuterYn", "colorCd", "specialMark", "careNm"]}
    out = _ask(
        "보호소 동물을 예비 입양자에게 소개하는 따뜻하고 정직한 2~3문장을 한국어로 써 주세요. "
        "과장하지 말고 주의할 점이 있으면 한 번 언급하세요. 제목·목록 없이 문장만.\n"
        f"동물 정보: {json.dumps(info, ensure_ascii=False)}\n매칭 이유: {reasons}\n"
        f"과거 데이터 기준 예상 입양 가능성: {prob:.0%}", max_tokens=1000)
    if out:
        return out.strip(), "LLM"
    good = [r[2:] for r in reasons if r.startswith("👍")][:2]
    warn = [r[2:] for r in reasons if r.startswith("⚠️")][:1]
    s = f"{info['careNm']}에서 지내는 {info['kindNm']}예요. 특이사항은 '{info['specialMark']}'입니다."
    if good:
        s += " " + ". ".join(good) + "."
    if warn:
        s += f" 다만 {warn[0]}."
    if prob < 0.4:
        s += " 비슷한 조건의 아이들은 입양되기 어려운 편이라 관심이 더 필요해요."
    return s, "규칙"
