#!/usr/bin/env bash
# EC2 호스트에서 1회 실행 (배포 워크플로가 mkdir 하므로 보통 불필요)
set -euo pipefail

UPLOAD_HOST="${UPLOAD_HOST:-/var/lib/mini-cleaning/uploads}"

sudo mkdir -p "$UPLOAD_HOST"
sudo chmod 775 "$UPLOAD_HOST"
echo "OK: $UPLOAD_HOST (마운트 대상: 컨테이너 /app/uploads)"
ls -la "$UPLOAD_HOST"
