#!/bin/bash
# Render Hobby 배포용 시작 스크립트
set -e

cd "$(dirname "$0")"

# 포트 설정 (Render는 $PORT 환경변수 제공)
PORT="${PORT:-10000}"

echo "=== Maple Meta Dashboard 시작 ==="
echo "PORT: $PORT"

# 백엔드 실행
cd backend
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"
