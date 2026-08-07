#!/usr/bin/env bash
# AIRP GraphRAG 웹 UI → Google Cloud Run 배포 스크립트
#
# 사전조건:
#   1) gcloud CLI 설치 및 로그인:  gcloud auth login
#   2) 프로젝트/결제 설정:         gcloud config set project <PROJECT_ID>
#   3) 이 저장소 루트에 .env 존재 (QDRANT_*, NEO4J_*, LLM_* 값)
#
# 사용법:  bash deploy/cloudrun.sh
set -euo pipefail

REGION="${REGION:-asia-northeast3}"   # 서울 리전
SERVICE="${SERVICE:-airp-api}"

# .env 로드 (시크릿 값은 화면에 출력하지 않음)
set -a; [ -f .env ] && . ./.env; set +a

need() { [ -n "${!1:-}" ] || { echo "환경변수 $1 가 비어있음(.env 확인)"; exit 1; }; }
need QDRANT_URL; need QDRANT_API_KEY
need NEO4J_URI;  need NEO4J_PASSWORD
need LLM_API_KEY

echo "== 1) 필요한 API 활성화 =="
gcloud services enable \
  run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com

echo "== 2) 시크릿 등록/업데이트 (값은 표준입력으로만 전달) =="
put_secret() {
  local name="$1" val="$2"
  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    printf '%s' "$val" | gcloud secrets versions add "$name" --data-file=-
  else
    printf '%s' "$val" | gcloud secrets create "$name" --data-file=-
  fi
}
put_secret airp-llm-api-key    "$LLM_API_KEY"
put_secret airp-qdrant-api-key "$QDRANT_API_KEY"
put_secret airp-neo4j-password "$NEO4J_PASSWORD"

echo "== 3) Cloud Run 배포 (Dockerfile 자동 빌드) =="
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --cpu 1 --memory 512Mi --timeout 120 --min-instances 0 \
  --set-env-vars "LLM_PROVIDER=${LLM_PROVIDER:-gemini},LLM_MODEL=${LLM_MODEL:-gemini-flash-lite-latest},EMBED_PROVIDER=${EMBED_PROVIDER:-gemini},EMBED_MODEL=${EMBED_MODEL:-gemini-embedding-001},QDRANT_URL=${QDRANT_URL},NEO4J_URI=${NEO4J_URI},NEO4J_USER=${NEO4J_USER:-neo4j}" \
  --set-secrets "LLM_API_KEY=airp-llm-api-key:latest,QDRANT_API_KEY=airp-qdrant-api-key:latest,NEO4J_PASSWORD=airp-neo4j-password:latest"

echo "== 완료 =="
gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)'
