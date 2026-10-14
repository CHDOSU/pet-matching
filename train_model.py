"""입양 가능성 모델 오프라인 학습. data/processed.csv → models/adoption_model.joblib, models/metrics.json"""
import json

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from preprocess import FEATURES_CAT, FEATURES_NUM

FEATURE_NAMES = {"species": "종", "size": "크기", "age_group": "연령대", "sex": "성별", "neuter": "중성화",
                 "breed_type": "품종 유형", "sido": "지역", "age_years": "나이", "weight": "체중"}


def build(model):
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), FEATURES_CAT),
        ("num", StandardScaler(), FEATURES_NUM),
    ])
    return Pipeline([("pre", pre), ("clf", model)])


def main():
    df = pd.read_csv("data/processed.csv")
    X, y = df[FEATURES_CAT + FEATURES_NUM], df["adopted"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=0, stratify=y)

    candidates = {
        "로지스틱 회귀": LogisticRegression(max_iter=1000),
        "그래디언트 부스팅": GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=0),
    }
    results, best = {}, None
    for name, clf in candidates.items():
        pipe = build(clf).fit(X_tr, y_tr)
        prob = pipe.predict_proba(X_te)[:, 1]
        results[name] = {"auc": round(roc_auc_score(y_te, prob), 4),
                         "accuracy": round(accuracy_score(y_te, prob >= 0.5), 4)}
        print(name, results[name])
        if best is None or results[name]["auc"] > results[best[0]]["auc"]:
            best = (name, pipe)

    name, pipe = best
    imp = permutation_importance(pipe, X_te, y_te, scoring="roc_auc", n_repeats=5, random_state=0)
    importance = sorted(
        ({"feature": FEATURE_NAMES.get(c, c.replace("t_", "성격·건강: ")), "importance": round(float(v), 4)}
         for c, v in zip(X.columns, imp.importances_mean)), key=lambda d: -d["importance"])

    joblib.dump(pipe, "models/adoption_model.joblib")
    with open("models/metrics.json", "w", encoding="utf-8") as f:
        json.dump({"best_model": name, "models": results, "n_train": len(X_tr), "n_test": len(X_te),
                   "base_rate": round(float(y.mean()), 4), "importance": importance}, f, ensure_ascii=False, indent=1)
    print("저장:", name)


if __name__ == "__main__":
    main()
