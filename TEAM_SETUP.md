# mini_backend — 팀 설정

## 원칙

- **env는 GitHub Actions Secrets만** → 배포 시 `docker run -e`로 컨테이너에 주입
- **EC2에 `.env` 파일 만들지 않음**
- **프론트(Vercel)에는 `API_URL`만** — `GEMINI_API_KEY`, `DATABASE_URL` 넣지 않음

## GitHub Actions Secrets (mini_project_backend)

| Secret | 필수 | 설명 |
|--------|------|------|
| `DOCKERHUB_USERNAME` | ○ | `jiminsong02` |
| `DOCKERHUB_TOKEN` | ○ | Docker Hub Access Token |
| `EC2_HOST` | ○ | `43.201.95.108` |
| `EC2_USERNAME` | ○ | `ubuntu` |
| `EC2_SSH_KEY` | ○ | `mini_project.pem` 전체 |
| `DATABASE_URL` | ○ | Neon `postgresql://...?sslmode=require` |
| `GEMINI_API_KEY` | ○ | Google AI Studio |
| `CORS_ORIGINS` | △ | Vercel URL 확정 후. 예: `["https://xxx.vercel.app"]` — 없으면 앱 기본값(localhost) |

Docker Hub 이미지: **`jiminsong02/mini_project`** (`deploy.yml`과 동일)

## EC2

- Docker만 설치. 배포는 GHA가 수행
- 컨테이너: `mini-cleaning-api`, 포트 **8080**
- 확인: `curl http://127.0.0.1:8080/health`

## Vercel (mini_frontend)

| 변수 | 값 |
|------|-----|
| `API_URL` | `http://43.201.95.108:8080` |

끝에 `/api/v1` 붙여도 BFF에서 제거됩니다.
