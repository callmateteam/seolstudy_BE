#!/bin/bash
# EC2 초기 설정 스크립트
# 실행: bash deploy/setup-ec2.sh

set -e

echo "=== SeolStudy EC2 Setup ==="

# 시스템 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# Python 3.12 설치
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt install -y python3.12 python3.12-venv python3.12-dev

# Node.js 설치 (Prisma용)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Git 설치
sudo apt install -y git

# 앱 디렉토리로 이동
cd /home/ubuntu/seolstudy

# 가상환경 생성
python3.12 -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt

# Prisma Node 설정
mkdir -p /tmp/prisma-node/bin
ln -sf $(which node) /tmp/prisma-node/bin/node

# Prisma 클라이언트 생성
export PATH=".venv/bin:/tmp/prisma-node/bin:$PATH"
PRISMA_USE_GLOBAL_NODE=1 prisma generate
PRISMA_USE_GLOBAL_NODE=1 prisma db push --accept-data-loss

# systemd 서비스 설정
sudo cp deploy/seolstudy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable seolstudy
sudo systemctl start seolstudy

echo "=== Setup Complete ==="
echo "서비스 상태: sudo systemctl status seolstudy"
echo "로그 확인: sudo journalctl -u seolstudy -f"
