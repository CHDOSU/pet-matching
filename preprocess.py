"""전처리·저장: 원본 기록을 크기·나이·종 등 모델 입력 특징으로 정리해 data/processed.csv 로 저장한다."""
import re
import sys

import pandas as pd

from matcher import TRAIT_KEYWORDS

POPULAR = {"푸들", "말티즈", "포메라니안", "웰시 코기", "골든 리트리버", "비숑 프리제", "러시안 블루",
           "스코티시 폴드", "먼치킨", "페르시안"}
FEATURES_CAT = ["species", "size", "age_group", "sex", "neuter", "breed_type", "sido"]
FEATURES_NUM = ["age_years", "weight"] + [f"t_{t}" for t in TRAIT_KEYWORDS]


def _num(s, default):
    m = re.search(r"\d+(\.\d+)?", str(s))
    return float(m.group()) if m else default


def featurize(df, ref_year=None):
    """API 응답 형식의 DataFrame → 특징 DataFrame. 학습과 추천에서 똑같이 쓴다."""
    out = pd.DataFrame(index=df.index)
    out["species"] = df["upKindNm"].fillna("개")
    out["weight"] = df["weight"].map(lambda s: _num(s, 5.0)).clip(0.3, 80)
    if ref_year is None:  # 과거 기록은 발견 연도 기준 나이
        ref = df["happenDt"].astype(str).str[:4].astype(int)
    else:
        ref = ref_year
    birth = df["age"].map(lambda s: _num(s, 0)).astype(int)
    out["age_years"] = (ref - birth).clip(0, 25)
    out["size"] = "소형"
    out.loc[(out.species == "개") & (out.weight >= 7), "size"] = "중형"
    out.loc[(out.species == "개") & (out.weight >= 15), "size"] = "대형"
    out["age_group"] = pd.cut(out.age_years, [-1, 1, 7, 99], labels=["어린", "성체", "노령"]).astype(str)
    out["sex"] = df["sexCd"].fillna("Q")
    out["neuter"] = df["neuterYn"].fillna("U")
    out["breed_type"] = df["kindNm"].map(lambda k: "인기품종" if k in POPULAR else "믹스" if "믹스" in str(k) or "코리안" in str(k) else "기타품종")
    out["sido"] = df["careAddr"].fillna("").str.split(" ").str[0]
    mark = df["specialMark"].fillna("")
    for t, kws in TRAIT_KEYWORDS.items():
        out[f"t_{t}"] = mark.map(lambda m: int(any(k in m for k in kws)))
    return out


def main(src="data/animals.csv", dst="data/processed.csv"):
    raw = pd.read_csv(src, dtype=str)
    raw = raw[raw["processState"] != "종료(반환)"]  # 주인에게 돌아간 경우는 입양 판단에서 제외
    feats = featurize(raw)
    feats["happen_month"] = raw["happenDt"].str[:6]
    feats["adopted"] = (raw["processState"] == "종료(입양)").astype(int)
    feats.to_csv(dst, index=False, encoding="utf-8-sig")
    print(f"{len(raw)}건 → {dst} (입양률 {feats.adopted.mean():.1%})")


if __name__ == "__main__":
    main(*sys.argv[1:])
