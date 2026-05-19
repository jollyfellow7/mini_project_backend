# mini_backend — 설정 가이드

청소 API(FastAPI) · Gemini · Neon · EC2 Docker 배포.

---

## 1. 어디에 무엇을 넣나요?

| 환경 | 설정 위치 |
|------|-----------|
| **로컬 PC** | `mini_backend/.env` (`.env.example` 복사) |
| **EC2** | 파일 없음 → GitHub Actions가 `docker run -e` 로 주입 |
| **Vercel** | 백엔드 env **넣지 않음** (프론트는 `API_URL`만) |

---

## 2. 로컬 실행 (conda)

```powershell
cd mini_backend
copy .env.example .env
# .env 편집: GEMINI_API_KEY, NEON_DB_*, JWT_SECRET

conda create -n mini-backend python=3.11 -y
conda activate mini-backend
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 37651
```

- Health: http://127.0.0.1:37651/health  
- 포트 표: `../LOCAL_TEST_PORTS.md`  
- `python -m venv .venv` 는 사용하지 않습니다.

---

## 3. GitHub Actions Secrets

`jiminsss02/mini_project_backend` → **Settings → Secrets and variables → Actions**

| Secret | 필수 | 설명 |
|--------|:----:|------|
| `DOCKERHUB_USERNAME` | ○ | `jiminsong02` |
| `DOCKERHUB_TOKEN` | ○ | Docker Hub Access Token |
| `EC2_HOST` | ○ | `43.201.95.108` |
| `EC2_USERNAME` | ○ | `ubuntu` |
| `EC2_SSH_KEY` | ○ | `mini_project.pem` **전체** 내용 |
| `NEON_DB_URL` | ○ | `jdbc:postgresql://...` |
| `NEON_DB_USERNAME` | ○ | Neon 사용자 |
| `NEON_DB_PASSWORD` | ○ | Neon 비밀번호 |
| `GEMINI_API_KEY` | ○ | Google AI Studio |
| `JWT_SECRET` | △ | 있으면 컨테이너에 주입 (청소 API는 현재 미사용) |
| `CORS_ORIGINS` | △ | 예: `["https://mini3.cloud"]` — BFF만 쓰면 생략 가능 |

Docker Hub 이미지: **`jiminsong02/mini_project`**

`main` push 시 빌드 → Hub push → EC2 SSH 배포 → `curl :8080/health`

---

## 4. EC2 확인

```bash
docker ps
docker logs -f mini-cleaning-api
curl http://127.0.0.1:8080/health
```

Gemini 호출 테스트: 프론트에서 스캔 후 로그에 `POST /api/v1/cleaning/scan` 및 응답 JSON의 `model_id` 확인.

---

## 5. 트러블슈팅

| 증상 | 조치 |
|------|------|
| GHA `NEON_DB_*` / `GEMINI_API_KEY` 오류 | Secret 이름·repo(`mini_project_backend`) 확인 |
| GHA SSH 실패 | `EC2_SSH_KEY` pem 전문, `EC2_HOST` IP |
| `docker pull` 실패 | Hub에 `jiminsong02/mini_project` 존재·public 여부 |
| health 실패 | `docker logs mini-cleaning-api` — DB URL·Gemini 키 |
| 밖에서 8080 안 됨 | AWS 보안 그룹 TCP **8080** 인바운드 |

규칙 전체: `../CODE_RULES.md`

---

## 6. 프론트 연동

Vercel `API_URL` = `http://43.201.95.108:8080` → `mini_frontend/TEAM_SETUP.md`
