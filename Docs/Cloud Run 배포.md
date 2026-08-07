# Cloud Run 배포 가이드 (ARIP 웹 UI)

ARIP GraphRAG 웹 UI(`arip-api`)를 Google Cloud Run에 올리는 방법입니다.

## 왜 가능한가 (검증됨)

- 웹 서비스는 모든 설정을 **환경변수**(`os.getenv`)로 읽음 → Cloud Run이 주입/시크릿으로 공급 가능
- 데이터는 **Qdrant Cloud · Neo4j Aura · Gemini** 를 HTTP로 조회 → 컨테이너에 로컬 상태 불필요(**stateless**)
- `arip-api` 는 `PORT` 환경변수를 따라 `0.0.0.0:$PORT` 바인딩 → Cloud Run 포트 규약 충족 (로컬 검증 완료: `PORT=9091` → 9091 바인딩, `/healthz` → `{"status":"ok"}`)
- 크롤링·SQLite(`seen.db`)·Slack/이메일/카카오는 **웹 서비스와 분리** → 배포 대상 아님(그건 GitHub Actions에서 계속 수행)

## 필요한 것

| 항목 | 설명 |
|------|------|
| GCP 프로젝트 | 결제 활성화 필요 (Cloud Run은 사용량 기반, scale-to-zero라 유휴 시 0원 수준) |
| gcloud CLI | 로컬 설치 + `gcloud auth login` |
| .env | 저장소 루트에 `QDRANT_URL/QDRANT_API_KEY/NEO4J_URI/NEO4J_PASSWORD/LLM_API_KEY` 등 |

> Docker는 **필요 없음**. `gcloud run deploy --source .` 가 Cloud Build로 Dockerfile을 빌드함.

## 배포 (자동 스크립트)

```bash
gcloud auth login
gcloud config set project <PROJECT_ID>
bash deploy/cloudrun.sh
```

스크립트가 하는 일: 필요한 API 활성화 → 민감값 3종을 **Secret Manager**에 등록 → `gcloud run deploy` (env·secret 주입) → 서비스 URL 출력.

## 배포 (수동)

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com

printf '%s' "$LLM_API_KEY"    | gcloud secrets create arip-llm-api-key    --data-file=-
printf '%s' "$QDRANT_API_KEY" | gcloud secrets create arip-qdrant-api-key --data-file=-
printf '%s' "$NEO4J_PASSWORD" | gcloud secrets create arip-neo4j-password --data-file=-

gcloud run deploy arip-api \
  --source . \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --cpu 1 --memory 512Mi --timeout 120 --min-instances 0 \
  --set-env-vars "LLM_PROVIDER=gemini,LLM_MODEL=gemini-flash-lite-latest,EMBED_PROVIDER=gemini,EMBED_MODEL=gemini-embedding-001,QDRANT_URL=<...>,NEO4J_URI=<...>,NEO4J_USER=neo4j" \
  --set-secrets "LLM_API_KEY=arip-llm-api-key:latest,QDRANT_API_KEY=arip-qdrant-api-key:latest,NEO4J_PASSWORD=arip-neo4j-password:latest"
```

배포가 끝나면 `https://arip-api-xxxxx-du.a.run.app` 형태의 **공개 URL**이 출력됩니다.

## ⚠️ 접근 제어 (중요)

- `--allow-unauthenticated` 는 URL을 **전 세계 공개**로 만듭니다. 누구나 접속 시 Gemini/Qdrant/Neo4j를 호출(비용·데이터 노출).
- 개인용이면 다음 중 하나를 권장:
  - **비공개 유지**: `--no-allow-unauthenticated` 로 배포 → 접근 시 `gcloud run services proxy arip-api --region asia-northeast3` 로 로컬 프록시 터널
  - 공개하되 앞단에 인증(예: IAP, 간단한 토큰 검사) 추가

## 비용 개요

- `--min-instances 0`: 요청 없을 땐 인스턴스 0 → **유휴 비용 거의 없음**
- 요청당 CPU/메모리 사용분 + Cloud Build 빌드 시간 소량 과금
- 실제 LLM/임베딩 비용은 Gemini 쪽에서 발생(쿼리당 임베딩 1회 + ask 시 생성 호출)

## 헬스체크

- `GET /healthz` → `{"status":"ok"}` (외부 호출 없음, 프로브용)

## 크롤링 파이프라인은?

데일리 브리핑 수집·색인(`arip`, `arip-kb index`)은 **GitHub Actions 크론**에서 계속 돌리는 걸 권장합니다. 굳이 Cloud Run에서 주기 실행하려면 **Cloud Run Jobs + Cloud Scheduler** 로 분리 구성해야 합니다(웹 서비스와 별개).
