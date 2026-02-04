# Synology NAS Docker 배포 가이드 - RecommandAi

## 프로젝트 개요

RecommandAi는 Python 기반의 주식 데이터 수집 및 AI 추천 시스템입니다.

- 한국/미국 주식 데이터 실시간 수집
- AI 기반 주식 추천 (Gemini API)
- 급등 예측 시스템
- 스케줄러를 통한 자동 실행

## 사전 준비

### 필수 API 키

다음 API 키들을 준비하세요:

- `GEMINI_API_KEY`: Google Gemini API 키
- `NAVER_CLIENT_ID`: 네이버 뉴스 API ID
- `NAVER_CLIENT_SECRET`: 네이버 뉴스 API Secret
- `OPENAI_API_KEY`: OpenAI API 키 (선택)

### 환경 변수 파일 생성

프로젝트 루트에 `.env` 파일 생성:

```env
# API Keys
GEMINI_API_KEY=your_gemini_api_key_here
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
OPENAI_API_KEY=your_openai_api_key

# Database
MARIADB_PASSWORD=strong_password_here
MARIADB_HOST=mariadb
MARIADB_PORT=3306
MARIADB_DATABASE=recommand_stock
MARIADB_USER=root

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
```

## 시놀로지 NAS 배포

### 방법 1: Docker Compose (권장)

1. **프로젝트를 NAS로 복사**

   ```
   /volume1/docker/RecommandAi/
   ```

2. **SSH로 NAS 접속**

   ```bash
   ssh admin@your-nas-ip
   cd /volume1/docker/RecommandAi
   ```

3. **환경 변수 파일 생성**

   ```bash
   nano .env
   # 위의 환경 변수 내용 입력
   ```

4. **Docker Compose로 실행**

   ```bash
   sudo docker-compose up -d --build
   ```

5. **로그 확인**
   ```bash
   sudo docker logs -f recommandai
   ```

### 방법 2: 개별 컨테이너 실행

1. **이미지 빌드**

   ```bash
   sudo docker build -t recommandai:latest .
   ```

2. **네트워크 생성**

   ```bash
   sudo docker network create recommand-network
   ```

3. **MariaDB 실행**

   ```bash
   sudo docker run -d \
     --name recommandai-mariadb \
     --network recommand-network \
     -e MYSQL_ROOT_PASSWORD=your_password \
     -e MYSQL_DATABASE=recommand_stock \
     -v /volume1/docker/RecommandAi/mariadb-data:/var/lib/mysql \
     -p 3306:3306 \
     mariadb:11
   ```

4. **Redis 실행**

   ```bash
   sudo docker run -d \
     --name recommandai-redis \
     --network recommand-network \
     -v /volume1/docker/RecommandAi/redis-data:/data \
     -p 6379:6379 \
     redis:7-alpine redis-server --appendonly yes
   ```

5. **RecommandAi 실행**
   ```bash
   sudo docker run -d \
     --name recommandai \
     --network recommand-network \
     --env-file .env \
     -v /volume1/docker/RecommandAi/logs:/app/logs \
     -v /volume1/docker/RecommandAi/data:/app/data \
     -v /volume1/docker/RecommandAi/output:/app/output \
     recommandai:latest
   ```

## 수동 실행 방법

스케줄러 대신 수동으로 특정 작업 실행:

### 금주 추천 실행

```bash
sudo docker exec recommandai python run_weekly_recommendation.py
```

### 뉴스 수집

```bash
sudo docker exec recommandai python collect_comprehensive_news.py
```

## 유용한 명령어

### 컨테이너 상태 확인

```bash
sudo docker ps
sudo docker-compose ps
```

### 로그 확인

```bash
# 전체 로그
sudo docker logs recommandai

# 실시간 로그
sudo docker logs -f recommandai

# 최근 100줄
sudo docker logs --tail 100 recommandai
```

### 컨테이너 내부 접속

```bash
sudo docker exec -it recommandai /bin/bash
```

### 데이터베이스 접속

```bash
sudo docker exec -it recommandai-mariadb mysql -u root -p
```

### Redis 접속

```bash
sudo docker exec -it recommandai-redis redis-cli
```

### 컨테이너 재시작

```bash
sudo docker restart recommandai
sudo docker-compose restart
```

### 컨테이너 중지

```bash
sudo docker stop recommandai recommandai-mariadb recommandai-redis
sudo docker-compose down
```

### 전체 재빌드

```bash
sudo docker-compose down
sudo docker-compose up -d --build
```

## 데이터 백업

### MariaDB 백업

```bash
sudo docker exec recommandai-mariadb \
  mysqldump -u root -p recommand_stock > backup_$(date +%Y%m%d).sql
```

### Redis 백업

```bash
sudo docker exec recommandai-redis redis-cli SAVE
sudo docker cp recommandai-redis:/data/dump.rdb ./backup_redis_$(date +%Y%m%d).rdb
```

## 스케줄 설정

`scheduler.py`에서 실행 스케줄을 설정할 수 있습니다:

- 데이터 수집: 평일 09:00-15:30 (매 30분)
- AI 추천: 매일 16:00
- 뉴스 수집: 매 1시간

## 트러블슈팅

### API 키 오류

- `.env` 파일의 API 키 확인
- 컨테이너 재시작: `sudo docker restart recommandai`

### 데이터베이스 연결 실패

- MariaDB 컨테이너 상태 확인: `sudo docker ps`
- 네트워크 확인: `sudo docker network inspect recommand-network`

### 외부에서 Redis/MariaDB 접속 불가

외부 클라이언트(DataGrip, Redis Desktop Manager 등)에서 접속이 안 되는 경우:

1. **NAS 방화벽 설정 확인**
   - 제어판 > 보안 > 방화벽
   - 사용하는 포트 허용 (Redis: 6380, MariaDB: 2906)

2. **Docker 포트 매핑 확인**
   ```bash
   sudo docker port recommandai-redis
   sudo docker port recommandai-mariadb
   ```

3. **컨테이너 내부에서 접속 테스트**
   ```bash
   # Redis 테스트
   sudo docker exec recommandai-redis redis-cli -a 'your_password' ping

   # MariaDB 테스트
   sudo docker exec recommandai-mariadb mysql -u root -p -e "SELECT 1"
   ```

4. **외부에서 포트 테스트**
   ```bash
   # Redis 연결 테스트
   redis-cli -h your-nas-ip -p 6380 -a 'your_password' ping

   # 포트 열림 확인
   nc -zv your-nas-ip 6380
   ```

### 메모리 부족

- Docker 메모리 제한 늘리기
- `docker-compose.yml`에 리소스 제한 추가:
  ```yaml
  deploy:
    resources:
      limits:
        memory: 2G
  ```

### Playwright 오류

- Chromium 수동 설치:
  ```bash
  sudo docker exec recommandai playwright install chromium --with-deps
  ```

## 모니터링

### 리소스 사용량

```bash
sudo docker stats recommandai
```

### 출력 파일 확인

```bash
ls -lh /volume1/docker/RecommandAi/output/
```

### 로그 파일

```bash
tail -f /volume1/docker/RecommandAi/logs/app.log
```
