# mini_backend — 설정 가이드



청소 + chungsora API (FastAPI) · Gemini · Neon · JWT · EC2 Docker 배포.



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

# .env 편집: GEMINI_API_KEY, NEON_DB_*, JWT_SECRET (필수 — chungsora JWT)



conda create -n mini-backend python=3.11 -y

conda activate mini-backend

pip install -r requirements.txt

uvicorn main:app --host 127.0.0.1 --port 37651

```



- Health: http://127.0.0.1:37651/health  

- Ready (DB): http://127.0.0.1:37651/health/ready  

- 포트 표: `../LOCAL_TEST_PORTS.md`  

- `python -m venv .venv` 는 사용하지 않습니다.

- chungsora 부모 계정·비밀번호는 **Neon `parent_accounts`에만** 저장 (코드·env·JSON 시드 없음)
- 신규 계정: `POST /api/v1/auth/signup` · 로그인: `POST /api/v1/auth/login`



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

| `JWT_SECRET` | ○ | chungsora JWT 서명 (GHA·배포 **필수**) |

| `CORS_ORIGINS` | △ | 미설정 시 기본값에 `localhost`·`https://mini3.cloud` 포함 |



Docker Hub 이미지: **`jiminsong02/mini_project`**



`main` push 시 빌드 → Hub push → EC2 SSH 배포 → `curl :8080/health` · `:8080/health/ready`



---



## 4. EC2 확인



```bash

docker ps

docker inspect mini-cleaning-api --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'

docker logs -f mini-cleaning-api

curl http://127.0.0.1:8080/health

curl http://127.0.0.1:8080/health/ready

```



### 4-1. uploads 볼륨 (baseline·고스트 이미지 유지)



재배포해도 사진/영상이 사라지지 않도록 **호스트 디렉터리**를 컨테이너에 마운트합니다.



| 위치 | 경로 |

|------|------|

| EC2 호스트 | `/var/lib/mini-cleaning/uploads` |

| 컨테이너 | `/app/uploads` (`UPLOAD_DIR=/app/uploads`) |

| baseline·로그 파일 | `/app/uploads/logs/{parent_id}/{date}/...` |

| URL | `/uploads/logs/...` → FastAPI StaticFiles |



`main` push 배포 시 GHA가 `mkdir` + `docker run -v ...` 를 자동 적용합니다. 수동 1회 설정: `scripts/setup-ec2-uploads-volume.sh`



**주의:** 볼륨 적용 **이전**에 컨테이너 안에만 있던 파일은 복구되지 않습니다. 부모 baseline·자녀 촬영을 한 번 다시 올려야 할 수 있습니다.



`/health/ready` 응답에 `"uploads": "ok"` 가 포함되어야 쓰기 가능합니다. `not_writable` 이면 볼륨 마운트·권한을 확인하세요.



- cleaning: 프론트 스캔 후 `POST /api/v1/cleaning/scan` · `model_id: gemini-...`

- chungsora: `POST /api/v1/auth/login` `{ "login_id": "<Neon에 등록된 id>", "password": "<...>" }` → JWT (`onboard_done` 포함)

### 배포·검증 스크립트 (로컬 conda)

```powershell
python -m tools.smoke_neon_e2e --http http://43.201.95.108:8080
python -m tools.smoke_neon_e2e --keep --login-id smoke_dev
python -m tools.backfill_onboard_done
python -m tools.verify_production_deploy
```

리포트: 모노레포 루트 `SMOKE_VERIFICATION_REPORT.md`



---



## 5. DB · ERD



- Neon PostgreSQL — cleaning + chungsora 테이블 (사용자별 `parent_account_id` 격리)

- ERD HTML: `docs/neon-erd.html` (브라우저에서 열기)



---



## 6. 트러블슈팅



| 증상 | 조치 |

|------|------|

| GHA `NEON_DB_*` / `GEMINI_API_KEY` / `JWT_SECRET` 오류 | Secret 이름·repo(`mini_project_backend`) 확인 |

| GHA SSH 실패 | `EC2_SSH_KEY` pem 전문, `EC2_HOST` IP |

| `docker pull` 실패 | Hub에 `jiminsong02/mini_project` 존재·public 여부 |

| `/health/ready` 503 | `docker logs mini-cleaning-api` — DB URL·Neon 연결 |

| chungsora 401 | `JWT_SECRET` 일치, Authorization Bearer |

| 밖에서 8080 안 됨 | AWS 보안 그룹 TCP **8080** 인바운드 |

| baseline URL 404 · 고스트 안 보임 | `curl :8080/health/ready` → `uploads: ok` · EC2 `ls /var/lib/mini-cleaning/uploads/logs` · 부모 baseline 재촬영 |



규칙 전체: `CODE_RULES.md` (모노레포 루트) 또는 팀 공유 문서



---



## 7. 프론트 연동



Vercel `API_URL` = `http://43.201.95.108:8080` → `mini_frontend/TEAM_SETUP.md`

