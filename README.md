# 🐾 유기동물 입양 매칭 (간이 웹사이트)

```
animals.csv(과거 5,897건) → preprocess.py(전처리·저장) → train_model.py(입양 가능성 모델, 오프라인 학습)
                                                                      ↓
보호센터 API(연락처·위치) ─┐                                    recommender.py(필터 + 점수) ⇄ llm.py(조건 변환·요약)
구조동물 API(현재 공고)  ──┴──────────────────────────────────────────↑
                                                                      ↓
                                                    app.py (Streamlit: 입력 · 추천 카드 · 상세 · 분석)
```

## 실행
```bash
pip install -r requirements.txt
python collect_history.py --key 일반인증키 --start 20240101 --end 20250930   # 실제 과거 기록 → data/animals.csv
# (키가 없으면 대신 python make_history.py 로 합성 데이터 생성)
python preprocess.py        # data/processed.csv
python train_model.py       # models/adoption_model.joblib, models/metrics.json
streamlit run app.py
```
키는 모두 선택입니다. 없으면 샘플 데이터와 규칙 기반 대체로 똑같이 동작합니다.
- `DATA_GO_KR_KEY`: 공공데이터포털 서비스키 (화면 사이드바에서 입력해도 됨)
- `ANTHROPIC_API_KEY`: Claude API 키 (조건 변환·소개글 생성)

## 단계별 설명
| 단계 | 파일 | 내용 |
|---|---|---|
| 과거 데이터 | `data/animals.csv` | 구조동물 API와 같은 필드 + `processState`(종료(입양)/자연사/안락사 등). 지금은 `make_history.py`로 만든 합성 데이터 |
| 전처리·저장 | `preprocess.py` | 체중→크기, 출생연도→나이·연령대, 품종→인기/믹스/기타, 특이사항→성격·건강 태그, 지역. `종료(반환)`은 제외 |
| 입양 가능성 모델 | `train_model.py` | 로지스틱 회귀와 그래디언트 부스팅을 비교해 AUC가 높은 쪽 저장 (현재 로지스틱 회귀, AUC 0.80). 순열 중요도 저장 |
| 외부 API | `data_source.py` | 구조동물 `abandonmentPublic_v2`, 보호센터 `shelterInfo_v2` (data.go.kr, 기관코드 1543061) |
| 추천 엔진 | `recommender.py`, `matcher.py` | 종·지역 필터 → 생활환경 적합도 + 입양 시급도(1 − 예측 입양 가능성) 가중 합 + 보호소 거리 보정 |
| LLM | `llm.py` | 자연어 → 매칭 조건 JSON(구조화 출력), 추천 동물 소개글. 키 없으면 정규식/템플릿 |
| 화면 | `app.py` | 자연어 입력, 추천 카드, 상세(소개글·보호센터·지도), 분석(입양률 차트·모델 성능·특징 중요도) |

최종 점수 = (1 − w) × 생활환경 적합도 + w × 입양 시급도. w(기본 0.2)는 화면의 "입양이 어려운 아이 우선 반영"으로 조절합니다.
