# mini_backend — 팀 설정

## GitHub Actions Secrets

| Secret | 설명 |
|--------|------|
| `DOCKERHUB_USERNAME` | Docker Hub 사용자명 |
| `DOCKERHUB_TOKEN` | Docker Hub 토큰 |
| `EC2_HOST` | EC2 퍼블릭 IP |
| `EC2_USERNAME` | `ubuntu` |
| `EC2_SSH_KEY` | `.pem` 전체 내용 |
| `DATABASE_URL` | Neon `postgresql://...?sslmode=require` |
| `GEMINI_API_KEY` | Google AI Studio 키 (**로컬 모델 없음**) |
| `CORS_ORIGINS` | 예: `["https://your-mini.vercel.app","http://localhost:3111"]` |

## EC2

- 컨테이너: `mini-cleaning-api`, 포트 **8080**
- 헬스: `curl http://127.0.0.1:8080/health`
- vding-api와 **같은 EC2**를 쓰면 8080 충돌 — 별도 인스턴스 또는 다른 호스트 포트 권장

## Vercel (mini_frontend)

- `API_URL=http://<mini-api-host>:8080` (끝에 `/api/v1` 넣어도 normalize 됨)
