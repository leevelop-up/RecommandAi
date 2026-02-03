#!/bin/bash
# NAS Docker RecommandAI 오류 확인 스크립트

echo "======================================"
echo "  NAS Docker RecommandAI 상태 확인"
echo "======================================"
echo ""

# NAS 서버 주소 입력 (사용자가 변경해야 함)
NAS_HOST="${NAS_HOST:-admin@192.168.0.100}"  # 기본값, 실제 NAS IP로 변경 필요

echo "NAS 서버: $NAS_HOST"
echo ""

# 1. Docker 컨테이너 상태 확인
echo "1. Docker 컨테이너 상태..."
ssh "$NAS_HOST" "sudo docker ps -a | grep -E 'recommand|mariadb|redis'"
echo ""

# 2. RecommandAI 로그 확인 (최근 50줄)
echo "2. RecommandAI 로그 (최근 50줄)..."
ssh "$NAS_HOST" "sudo docker logs --tail 50 recommandai 2>&1"
echo ""

# 3. Docker Compose 상태 확인
echo "3. Docker Compose 상태..."
ssh "$NAS_HOST" "cd /volume1/docker/RecommandAi && sudo docker-compose ps"
echo ""

# 4. 디스크 사용량 확인
echo "4. 디스크 사용량..."
ssh "$NAS_HOST" "df -h | grep volume1"
echo ""

# 5. 최근 에러 로그만 추출
echo "5. 최근 에러 메시지..."
ssh "$NAS_HOST" "sudo docker logs --tail 100 recommandai 2>&1 | grep -i error"
echo ""

echo "======================================"
echo "  상태 확인 완료"
echo "======================================"
