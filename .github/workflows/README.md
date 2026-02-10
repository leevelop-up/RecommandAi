# GitHub Actions 자동 배포 설정

## 필수 Secrets 설정

GitHub Repository → Settings → Secrets and variables → Actions에서 다음 secrets를 추가하세요:

### 1. NAS_HOST
NAS 서버 주소
```
leevelop.com
```

### 2. NAS_USER
NAS SSH 사용자명
```
your-username
```

### 3. NAS_SSH_KEY
NAS SSH 개인키 (Private Key)

```bash
# 로컬에서 SSH 키 생성 (이미 있으면 생략)
ssh-keygen -t ed25519 -C "github-actions"

# 공개키를 NAS 서버에 등록
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@leevelop.com

# 개인키 내용을 복사해서 GitHub Secrets에 등록
cat ~/.ssh/id_ed25519
```

### 4. NAS_PORT
NAS SSH 포트 (기본값: 22)
```
22
```

### 5. NAS_DEPLOY_PATH
NAS 서버의 프로젝트 배포 경로
```
/home/user/projects
```

## 자동 배포 흐름

```
Git Push (main) 
    ↓
GitHub Actions 트리거
    ↓
NAS 서버 SSH 접속
    ↓
Git Pull
    ↓
Docker 이미지 빌드
    ↓
컨테이너 재시작
    ↓
헬스체크
    ↓
배포 완료 ✅
```

## 수동 트리거

Actions 탭에서 "Run workflow" 버튼을 클릭하면 수동으로도 배포할 수 있습니다.

## 배포 로그 확인

1. GitHub Repository → Actions 탭
2. 최근 워크플로우 실행 클릭
3. "Deploy to NAS Server" job 확인
