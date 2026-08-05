# 기여 가이드 (Contributing)

ARIP에 관심 가져주셔서 감사합니다. 작은 수정도 환영합니다.

## 개발 환경

```bash
git clone https://github.com/LumenSemantics/on-demand-rag.git
cd on-demand-rag
uv sync --extra dev        # 의존성 설치
cp .env.example .env       # 필요한 값 채우기 (없어도 무료 모드로 동작)
```

## 실행 · 검증

```bash
uv run arip --dry-run      # 발송 없이 콘솔에서 결과 확인
uv run pytest -q           # 테스트
uv run ruff check .        # 린트
```

PR를 올리기 전에 `pytest`와 `ruff check`가 모두 통과하는지 확인해 주세요. (CI가 자동으로 검사합니다.)

## 브랜치 · 커밋 · PR

1. `main`에서 브랜치를 파세요: `feat/…`, `fix/…`, `docs/…`
2. 커밋 메시지는 무엇을·왜 바꿨는지 한 줄 요약 + 필요 시 본문
3. PR 템플릿을 채우고, 관련 이슈를 링크해 주세요

## 기여하기 좋은 영역

- **새 소스 추가**: `config/sources.yaml`에 RSS 한 줄, 또는 `arip/collectors/`에 수집기
- **카탈로그 카테고리**: `arip/catalog.py`의 규칙/카테고리 개선
- **알림 채널**: `arip/notify/`에 새 채널(Discord, Telegram 등)
- **문서 · 번역**

## 코딩 규칙

- Python 3.11+, 타입 힌트 권장
- 새 기능에는 가능한 한 테스트 추가 (`tests/`)
- 비밀값(키·토큰)은 절대 커밋하지 마세요 — `.env`는 `.gitignore`에 있습니다

행동 규범은 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)를 따릅니다.
