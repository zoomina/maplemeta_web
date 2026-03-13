# CHANGELOG

## 260313 업데이트 (commit: f23703a)

작업 기준 문서: `note/260313_update.md`, `note/score_metric.md`, `note/프로토타입수정기획안.md`

---

### [홈] 항목 1: 카드 클릭 리다이렉트

**파일**: `frontend/src/components/home/EventCarousel.tsx`

- 기존: 카드 하단에 "바로가기 →" 텍스트 링크 별도 표시
- 변경: 카드 전체를 `<a>` 태그로 감싸서 클릭 시 URL로 이동
- url이 없는 항목은 `<div>`로 유지 (클릭 불가)

---

### [메타분석] 항목 2: KPI 게이지 차트 + Shift Score 방향성

**파일**: `frontend/src/components/meta/KPICard.tsx`

- 기존: 숫자+텍스트 단순 카드
- 변경: SVG 반원형(semicircle) 게이지 차트

**밸런스 점수** (`type="balance"`, 0~100):
- 구간별 색상: 0~34 빨강, 35~49 주황, 50~64 노랑, 65~79 라임, 80~100 초록
- 게이지 fill = score / 100

**Shift Score** (`type="shift"`, 실질 범위 약 -20~20):
- 색상: 양수 초록, ±3 이내 회색(중립), 음수 빨강
- 게이지 fill = |score| / 20 (최대 1)
- 방향 화살표: score > 3 → ▲ (상향), score < -3 → ▼ (하향)

---

### [메타분석] 항목 4 + 밸런스 메시지 개선

**파일**: `frontend/src/pages/MetaPage.tsx`, `backend/services/repositories/meta_repository.py`

**밸런스 점수 메시지** (5단계, score_metric.md + 260313_update.md 기준):
- 80~100: 직업 분포가 전반적으로 고르게 유지...
- 65~79: 전반적으로는 양호하지만, 일부 직업이 조금 더 선호...
- 50~64: 특정 직업으로의 쏠림이 조금 나타나고 있어요...
- 35~49: 특정 직업에 대한 선호가 뚜렷합니다...
- 0~34: 메타가 특정 직업에 강하게 몰려 있어요...

**p1 규칙** (`effective_score = min(score, 64)` if p1≥40%, `min(score, 49)` if p1≥50%):
- 점수가 높더라도 1위 직업 점유율이 크면 메시지 등급 강제 하향

**Shift KPI 해석 메시지** (5단계, 각 Outcome/Stat/Build):
- `shiftCaption(value, axis)` 함수, MetaPage.tsx에서 caption prop으로 전달
- 기준값: ±15 이상 → 강한 변화, ±3~15 → 완만한 변화, ±3 이내 → 변화 없음

---

### [메타분석] 항목 3: 차트 설명 텍스트 추가

**파일**: `frontend/src/pages/MetaPage.tsx`

각 차트 아래에 `<p>` 설명 텍스트 추가:
- **직업별 층수 분포**: "각 직업이 평균적으로 몇 층까지 올라갔는지, 어느 층대에 유저가 많이 분포하는지..."
- **TER 분포**: "시간 효율 비율(TER)은 분당 클리어 층수를 나타냅니다..."
- **50층 달성률 순위 추이**: "패치별로 각 직업의 50층 달성률 순위가 어떻게 변했는지..."
- **Shift 랭크**: "이전 패치 대비 메타 변화 폭이 큰 직업을 순위로 보여줍니다..."

---

### [메타분석] 항목 5: 버전 날짜 표시 + 패치 정보 카드

**파일**: `backend/api/version.py`, `frontend/src/pages/MetaPage.tsx`, `frontend/src/types/index.ts`

**백엔드 신규 엔드포인트**: `GET /api/version/list-full`
- 반환: `[{version: string, start_date: string|null}]`
- `_safe_date` 함수를 모듈 레벨로 추출 (기존 `version_detail` 내부 중복 제거)

**프론트엔드**:
- `VersionItem` 타입 추가 (`types/index.ts`)
- MetaPage: `useApi<VersionItem[]>('/api/version/list-full')` 로 버전 목록 조회
- 드롭다운 옵션에 날짜 표시: `"1.2.356 (2025-01-05)"` 형태
- 버전 선택 시 `/api/version/{version}` 호출, 패치 정보 카드 표시
  - 패치 타입 배지 (이벤트, 직업, 스킬 등)
  - 업데이트 직업 목록
  - 패치 기간 (start_date ~ end_date)

---

### [직업분석] 항목 6: Shift Score 툴팁

**파일**: `frontend/src/pages/JobPage.tsx`

- 전체 랭킹 테이블 헤더에서 `shift` 포함 컬럼 자동 감지
- `?` 버튼(원형 테두리) 추가, hover 시 `title` 속성으로 설명 표시
- 툴팁 내용: "Shift Score는 이전 패치 대비 메타 변화 크기, 양수=상향/음수=하향"

---

### [직업분석] 항목 7: 직업 전신 이미지 (storage 파일 우선)

**파일**: `backend/services/repositories/job_repository.py`, `frontend/src/pages/JobPage.tsx`

**백엔드** (`get_character_detail`):
- `img_full_raw`가 비어있을 경우 `/home/jamin/static/character/{job명}.jpg` 직접 탐색
- `.jpg` → `.jpeg` → `.webp` → `.png` 순서로 시도
- 여전히 없으면 기존 img(썸네일 URL) 폴백

**프론트엔드** (JobPage.tsx):
- `img_full_resolved`가 넥슨 썸네일 URL(`lwi.nexon.com`)이 아닌 경우에만 전신 이미지로 표시
- onError: img_full_resolved 로드 실패 시 썸네일로 자동 전환

---

### [직업분석] 항목 8: 하이퍼스탯 풀네임

**파일**: `frontend/src/pages/JobPage.tsx`

`HYPER_STAT_FULLNAME` 매핑 테이블 추가:
- `보공` → 보스 공격력
- `크뎀` → 크리티컬 데미지
- `방무` → 방어율 무시
- `공마` → 공격력/마력
- `크확` → 크리티컬 확률
- `일공` → 일반 공격력
- 기타 (`상태이상내성`, `아케인포스`, `경험치`, `hp`, `dex`, `int`, `luck`, `mpstr`, `df_tf`)

`transformHyperTop5()` 함수로 TopTable에 전달 전 `항목` 컬럼 변환.

---

### [직업분석] 항목 9: stat/item 탭 버튼 디자인 개선

**파일**: `frontend/src/pages/JobPage.tsx`

- 기존: 작은 border 버튼 2개, 텍스트 `stat` / `item`
- 변경: 연결된 탭 바 형태 (`rounded-lg overflow-hidden border`)
  - 활성 탭: `bg-[#FF8C00] text-[#0F1117]`
  - 비활성 탭: `bg-[#1A1D2E] text-[#94A3B8]`
  - 버튼 텍스트: `스탯` / `아이템` (한국어로 변경)

---

### [패치노트] 항목 10: 테이블 아웃라인

**파일**: `frontend/src/index.css`

`.prose-dark` 스코프에 테이블 CSS 추가:
- `table`: border-collapse, full width
- `thead th`: 배경색 `#1F2440`, 테두리 `#383B52`
- `tbody td`: 테두리 `#2A2D3E`, hover 시 `#1F2440` 배경
