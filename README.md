# 🍁 Maple Meta Dashboard

메이플스토리 메타 분석 대시보드 웹 애플리케이션

## 주요 기능

- **홈** — 공지사항, 업데이트, 진행중인 이벤트, 캐시샵 공지 캐러셀
- **메타분석** — 밸런스 점수 KPI, 직업별 층수 분포(Violin), TER 분포, 50층 달성률 순위 추이(Bump Chart)
- **직업분석** — 직업 선택 그리드 + 랭킹 테이블 → 직업별 레이다 차트, 스탯/아이템 히스토그램
- **패치노트** — 버전별 패치노트 마크다운 뷰어

## 기술 스택

| 영역 | 기술 |
|---|---|
| 백엔드 | FastAPI, SQLAlchemy, PostgreSQL, APScheduler |
| 프론트엔드 | React 18, TypeScript, Vite, Tailwind CSS |
| 차트 | Apache ECharts (직업 아이콘 이미지 지원) |
| 배포 | Render Hobby |

## 프로젝트 구조

```
maplemeta_web/
├── backend/
│   ├── main.py              # FastAPI 앱 + self-ping 스케줄러
│   ├── api/                 # API 라우터
│   │   ├── home.py          # /api/home/*
│   │   ├── meta.py          # /api/meta
│   │   ├── job.py           # /api/job/*
│   │   └── version.py       # /api/version/*
│   ├── services/            # DB 연결 + 데이터 레포지터리
│   ├── data/                # CSV fallback 데이터
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/           # 홈, 메타분석, 직업분석, 패치노트
│       ├── components/      # 공통 컴포넌트 + 차트
│       ├── hooks/           # useApi, useVersion
│       └── types/           # TypeScript 타입 정의
├── render.yaml              # Render 배포 설정
└── .env.example
```

## 로컬 개발 환경 설정

### 사전 요구사항
- Python 3.8+
- Node.js 20+
- PostgreSQL (또는 CSV fallback으로 DB 없이도 동작)

### 백엔드 실행

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env
# .env에 DB 정보 입력

uvicorn main:app --reload --port 8000
```

### 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173 (백엔드 proxy 자동 설정)
```

## Render 배포

### 설정값

| 항목 | 값 |
|---|---|
| Build Command | `pip install -r backend/requirements.txt && cd frontend && npm install && npm run build` |
| Start Command | `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT` |

### 환경변수

| 변수 | 설명 |
|---|---|
| `PGHOST` | PostgreSQL 호스트 |
| `PGDATABASE` | 데이터베이스 이름 |
| `PGUSER` | 사용자 |
| `PGPASSWORD` | 비밀번호 |
| `PGSCHEMA` | 스키마 (기본값: `dm`) |
| `SELF_PING_URL` | 배포 후 서비스 URL + `/api/health` (sleep 방지용) |

> **Render Hobby sleep 방지**: `SELF_PING_URL` 설정 시 14분마다 자동 self-ping하여 서버가 sleep되지 않습니다. 콜드 스타트 발생 시 프론트엔드에 안내 오버레이가 표시됩니다.

## API 엔드포인트

```
GET /api/health
GET /api/home/notices
GET /api/home/updates
GET /api/home/events
GET /api/home/cashshop
GET /api/version/list
GET /api/version/{version}
GET /api/version/{version}/patch-note
GET /api/meta?type=전체&version=
GET /api/job/types
GET /api/job/list?type=전체&keyword=
GET /api/job/ranking?type=전체&version=
GET /api/job/{job}
GET /api/job/{job}/stats?segment=전체&version=
```
