# Maple Meta Dashboard

메이플스토리 메타 분석 대시보드 웹 애플리케이션

## 주요 기능

- **홈** - 공지사항, 업데이트, 진행중인 이벤트, 캐시샵 공지 캐러셀
- **메타분석** - 밸런스 점수 KPI, 직업별 층수 분포(Violin), TER 분포, 50층 달성률 순위 추이(Bump Chart)
- **직업분석** - 직업 선택 그리드 + 랭킹 테이블, 직업별 레이다 차트, 스탯/아이템 히스토그램
- **패치노트** - 버전별 패치노트 마크다운 뷰어

## 기술 스택

| 영역 | 기술 |
|---|---|
| 백엔드 | FastAPI, SQLAlchemy, PostgreSQL |
| 프론트엔드 | React 18, TypeScript, Vite, Tailwind CSS |
| 차트 | Apache ECharts |
| 데이터베이스 | Supabase (PostgreSQL) |
| 배포 | fly.io |

## 프로젝트 구조

```
maplemeta_web/
├── backend/
│   ├── main.py              # FastAPI 앱
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
├── Dockerfile               # fly.io 배포용
├── fly.toml                 # fly.io 설정
└── .env.example
```

## 로컬 개발 환경 설정

### 사전 요구사항

- Python 3.11+
- Node.js 20+

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

## fly.io 배포

### 초기 설정

```bash
fly auth login
fly secrets set PGHOST=<pooler-host> PGUSER=<user> PGPASSWORD=<password>
```

### 배포

```bash
fly deploy
```

### 환경변수

fly.toml의 `[env]` 섹션에 비민감 설정이 있으며, 민감 정보는 `fly secrets`로 관리합니다.

| 변수 | 관리 방식 | 설명 |
|---|---|---|
| `PGHOST` | fly secrets | Supabase Session Pooler 호스트 |
| `PGUSER` | fly secrets | Supabase 사용자 (project-ref 포함) |
| `PGPASSWORD` | fly secrets | DB 비밀번호 |
| `PGDATABASE` | fly.toml env | 데이터베이스 이름 |
| `PGPORT` | fly.toml env | 포트 (5432) |
| `PGSCHEMA` | fly.toml env | 스키마 (public) |

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
