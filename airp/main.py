from __future__ import annotations

import argparse
import sys

from . import archive, catalog, curate, translate
from .collectors import arxiv, huggingface, rss
from .collectors.base import Item
from .config import Config, load_config
from .notify import email as email_notify
from .notify import slack  # kakao 발송 비활성화(주석 처리)
from .report.builder import build_report  # build_digest는 kakao 발송 비활성화로 미사용
from .store.dedup import SeenStore
from .summarize import llm
from .util import is_korean, parallel_map


def collect_all(cfg: Config) -> tuple[list[Item], list[str]]:
    """설정된 모든 소스를 수집한다. 한 소스가 실패해도 나머지는 진행.

    반환: (수집 항목, 실패한 소스 이름 목록)
    """
    items: list[Item] = []
    failed: list[str] = []
    src = cfg.sources or {}

    ax = src.get("arxiv") or {}
    if ax:
        try:
            got = arxiv.collect(ax.get("categories", ["cs.AI"]), ax.get("max_results", 30))
            print(f"[arxiv] {len(got)}건")
            items += got
        except Exception as e:  # noqa: BLE001
            print(f"[arxiv] 실패: {e}", file=sys.stderr)
            failed.append("arxiv")

    hf = src.get("huggingface") or {}
    if hf.get("daily_papers"):
        try:
            got = huggingface.collect(hf.get("limit", 30))
            print(f"[huggingface] {len(got)}건")
            items += got
        except Exception as e:  # noqa: BLE001
            print(f"[huggingface] 실패: {e}", file=sys.stderr)
            failed.append("huggingface")

    for feed in src.get("rss", []) or []:
        name = feed.get("name", "?")
        try:
            got = rss.collect(name, feed["url"], feed.get("limit", 15))
            # 소스별 키워드 필터(선택): 전체기사 피드에서 특정 주제만 남길 때 사용.
            # feed에 include/exclude가 있으면 이 소스에만 적용(전역 filter와 별개).
            if feed.get("include") or feed.get("exclude"):
                kept = curate.keyword_filter(got, feed.get("include"), feed.get("exclude"))
                print(f"[rss:{name}] {len(got)}건 → 필터 후 {len(kept)}건")
                got = kept
            else:
                print(f"[rss:{name}] {len(got)}건")
            items += got
        except Exception as e:  # noqa: BLE001
            print(f"[rss:{name}] 실패: {e}", file=sys.stderr)
            failed.append(f"rss:{name}")

    return items, failed


def _force_utf8_stdout() -> None:
    """Windows 콘솔(cp949 등)에서 이모지·한글 출력이 깨지거나 죽지 않도록 UTF-8로 강제."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass


def _index_knowledge(cfg: Config, items: list[Item]) -> None:
    """신규 항목을 Qdrant(벡터)·Neo4j(그래프)에 색인. 설정된 것만 처리(지연 import)."""
    from .knowledge import embed as kb_embed
    from .knowledge import graph as kb_graph
    from .knowledge import store as kb_store

    if cfg.qdrant_url and cfg.llm_api_key:
        texts = [f"{it.title}\n{it.abstract}".strip() for it in items]
        vecs = kb_embed.embed_texts(texts, cfg.embed_provider, cfg.llm_api_key, cfg.embed_model)
        qc = kb_store.get_client(cfg.qdrant_url, cfg.qdrant_api_key)
        kb_store.ensure_collection(qc, len(vecs[0]))
        print(f"[knowledge] Qdrant 색인 {kb_store.index(qc, items, vecs)}건")
    if cfg.neo4j_uri:
        drv = kb_graph.get_driver(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
        kb_graph.ensure_constraints(drv)
        print(f"[knowledge] Neo4j 색인 {kb_graph.index(drv, items)}건")
        drv.close()


_TREND_SURGE = 3.0  # 급상승으로 볼 배율 임계치
_TREND_MIN = 3      # 급상승으로 볼 최소 최근 건수


def _insert_trends(cfg: Config, report: str) -> str:
    """색인된 그래프의 카테고리 급증을 리포트 첫 섹션 앞에 삽입(임계치 초과는 🚨)."""
    from .knowledge import graph as kb_graph
    from .knowledge import trends as kb_trends

    drv = kb_graph.get_driver(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
    try:
        docs = kb_trends.fetch_docs(drv)
    finally:
        drv.close()
    rows = kb_trends.category_trends(docs, days=7)
    if not rows:
        return report

    def fmt(s: float) -> str:
        return "∞" if s == float("inf") else f"{s:.1f}x"

    def hot(r: dict) -> bool:
        return r["surge"] >= _TREND_SURGE and r["recent"] >= _TREND_MIN

    surging = [r for r in rows if hot(r)]
    lines = ["## 📈 트렌드 (최근 7일)"]
    if surging:
        lines.append("**🚨 급상승:** " + ", ".join(f"{r['category']} {fmt(r['surge'])}" for r in surging[:5]))
    for r in rows[:5]:
        mark = "🚨 " if hot(r) else ""
        lines.append(f"- {mark}{r['category']}: {r['recent']}건 ({fmt(r['surge'])})")
    section = "\n".join(lines) + "\n\n"
    idx = report.find("\n## ")
    if idx == -1:
        return report + "\n" + section
    return report[: idx + 1] + section + report[idx + 1 :]


def main() -> int:
    _force_utf8_stdout()
    parser = argparse.ArgumentParser(description="AIRP Stage 1 — Crawl & Notify")
    parser.add_argument("--dry-run", action="store_true", help="알림 발송 없이 콘솔 출력만 (seen 기록 안 함)")
    parser.add_argument("--no-summary", action="store_true", help="LLM 요약 건너뜀")
    parser.add_argument("--no-archive", action="store_true", help="reports/ 아카이브 저장 건너뜀")
    parser.add_argument("--no-index", action="store_true", help="Qdrant/Neo4j 지식 색인 건너뜀")
    parser.add_argument("--no-translate", action="store_true", help="제목 한국어 번역 건너뜀")
    parser.add_argument("--group-by", choices=["category", "source"], default=None,
                        help="브리핑 묶음 기준 (기본: 설정 또는 category)")
    parser.add_argument("--classify", choices=["keyword", "llm"], default=None,
                        help="카탈로그 분류 방식 (기본: 설정 또는 keyword). llm은 LLM 키 필요")
    parser.add_argument("--limit-summary", type=int, default=0, help="요약할 최대 항목 수 (0=전체 신규 항목)")
    args = parser.parse_args()

    cfg = load_config()
    store = SeenStore(cfg.db_path)

    all_items, failed = collect_all(cfg)
    print(f"총 수집 {len(all_items)}건")
    if failed:
        print(f"실패한 소스: {', '.join(failed)}", file=sys.stderr)

    # 헬스체크: 아무것도 못 받았는데 실패가 있으면 = 모든 소스 장애로 간주하고 경고
    if not all_items and failed:
        warn = "⚠️ AI 브리핑: 모든 소스 수집 실패 — " + ", ".join(failed)
        print(warn, file=sys.stderr)
        if not args.dry_run and cfg.slack_webhook:
            try:
                slack.send(cfg.slack_webhook, warn)
            except Exception as e:  # noqa: BLE001
                print(f"[slack] 경고 발송 실패: {e}", file=sys.stderr)
        store.close()
        return 1

    # 키워드 필터 (sources.yaml의 filter 섹션)
    flt = (cfg.sources or {}).get("filter") or {}
    filtered = curate.keyword_filter(all_items, flt.get("include"), flt.get("exclude"))
    if len(filtered) != len(all_items):
        print(f"필터 후 {len(filtered)}건 (제외 {len(all_items) - len(filtered)}건)")

    new_items = store.filter_new(filtered)
    print(f"신규 {len(new_items)}건")

    if not new_items:
        print("신규 항목 없음 — 종료")
        store.close()
        return 0

    # 소스별 정렬(중요도)·상한
    max_per_source = int(flt.get("max_per_source", 0) or 0)
    display_items = curate.sort_and_cap(new_items, max_per_source)
    if len(display_items) != len(new_items):
        print(f"표시 {len(display_items)}건 (소스별 상한 {max_per_source})")

    # 브리핑 묶음 기준 결정 (CLI > 설정 > 기본 category) + 카탈로그 분류
    report_cfg = (cfg.sources or {}).get("report") or {}
    group_by = args.group_by or report_cfg.get("group_by") or "category"
    if group_by == "category":
        mode = args.classify or report_cfg.get("classify") or "keyword"
        if mode == "llm" and cfg.llm_provider and cfg.llm_api_key:
            print(f"카탈로그 분류: LLM ({cfg.llm_provider})")
            catalog.classify_all_llm(display_items, cfg.llm_provider, cfg.llm_api_key, cfg.llm_model)
        else:
            if mode == "llm":
                print("LLM 분류 요청됐으나 키 없음 → 키워드 분류로 대체", file=sys.stderr)
            catalog.classify_all(display_items)
        print(f"카탈로그 분포: {catalog.counts(display_items)}")

    # 제목 한국어 번역 (선택, LLM 필요) — 고유명사·약어는 원문 유지
    do_translate = (
        not args.no_translate
        and report_cfg.get("translate", True)
        and bool(cfg.llm_provider)
        and bool(cfg.llm_api_key)
    )
    if do_translate:
        n = sum(1 for it in display_items if it.title and not is_korean(it.title))
        skipped = len(display_items) - n
        print(f"제목 번역 중… ({n}건, 이미 한국어 {skipped}건 건너뜀)")
        translate.translate_titles_llm(display_items, cfg.llm_provider, cfg.llm_api_key, cfg.llm_model)

    # 요약 (선택) — 실제 표시할 항목만
    do_summary = (not args.no_summary) and bool(cfg.llm_provider) and bool(cfg.llm_api_key)
    if do_summary:
        targets = display_items if args.limit_summary <= 0 else display_items[: args.limit_summary]
        print(f"요약 중… ({len(targets)}건, provider={cfg.llm_provider})")

        def _summarize(it: Item) -> None:
            if it.abstract:
                it.summary = llm.summarize(it.abstract, cfg.llm_provider, cfg.llm_api_key, cfg.llm_model)

        parallel_map(_summarize, targets, workers=8)  # 순차 호출 → 동시 호출로 단축

    report = build_report(display_items, group_by=group_by)

    if args.dry_run:
        print("\n" + report)
        store.close()
        return 0

    # 지식 계층 색인 (선택): Qdrant/Neo4j가 설정돼 있으면 신규 항목을 적재
    if not args.no_index and (cfg.qdrant_url or cfg.neo4j_uri):
        try:
            _index_knowledge(cfg, display_items)
        except Exception as e:  # noqa: BLE001
            print(f"[knowledge] 색인 실패: {e}", file=sys.stderr)

    # 트렌드 섹션: 색인된 그래프에서 카테고리 급증을 계산해 리포트 상단에 삽입
    if cfg.neo4j_uri:
        try:
            report = _insert_trends(cfg, report)
        except Exception as e:  # noqa: BLE001
            print(f"[trend] 실패: {e}", file=sys.stderr)

    # 아카이브: reports/YYYY-MM-DD.md 저장 + 인덱스 재생성 (발송과 독립)
    if not args.no_archive:
        try:
            path = archive.write_report(report, cfg.archive_dir)
            archive.rebuild_index(cfg.archive_dir)
            print(f"[archive] 저장: {path}")
        except Exception as e:  # noqa: BLE001
            print(f"[archive] 실패: {e}", file=sys.stderr)

    sent = False
    if cfg.slack_webhook:
        slack.send(cfg.slack_webhook, report)
        print("[slack] 발송 완료")
        sent = True
    if cfg.smtp_host and cfg.email_to:
        try:
            email_notify.send(
                cfg.smtp_host, cfg.smtp_port, cfg.smtp_user, cfg.smtp_password,
                cfg.email_to, "AI 연구 브리핑", report,
            )
            print("[email] 발송 완료")
            sent = True
        except Exception as e:  # noqa: BLE001
            print(f"[email] 실패: {e}", file=sys.stderr)

    # 카카오톡 발송 비활성화(주석 처리). 다시 켜려면 아래 블록의 주석을 해제하고,
    # 상단 임포트에 `from datetime import datetime`, `kakao`(from .notify),
    # `build_digest`(from .report.builder)를 다시 추가하면 된다.
    # # 카카오톡: 길이 제한 때문에 다이제스트 + 전체 보기 링크로 발송
    # if cfg.kakao_rest_api_key and cfg.kakao_refresh_token:
    #     try:
    #         digest = build_digest(display_items, group_by=group_by)
    #         link = f"{cfg.report_base_url}/{datetime.now():%Y-%m-%d}.md" if cfg.report_base_url else ""
    #         kakao.send(cfg.kakao_rest_api_key, cfg.kakao_refresh_token, digest, link)
    #         print("[kakao] 발송 완료")
    #         sent = True
    #     except Exception as e:  # noqa: BLE001
    #         print(f"[kakao] 실패: {e}", file=sys.stderr)

    if not sent:
        print("발송 대상 미설정(SLACK_WEBHOOK_URL 등) — 콘솔 출력:")
        print("\n" + report)

    # 상한으로 이번에 표시 안 한 초과분까지 seen 처리해 다음날 재알림을 막는다
    store.mark_seen(new_items)
    store.close()
    print("완료.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
