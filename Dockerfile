# AIRP GraphRAG 웹 UI — Google Cloud Run 용 컨테이너
# 빌드: docker build -t airp-api .
# 로컬 실행: docker run -p 8080:8080 --env-file .env airp-api
FROM python:3.11-slim

# 파이썬 런타임 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    PORT=8080

WORKDIR /app

# 의존성 먼저 복사(레이어 캐시). api extra만 설치하면 웹 UI 구동에 충분.
COPY pyproject.toml README.md ./
COPY airp ./airp
RUN pip install --upgrade pip && pip install ".[api]"

# Cloud Run은 PORT 환경변수를 주입한다. HOST=0.0.0.0 로 모든 인터페이스 바인딩.
EXPOSE 8080
CMD ["airp-api"]
