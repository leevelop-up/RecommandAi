#!/bin/bash

# RecommandStock API 서버 시작 스크립트

echo "=================================="
echo "  RecommandStock API 서버 시작"
echo "=================================="

# FastAPI 의존성 확인 및 설치
if ! python -c "import fastapi" 2>/dev/null; then
    echo "FastAPI 설치 중..."
    pip install -r requirements_api.txt
fi

# API 서버 시작
echo ""
echo "API 서버 시작: http://localhost:8000"
echo "API 문서: http://localhost:8000/docs"
echo ""
echo "종료하려면 Ctrl+C를 누르세요"
echo ""

python api/main.py
