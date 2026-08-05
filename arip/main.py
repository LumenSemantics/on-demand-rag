from __future__ import annotations

import argparse
import sys

from .collectors import arxiv, huggingface, rss
from .collectors.base import Item
from .config import Config, load_config
from .notify import email as email_notify
from .notify import slack
from .report.builder import build_report
from .store.dedup import SeenStore
from .summarize import llm


def collect_all(cfg: Config) -> list[Item]:
    """설정된 모든 소스를 수집한다. 한 소스가 실패해도 나머지는 진행."""
    items: list[Item] = []
    src = cfg.sources or {}

    ax = src.get("arxiv") or {}
    if ax:
        try:
            got = arxiv.collect(ax.get("categories", ["cs.AI"]), ax.get("max_results", 30))
            print(f"[arxiv] {len(got)}건")
            items += got
        except Exception as e:  # noqa: BLE001
            print(f"[arxiv] 실패: {e}", file=sys.stderr)

    hf = src.get("huggingface") or {}
    if hf.get("daily_papers"):
        try:
            got = huggingface.collect(hf.get("limit", 30))
            print(f"[huggingface] {len(got)}건")
            items += got
        except Exception as e:  # noqa: BLE001
            print(f"[huggingface] 실패: {e}", file=sys.stderr)

    for feed in src.get("rss", []) or []:
        name = feed.get("name", "?")
        try:
            got = rss.collect(name, feed["url"], feed.get("limit", 15))
            print(f"[rss:{name}] {len(got)}건")
            items += got
        except Exception as e:  # noqa: BLE001
            print(f"[rss:{name}] 실패: {e}", file=sys.stderr)

    return items


def _force_utf8_stdout() -> None:
    """Windows 콘솔(cp949 등)에서 이모지·한글 출력이 깨지거나 죽지 않도록 UTF-8로 강제."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass


def main() -> int:
    _force_utf8_stdout()
    parser = argparse.ArgumentParser(description="ARIP Stage 1 — Crawl & Notify")
    parser.add_argument("--dry-run", action="store_true", help="알림 발송 없이 콘솔 출력만 (seen 기록 안 함)")
    parser.add_argument("--no-summary", action="store_true", help="LLM 요약 건너뜀")
    parser.add_argument("--limit-summary", type=int, default=0, help="요약할 최대 항목 수 (0=전체 신규 항목)")
    args = parser.parse_args()

    cfg = load_config()
    store = SeenStore(cfg.db_path)

    all_items = collect_all(cfg)
    print(f"총 수집 {len(all_items)}건")

    new_items = store.filter_new(all_items)
    print(f"신규 {len(new_items)}건")

    if not new_items:
        print("신규 항목 없음 — 종료")
        store.close()
        return 0

    do_summary = (not args.no_summary) and bool(cfg.llm_provider) and bool(cfg.llm_api_key)
    if do_summary:
        targets = new_items if args.limit_summary <= 0 else new_items[: args.limit_summary]
        print(f"요약 중… ({len(targets)}건, provider={cfg.llm_provider})")
        for it in targets:
            if it.abstract:
                it.summary = llm.summarize(it.abstract, cfg.llm_provider, cfg.llm_api_key, cfg.llm_model)

    report = build_report(new_items)

    if args.dry_run:
        print("\n" + report)
        store.close()
        return 0

    sent = False
    if cfg.slack_webhook:
        slack.send(cfg.slack_webhook, report)
        print("[slack] 발송 완료")
        sent = True
    if cfg.smtp_host and cfg.email_to:
        email_notify.send(
            cfg.smtp_host, cfg.smtp_port, cfg.smtp_user, cfg.smtp_password,
            cfg.email_to, "AI 연구 브리핑", report,
        )
        print("[email] 발송 완료")
        sent = True

    if not sent:
        print("발송 대상 미설정(SLACK_WEBHOOK_URL 등) — 콘솔 출력:")
        print("\n" + report)

    store.mark_seen(new_items)
    store.close()
    print("완료.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
