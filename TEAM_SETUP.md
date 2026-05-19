# mini_backend — 팀 설정



## GitHub Actions Secrets



| Secret | 필수 | 설명 |

|--------|------|------|

| `DOCKERHUB_USERNAME` | ○ | `jiminsong02` |

| `DOCKERHUB_TOKEN` | ○ | Docker Hub Access Token |

| `EC2_HOST` | ○ | `43.201.95.108` |

| `EC2_USERNAME` | ○ | `ubuntu` |

| `EC2_SSH_KEY` | ○ | `mini_project.pem` 전체 |

| `NEON_DB_URL` | ○ | `jdbc:postgresql://...` |

| `NEON_DB_USERNAME` | ○ | Neon DB 사용자 |

| `NEON_DB_PASSWORD` | ○ | Neon DB 비밀번호 |

| `JWT_SECRET` | △ | 있으면 주입 (mini 청소 API는 현재 미사용) |

| `GEMINI_API_KEY` | ○ | Google AI Studio |

| `CORS_ORIGINS` | △ | Vercel URL 확정 후 (없으면 localhost 기본값) |



Docker Hub: **`jiminsong02/mini_project`**



## Vercel (mini_frontend)



| 변수 | 값 |

|------|-----|

| `API_URL` | `http://43.201.95.108:8080` |



`DATABASE_URL` / `NEON_*` / `JWT_SECRET` / `GEMINI_API_KEY` → **Vercel에 넣지 않음**

