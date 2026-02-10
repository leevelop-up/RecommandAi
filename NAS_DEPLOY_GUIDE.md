# NAS 배포 가이드

## 시스템 구성

```
┌─────────────────────────────────────────────────┐
│              NAS Server (leevelop.com)          │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐      ┌──────────────┐        │
│  │ RecommandAi  │      │RecommandStock│        │
│  │   Backend    │◄────►│   Frontend   │        │
│  │   :8000      │      │    :3000     │        │
│  └──────────────┘      └──────────────┘        │
│         │                                       │
│         ▼                                       │
│  ┌──────────────┐                              │
│  │   MariaDB    │                              │
│  │   :2906      │                              │
│  └──────────────┘                              │
└─────────────────────────────────────────────────┘
```

## 배포 순서

### 1. NAS 서버 접속

```bash
ssh user@leevelop.com
```

### 2. RecommandAi (백엔드) 배포

```bash
# 프로젝트 디렉토리로 이동
cd /path/to/RecommandAi

# 최신 코드 가져오기
git pull origin main

# .env 파일 확인 (이미 설정되어 있어야 함)
cat .env

# Docker Compose로 배포
./deploy.sh
```

**배포 완료 확인:**
```bash
# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f api

# 헬스체크
curl http://localhost:8000/health
```

### 3. RecommandStock (프론트엔드) 배포

```bash
# 프로젝트 디렉토리로 이동
cd /path/to/RecommandStock

# 최신 코드 가져오기
git pull origin main

# Docker Compose로 배포
./deploy.sh
```

**배포 완료 확인:**
```bash
# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f frontend
```

## 포트 설정

| 서비스 | 포트 | 설명 |
|--------|------|------|
| Backend API | 8000 | FastAPI 서버 |
| Frontend | 3000 | React 웹 앱 |
| MariaDB | 2906 | 데이터베이스 (기존) |
| Redis | 6379 | 캐시 (triplog-1 컨테이너 사용) |

## 접속 URL

- **백엔드 API**: http://leevelop.com:8000
- **API 문서**: http://leevelop.com:8000/docs
- **프론트엔드**: http://leevelop.com:3000

## 환경 변수

### RecommandAi (.env)
```bash
# MariaDB 설정
MARIADB_HOST=leevelop.com
MARIADB_PORT=2906
MARIADB_USER=merong2969
MARIADB_PASSWORD=Seung0075!
MARIADB_DATABASE=recommandstock

# Redis 설정
REDIS_HOST=172.20.0.1
REDIS_PORT=6379

# AI API Keys
GEMINI_API_KEY=your-key
GROQ_API_KEY=your-key
XAI_API_KEY=your-key
AI_ENGINE=groq
```

### RecommandStock (.env)
```bash
VITE_API_URL=http://leevelop.com:8000/api
```

## 데이터 수집 스케줄

스케줄러 컨테이너가 자동으로 다음 작업을 수행합니다:

- **매일 오후 6시**: 테마 & 종목 데이터 수집
- **매일 오후 6시 30분**: 뉴스 데이터 수집
- **매일 오후 7시**: 데이터베이스 업데이트

## 트러블슈팅

### API 연결 안 됨
```bash
# 백엔드 로그 확인
docker-compose -f /path/to/RecommandAi/docker-compose.yml logs api

# 포트 확인
netstat -tulpn | grep 8000
```

### 프론트엔드 빌드 실패
```bash
# 빌드 로그 확인
docker-compose -f /path/to/RecommandStock/docker-compose.yml logs frontend

# 수동 빌드
cd /path/to/RecommandStock
docker-compose build --no-cache
```

### 데이터베이스 연결 안 됨
```bash
# DB 연결 테스트
mysql -h leevelop.com -P 2906 -u merong2969 -p recommandstock

# 테이블 확인
SHOW TABLES;
SELECT COUNT(*) FROM themes;
```

## 유지보수

### 로그 확인
```bash
# 백엔드 로그
docker-compose -f /path/to/RecommandAi/docker-compose.yml logs -f --tail=100

# 프론트엔드 로그
docker-compose -f /path/to/RecommandStock/docker-compose.yml logs -f --tail=100
```

### 컨테이너 재시작
```bash
# 백엔드
cd /path/to/RecommandAi
docker-compose restart

# 프론트엔드
cd /path/to/RecommandStock
docker-compose restart
```

### 데이터 수동 수집
```bash
# 스케줄러 컨테이너 내부에서 실행
docker exec -it recommandai-scheduler python scrapers/run_scrapers.py
docker exec -it recommandai-scheduler python database/insert_data.py --clear
```

## 백업

### 데이터베이스 백업
```bash
mysqldump -h leevelop.com -P 2906 -u merong2969 -p recommandstock > backup_$(date +%Y%m%d).sql
```

### 복원
```bash
mysql -h leevelop.com -P 2906 -u merong2969 -p recommandstock < backup_20260210.sql
```
