# SeolStudy 배포 가이드

## GitHub Secrets 설정

GitHub 레포지토리 Settings → Secrets and variables → Actions에서 아래 시크릿을 추가하세요:

| Secret Name | 설명 | 예시 |
|-------------|------|------|
| `EC2_HOST` | EC2 인스턴스 퍼블릭 IP 또는 도메인 | `13.124.xxx.xxx` |
| `EC2_USER` | SSH 접속 사용자 | `ubuntu` |
| `EC2_SSH_KEY` | EC2 프라이빗 키 (.pem 파일 전체 내용) | `-----BEGIN RSA PRIVATE KEY-----...` |
| `EC2_APP_PATH` | 앱 설치 경로 | `/home/ubuntu/seolstudy` |

## EC2 초기 설정

1. EC2 인스턴스 생성 (Ubuntu 22.04 LTS 권장)

2. 보안 그룹 인바운드 규칙:
   - SSH (22): 내 IP
   - HTTP (80): 0.0.0.0/0
   - Custom TCP (8000): 0.0.0.0/0

3. EC2에 SSH 접속 후 프로젝트 클론:
   ```bash
   cd /home/ubuntu
   git clone https://github.com/YOUR_USERNAME/seolstudy.git
   cd seolstudy
   ```

4. `.env` 파일 생성:
   ```bash
   cat > .env << 'EOF'
   DATABASE_URL=postgresql://user:password@your-rds-endpoint:5432/seolstudy
   JWT_SECRET_KEY=your-super-secret-key
   AWS_ACCESS_KEY_ID=your-aws-key
   AWS_SECRET_ACCESS_KEY=your-aws-secret
   AWS_REGION=ap-northeast-2
   S3_BUCKET_NAME=seolstudy-uploads
   EOF
   ```

5. 초기 설정 스크립트 실행:
   ```bash
   bash deploy/setup-ec2.sh
   ```

## CI/CD 플로우

```
main 브랜치 푸시
       ↓
   테스트 실행 (PostgreSQL 컨테이너)
       ↓
   테스트 성공 시 EC2 배포
       ↓
   git pull → pip install → prisma generate → systemctl restart
```

## 유용한 명령어

```bash
# 서비스 상태 확인
sudo systemctl status seolstudy

# 로그 실시간 확인
sudo journalctl -u seolstudy -f

# 서비스 재시작
sudo systemctl restart seolstudy

# 서비스 중지
sudo systemctl stop seolstudy
```

## Nginx 리버스 프록시 (선택)

HTTPS 및 도메인 설정 시:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx

# /etc/nginx/sites-available/seolstudy
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# 활성화
sudo ln -s /etc/nginx/sites-available/seolstudy /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# SSL 인증서 (Let's Encrypt)
sudo certbot --nginx -d your-domain.com
```
