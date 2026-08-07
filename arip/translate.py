from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from .collectors.base import Item

_LINE_RE = re.compile(r"^\s*(\d+)[.)]\s*(.+?)\s*$", re.MULTILINE)


def _build_prompt(batch: Sequence[Item]) -> str:
    rows = "\n".join(f"{i + 1}. {it.title}" for i, it in enumerate(batch))
    return (
        "다음 AI 연구/기술 항목 제목을 한국어로 번역하라.\n"
        "규칙: 모델명·고유명사·기술 약어(GPT, RAG, LoRA, Transformer, MoE 등)는 원문 그대로 두고 "
        "나머지만 자연스러운 한국어로 옮겨라. 이미 한국어면 그대로 둔다.\n"
        "각 항목을 '번호. 번역' 형식으로 정확히 한 줄씩만 출력하라. 번역 안에 줄바꿈·설명 금지.\n\n"
        f"{rows}\n"
    )


def _parse(raw: str, n: int) -> list[str | None]:
    """'번호. 번역' 응답을 항목 순서대로 파싱. 누락/실패는 None."""
    out: list[str | None] = [None] * n
    for m in _LINE_RE.finditer(raw or ""):
        i = int(m.group(1)) - 1
        if 0 <= i < n:
            out[i] = m.group(2).strip()
    return out


def translate_titles_llm(
    items: Iterable[Item],
    provider: str,
    api_key: str,
    model: str,
    batch_size: int = 15,
) -> None:
    """제목을 LLM으로 한국어 번역해 title_ko에 채운다. 실패 항목은 빈 값(원문 유지)."""
    from .summarize import llm
    from .util import parallel_map

    items = list(items)
    batches = [items[i : i + batch_size] for i in range(0, len(items), batch_size)]

    def _do(batch: list[Item]) -> None:
        try:
            raw = llm.complete(_build_prompt(batch), provider, api_key, model, max_tokens=2000)
            translations = _parse(raw, len(batch))
        except Exception:  # noqa: BLE001
            translations = [None] * len(batch)
        for it, ko in zip(batch, translations):
            it.title_ko = ko or ""

    parallel_map(_do, batches, workers=4)
