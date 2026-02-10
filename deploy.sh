#!/bin/bash
# NAS 배포 스크립트

set -e

echo "🚀 RecommandAi 배포 시작..."

# 1. Git pull
echo "📥 최신 코드 가져오기..."
git pull origin main

# 2. Docker 이미지 빌드
echo "🔨 Docker 이미지 빌드..."
docker-compose build

# 3. 기존 컨테이너 중지 및 제거
echo "🛑 기존 컨테이너 중지..."
docker-compose down

# 4. 새 컨테이너 시작
echo "▶️  새 컨테이너 시작..."
docker-compose up -d

# 5. 헬스체크
echo "🏥 헬스체크..."
sleep 5
curl -f http://localhost:8000/health || exit 1

echo "✅ 배포 완료!"
docker-compose ps
