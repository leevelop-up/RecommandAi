#!/bin/bash
# RecommandAi 서비스 시작 스크립트

echo "========================================"
echo "  RecommandAi 서비스 시작"
echo "========================================"

# 스케줄러 백그라운드 실행
echo "📅 스케줄러 시작..."
python scheduler.py --mode weekly &
SCHEDULER_PID=$!

# 잠시 대기 (스케줄러 초기화)
sleep 2

# 웹 서버 시작
echo "🌐 웹 대시보드 시작..."
python web_server.py &
WEB_PID=$!

echo ""
echo "✅ 모든 서비스 시작 완료"
echo "   - 스케줄러 PID: $SCHEDULER_PID"
echo "   - 웹 서버 PID: $WEB_PID"
echo "   - 웹 대시보드: http://localhost:8000"
echo ""
echo "Ctrl+C를 눌러 종료하세요"
echo "========================================"

# 시그널 처리 함수
cleanup() {
    echo ""
    echo "서비스 종료 중..."
    kill $SCHEDULER_PID 2>/dev/null
    kill $WEB_PID 2>/dev/null
    exit 0
}

# SIGINT, SIGTERM 처리
trap cleanup SIGINT SIGTERM

# 프로세스 대기
wait
