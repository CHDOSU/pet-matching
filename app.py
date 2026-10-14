"""반려동물 입양 매칭 - 실행: streamlit run app.py"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from data_source import load_animals, load_shelters
from llm import parse_conditions, summarize
from matcher import UserProfile
from recommender import CENTER, load_model, recommend

HERE = Path(__file__).parent
st.set_page_config(page_title="반려동물 입양 매칭", page_icon="🐾", layout="wide")


@st.cache_data(ttl=3600)
def get_data(key):
    animals, source = load_animals(key or None)
    return animals, source, load_shelters(key or None)


@st.cache_resource
def get_model():
    return load_model()


@st.cache_data
def get_history():
    return pd.read_csv(HERE / "data" / "processed.csv")


@st.cache_data(show_spinner=False)
def get_summary(desertion_no, raw_json, reasons, prob):
    return summarize(json.loads(raw_json), reasons, prob)


DEFAULTS = {"species": "상관없음", "housing": "아파트", "walk_minutes": 40, "alone_hours": 8,
            "experience": False, "has_kids": False, "has_pets": False, "size_pref": "상관없음",
            "age_pref": "상관없음", "region": "전체", "wish_text": ""}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)

# ---------- 사이드바: 데이터·조건 입력 ----------
with st.sidebar:
    with st.expander("🔑 API 키 (선택)"):
        key = st.text_input("공공데이터포털 서비스키", type="password")
    animals, source, shelters = get_data(key)
    model = get_model()
    st.caption(f"데이터: {source}  \n모델: {'학습됨' if model else '없음 (train_model.py 실행 필요)'}")

    regions = sorted({a.get("careAddr", "").split(" ")[0] for a in animals if a.get("careAddr")})
    st.header("🏠 나의 생활환경")
    st.radio("원하는 동물", ["상관없음", "개", "고양이"], horizontal=True, key="species")
    st.selectbox("주거 형태", ["원룸", "아파트", "단독주택"], key="housing")
    st.slider("하루 산책·놀이 가능 시간(분)", 0, 180, step=10, key="walk_minutes")
    st.slider("하루 집을 비우는 시간", 0, 14, key="alone_hours")
    st.checkbox("반려동물을 키워본 적 있어요", key="experience")
    st.checkbox("집에 어린 아이가 있어요", key="has_kids")
    st.checkbox("다른 반려동물이 있어요", key="has_pets")
    care_ok = st.checkbox("치료가 필요한 아이도 괜찮아요")
    st.header("💕 선호")
    st.selectbox("크기", ["상관없음", "소형", "중형", "대형"], key="size_pref")
    st.selectbox("나이", ["상관없음", "어린", "성체", "노령"], key="age_pref")
    if st.session_state.region not in ["전체"] + regions:
        st.session_state.region = "전체"
    st.selectbox("보호소 지역", ["전체"] + regions, key="region")
    home = st.selectbox("내가 사는 곳 (거리 계산)", ["선택 안 함"] + list(CENTER))
    st.text_input("원하는 성격", key="wish_text", placeholder="예: 얌전하고 사람을 잘 따르는")
    urgency_w = st.slider("입양이 어려운 아이 우선 반영", 0.0, 0.5, 0.2, 0.05,
                          help="모델이 예측한 입양 가능성이 낮은 아이에게 가산점을 주는 비율")
    top_n = st.slider("추천 개수", 3, 18, 6, step=3)

# ---------- 상단: 자연어 조건 입력 (LLM 조건 변환) ----------
st.title("🐾 유기동물 입양 매칭")
st.caption("과거 5,897건의 보호 기록으로 학습한 입양 가능성 모델과 실시간 구조동물 공고를 함께 써서, 나와 잘 맞는 아이를 찾아드려요.")

def apply_text(regions):
    """폼 제출 콜백: 위젯이 그려지기 전에 실행되므로 사이드바 값을 바꿀 수 있다."""
    text = st.session_state.get("nl_text", "")
    if not text.strip():
        return
    cond, how = parse_conditions(text, regions)
    for k, v in cond.items():
        if k in DEFAULTS:
            st.session_state[k] = v
    st.session_state["parsed_by"] = how


with st.form("nl"):
    st.text_area("어떤 아이를 찾으세요? 편하게 적어 주세요", key="nl_text", height=80,
                 placeholder="예: 서울 원룸에 혼자 살고 출근하면 9시간 정도 비워요. 처음 키워보고, 얌전한 고양이면 좋겠어요.")
    st.form_submit_button("조건으로 변환 ✨", on_click=apply_text, args=(regions,))
if "parsed_by" in st.session_state:
    st.success(f"왼쪽 조건을 채웠어요 ({st.session_state.parsed_by} 기반). 필요하면 직접 고쳐 주세요.")

user = UserProfile(**{k: st.session_state[k] for k in DEFAULTS}, care_ok=care_ok)
results = recommend(user, animals, shelters, model, urgency_w, home if home in CENTER else None, top_n)

tab_rec, tab_detail, tab_ana = st.tabs(["추천 카드", "상세 보기", "분석"])

# ---------- 추천 카드 ----------
with tab_rec:
    if not results:
        st.warning("조건에 맞는 아이가 없어요. 지역이나 동물 종류를 넓혀 보세요.")
    for i in range(0, len(results), 3):
        cols = st.columns(3)
        for col, r in zip(cols, results[i:i + 3]):
            a, raw = r["animal"], r["animal"].raw
            with col.container(border=True):
                if raw.get("popfile1"):
                    st.image(raw["popfile1"], use_container_width=True)
                st.subheader(f"{'🐶' if a.species == '개' else '🐱'} {raw.get('kindNm', '')}")
                st.progress(r["score"] / 100, text=f"추천 점수 {r['score']}점")
                st.caption(f"생활환경 적합도 {r['fit']}점 · 예상 입양 가능성 {r['prob']:.0%}")
                sex = {"M": "수컷", "F": "암컷"}.get(raw.get("sexCd"), "성별 미상")
                st.write(f"{a.age_group}({a.age_years}살) · {a.size} {a.weight}kg · {sex}")
                st.write(f"📝 {raw.get('specialMark', '')}")
                with st.expander("추천 이유"):
                    for why in r["reasons"]:
                        st.write(why)
                dist = f" · 약 {r['distance']:.0f}km" if r["distance"] is not None else ""
                st.caption(f"📍 {raw.get('careNm', '')}{dist}  \n공고 마감 {raw.get('noticeEdt', '')}")

# ---------- 상세 보기 ----------
with tab_detail:
    if results:
        labels = [f"{i + 1}. {r['animal'].raw.get('kindNm')} ({r['animal'].raw.get('careNm')}) - {r['score']}점"
                  for i, r in enumerate(results)]
        r = results[st.selectbox("추천된 아이 선택", range(len(results)), format_func=lambda i: labels[i])]
        a, raw, sh = r["animal"], r["animal"].raw, r["shelter"]
        left, right = st.columns([3, 2])
        with left:
            st.subheader(f"{raw.get('kindNm')} · {raw.get('colorCd', '')}")
            with st.spinner("소개글 쓰는 중..."):
                intro, how = get_summary(raw.get("desertionNo"), json.dumps(raw, ensure_ascii=False),
                                         tuple(r["reasons"]), r["prob"])
            st.info(intro)
            st.caption(f"소개글: {how} 기반")
            c1, c2, c3 = st.columns(3)
            c1.metric("추천 점수", r["score"])
            c2.metric("생활환경 적합도", r["fit"])
            c3.metric("예상 입양 가능성", f"{r['prob']:.0%}")
            st.table(pd.DataFrame({
                "항목": ["공고번호", "나이", "체중", "성별", "중성화", "발견 장소", "공고 기간", "특이사항"],
                "내용": [raw.get("noticeNo", ""), f"{raw.get('age', '')} ({a.age_group})", raw.get("weight", ""),
                       {"M": "수컷", "F": "암컷"}.get(raw.get("sexCd"), "미상"),
                       {"Y": "완료", "N": "안 함"}.get(raw.get("neuterYn"), "미상"), raw.get("happenPlace", ""),
                       f"{raw.get('noticeSdt', '')} ~ {raw.get('noticeEdt', '')}", raw.get("specialMark", "")],
            }).set_index("항목"))
            st.write("**추천 이유**")
            for why in r["reasons"]:
                st.write(why)
        with right:
            st.subheader("🏥 보호센터")
            st.write(f"**{raw.get('careNm', '')}**")
            st.write(f"📞 {sh.get('careTel') or raw.get('careTel', '')}")
            st.write(f"📍 {sh.get('careAddr') or raw.get('careAddr', '')}")
            if sh.get("weekOprStime"):
                st.write(f"🕘 평일 {sh['weekOprStime']}~{sh.get('weekOprEttime', '')} · 휴무 {sh.get('closeDay', '-')}")
            if sh.get("lat"):
                st.map(pd.DataFrame({"lat": [float(sh["lat"])], "lon": [float(sh["lng"])]}), zoom=10)

# ---------- 분석 ----------
with tab_ana:
    hist = get_history()
    metrics_path = HERE / "models" / "metrics.json"
    st.subheader("과거 보호 기록 (animals.csv)")
    c1, c2, c3 = st.columns(3)
    c1.metric("학습에 쓴 기록", f"{len(hist):,}건")
    c2.metric("전체 입양률", f"{hist.adopted.mean():.1%}")
    c3.metric("현재 보호 중 (공고)", f"{len(animals)}마리")
    g1, g2 = st.columns(2)
    with g1:
        st.write("연령대별 입양률")
        st.bar_chart(hist.groupby("age_group").adopted.mean().reindex(["어린", "성체", "노령"]))
    with g2:
        st.write("종·크기별 입양률")
        st.bar_chart(hist.assign(g=hist.species + " " + hist["size"]).groupby("g").adopted.mean())
    st.write("월별 입양 건수")
    st.line_chart(hist[hist.adopted == 1].groupby("happen_month").size())
    if metrics_path.exists():
        m = json.loads(metrics_path.read_text(encoding="utf-8"))
        st.subheader("입양 가능성 모델")
        st.write(f"채택 모델: **{m['best_model']}** (학습 {m['n_train']:,}건 / 평가 {m['n_test']:,}건)")
        st.dataframe(pd.DataFrame(m["models"]).T.rename(columns={"auc": "AUC", "accuracy": "정확도"}))
        st.write("특징 중요도 (순열 중요도, AUC 감소량)")
        imp = pd.DataFrame(m["importance"]).set_index("feature")
        st.bar_chart(imp[imp.importance > 0].sort_values("importance"), horizontal=True)
