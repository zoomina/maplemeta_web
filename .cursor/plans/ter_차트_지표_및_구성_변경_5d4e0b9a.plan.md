---
name: TER 차트 지표 및 구성 변경
overview: x축 지표를 TER(분당 층수) 대신 record_sec/floor(층당 소요 초)로 단순화하고, 여유구간 30% 적용, diverging bar(위=50층 이상/아래=50층 미만), 직업별 스택, 고효율 3위 원형 썸네일을 반영합니다.
todos: []
isProject: false
---

# TER 차트 지표 단순화 및 그래프 구성 변경 (수정)

## 지표 변경 (핵심)

**기존 (복잡)**  

- TER = floor / record_sec * 60 → "분당 클리어 층수" (높을수록 효율 좋음)

**변경 (단순)**  

- **x축 = record_sec / floor** → "층당 소요 초" (한 층당 몇 초 걸렸는지)
- **낮을수록** 같은 시간에 더 많이 클리어 = 효율 좋음. 운영/이해 모두 쉬움.

이하 백엔드·프론트·구간 정의는 이 지표 기준으로 통일.

---

## 1. 백엔드

**파일**: `[backend/services/repositories/meta_repository.py](backend/services/repositories/meta_repository.py)`

- `**_compute_ter` → 지표를 record_sec/floor로 변경**
  - 40~69층, record_sec > 0 필터 유지.
  - **sec_per_floor = record_sec / floor** 계산 (TER 대신).
  - is_floor50 = (floor >= 50) 유지.
  - 직업별: **sec_per_floor_p50** (median 층당초), floor50_rate, n, n_50plus, n_below50.
  - **여유구간**: 50층 이상 레코드의 sec_per_floor **하위 30%** 구간 → relaxed_lo, relaxed_hi (0%ile, 30%ile).
  - **근접구간**: 50층 미만 레코드의 sec_per_floor **하위 30%** 구간 → near_lo, near_hi.
  - 직업별 **n_in_relaxed**: 해당 직업의 50+ 레코드 중 sec_per_floor가 [relaxed_lo, relaxed_hi] 안에 있는 개수.
  - 반환: ter DataFrame (job_name, sec_per_floor_p50, floor50_rate, n, n_50plus, n_below50, n_in_relaxed) + ter_bands (relaxed_lo/hi, near_lo/hi).

**API** `[backend/api/meta.py](backend/api/meta.py)`: ter 항목에 sec_per_floor_p50 및 위 필드들, 응답에 ter_bands 포함.

---

## 2. 프론트엔드

- **타입**: TERJobData에 ter_p50 대신 **sec_per_floor_p50** (또는 호환용 ter_p50 이름 유지하고 값만 층당초로). n, n_50plus, n_below50, n_in_relaxed, ter_bands 타입 추가.
- **TERChart**
  - x축: **record_sec/floor (층당 소요 초)** 구간으로 bin (20개). 축 라벨 예: "층당 소요 시간(초)".
  - y축 위 = 50층 이상 인원, y축 아래 = 50층 미만 인원 (diverging bar). 직업별 스택 유지.
  - 여유구간: 50+ 쪽 markArea — sec_per_floor **낮은 쪽** 30% 구간 (relaxed_lo ~ relaxed_hi).
  - 근접구간: 50- 쪽 markArea — 동일하게 낮은 30% 구간 (near_lo ~ near_hi).
  - 고효율 상위 3위: n_in_relaxed 기준, BumpChart와 동일한 원형 썸네일(심볼 컬러 테두리)로 그래프 위에 표시.

---

## 3. 요약


| 항목       | 내용                                                  |
| -------- | --------------------------------------------------- |
| x축 지표    | **record_sec / floor** (층당 소요 초)                    |
| 해석       | 값이 **작을수록** 효율 좋음                                   |
| 여유/근접 구간 | 각각 50+ / 50- 레코드의 층당초 **하위 30%** 구간                 |
| 차트       | x축 위쪽 = 50층 이상, 아래쪽 = 50층 미만, 직업별 스택, 고효율 3위 원형 썸네일 |


이렇게 하면 "한 층당 몇 초" 하나의 숫자로 통일되어 운영 측 이해와 유지보수가 쉬워집니다.