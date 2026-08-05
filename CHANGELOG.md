# Changelog

이 프로젝트의 주요 변경 사항을 기록합니다.
형식은 [Keep a Changelog](https://keepachangelog.com/)를, 버전은 [SemVer](https://semver.org/)를 따릅니다.

## [0.1.0] - 2026-08-05

첫 릴리스 — Stage 1 (Crawl & Notify) 완성.

### Added
- 수집기: arXiv, HuggingFace Daily Papers, 범용 RSS (OpenAI·Google·MIT Tech Review·The Decoder 등)
- SQLite 기반 중복 제거 (arXiv 버전 접미사 정규화 포함)
- 키워드 필터(include/exclude) + 소스별 상한 + HuggingFace upvotes 정렬
- AI 주제 카탈로그 분류: LLM 기반(정확) / 키워드 규칙(무료 폴백)
- 한국어 한 줄 요약(LLM) / 초록 발췌(무료 폴백)
- 알림 채널: Slack(전문), 카카오톡(다이제스트+링크), 이메일(SMTP)
- 리포트 아카이브: `reports/YYYY-MM-DD.md` + 인덱스 자동 생성·커밋
- GitHub Actions 매일 자동 실행(KST 07:00) + 수동 실행
- 모든 소스 실패 시 헬스체크 경고

[0.1.0]: https://github.com/LumenSemantics/on-demand-rag/releases/tag/v0.1.0
