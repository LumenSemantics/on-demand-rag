from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from .collectors.base import Item

# AI 주제 카탈로그 정의: (라벨, [정규식 패턴]).
# 위에서부터 먼저 매칭되는 카테고리로 분류(first-match-wins)하므로,
# 구체적인 주제를 위에, 포괄적인 LLM/기타를 아래에 둔다.
_RULES: list[tuple[str, list[str]]] = [
    ("🤖 에이전트·툴", [r"\bagents?\b", r"multi-?agent", r"tool[- ]?use", r"function[- ]?calling", r"tool-integrated"]),
    ("🔎 검색·RAG", [r"retrieval", r"\brag\b", r"retrieval-augmented", r"re-?rank", r"vector (search|database|store)"]),
    ("🧠 추론·수학", [r"reasoning", r"chain[- ]of[- ]thought", r"\bcot\b", r"\bmath\b", r"theorem", r"\bplanning\b", r"test[- ]time", r"inference[- ]time"]),
    ("🖼️ 멀티모달·비전", [r"multi-?modal", r"\bvision\b", r"\bvisual\b", r"\bimages?\b", r"\bvideos?\b", r"\b3d\b", r"diffusion", r"\bvlm\b", r"segmentation"]),
    ("🔊 음성·오디오", [r"\bspeech\b", r"\baudio\b", r"\basr\b", r"\btts\b", r"\bmusic\b", r"\bvoice\b"]),
    ("💻 코드", [r"\bcode\b", r"coding", r"program(ming)?", r"software engineering", r"swe-?bench", r"code (generation|editing)"]),
    ("⚡ 효율·최적화", [r"quantiz", r"efficien", r"\bsparse\b", r"\bmoe\b", r"mixture[- ]of[- ]experts", r"kv[- ]?cache", r"distillat", r"prun(e|ing)", r"long[- ]context", r"throughput", r"latency"]),
    ("🏋️ 학습·파인튜닝", [r"reinforcement learning", r"\brlhf\b", r"\bdpo\b", r"fine[- ]?tun", r"preference optimization", r"post[- ]training", r"pre[- ]?train", r"instruction tuning"]),
    ("📊 벤치마크·평가", [r"benchmark", r"evaluat", r"\beval\b", r"leaderboard"]),
    ("🛡️ 안전·정렬", [r"\bsafety\b", r"alignment", r"jailbreak", r"hallucinat", r"robustness", r"red[- ]?team", r"adversarial", r"\btoxic", r"\bbias\b"]),
    ("🏛️ 정책·규제", [r"regulat", r"governance", r"\bpolicy\b", r"compliance", r"eu ai act", r"legislation"]),
    ("📚 데이터셋", [r"\bdataset\b", r"\bcorpus\b", r"benchmark dataset"]),
    ("📝 언어모델(LLM)", [r"language models?", r"\bllms?\b", r"\bgpt\b", r"transformer", r"foundation models?", r"pretrained models?"]),
]
_ETC = "🗂️ 기타"

# 카탈로그 노출 순서 (규칙 순서 + 기타 맨 뒤)
CATEGORY_ORDER: list[str] = [label for label, _ in _RULES] + [_ETC]

# 패턴 사전 컴파일
_COMPILED: list[tuple[str, list[re.Pattern[str]]]] = [
    (label, [re.compile(p, re.IGNORECASE) for p in pats]) for label, pats in _RULES
]


def classify(item: Item) -> str:
    """제목+초록을 보고 AI 주제 카테고리 라벨을 돌려준다(미해당 시 기타)."""
    hay = f"{item.title} {item.abstract}"
    for label, patterns in _COMPILED:
        if any(p.search(hay) for p in patterns):
            return label
    return _ETC


def classify_all(items: Iterable[Item]) -> None:
    """각 항목의 category를 키워드 규칙으로 채운다(제자리 수정)."""
    for it in items:
        it.category = classify(it)


# ── LLM 기반 분류 ──────────────────────────────────────────────
_PAIR_RE = re.compile(r"(\d+)\s*=\s*(\d+)")


def _build_llm_prompt(batch: Sequence[Item]) -> str:
    cats = "\n".join(f"{i + 1}) {label}" for i, label in enumerate(CATEGORY_ORDER))
    rows = "\n".join(f"{i + 1}. {it.title}" for i, it in enumerate(batch))
    return (
        "다음 AI 연구/기술 항목들을 아래 카테고리 중 하나로 분류하라.\n\n"
        f"카테고리:\n{cats}\n\n"
        f"항목:\n{rows}\n\n"
        "각 항목마다 '항목번호=카테고리번호'만 한 줄씩 출력하라. 설명·다른 텍스트 금지.\n"
        "예)\n1=1\n2=6\n"
    )


def _parse_llm_labels(raw: str, n: int) -> list[str | None]:
    """'항목번호=카테고리번호' 응답을 파싱해 항목 순서대로 라벨 리스트를 만든다.

    유효 범위를 벗어난 항목은 None(→ 상위에서 키워드로 폴백).
    """
    labels: list[str | None] = [None] * n
    for a, b in _PAIR_RE.findall(raw or ""):
        i, c = int(a) - 1, int(b) - 1
        if 0 <= i < n and 0 <= c < len(CATEGORY_ORDER):
            labels[i] = CATEGORY_ORDER[c]
    return labels


def classify_all_llm(
    items: Iterable[Item],
    provider: str,
    api_key: str,
    model: str,
    batch_size: int = 25,
) -> None:
    """LLM으로 분류해 category를 채운다. 실패한 항목은 키워드 규칙으로 폴백."""
    # 지연 임포트로 순환 참조 회피
    from .summarize import llm

    items = list(items)
    for start in range(0, len(items), batch_size):
        batch = items[start : start + batch_size]
        labels: list[str | None]
        try:
            raw = llm.complete(_build_llm_prompt(batch), provider, api_key, model, max_tokens=600)
            labels = _parse_llm_labels(raw, len(batch))
        except Exception:  # noqa: BLE001
            labels = [None] * len(batch)
        for it, lab in zip(batch, labels):
            it.category = lab or classify(it)  # 미분류/실패 → 키워드


def counts(items: Sequence[Item]) -> dict[str, int]:
    """카테고리별 건수(카탈로그 순서 유지)."""
    out: dict[str, int] = {}
    for it in items:
        label = it.category or classify(it)
        out[label] = out.get(label, 0) + 1
    return {label: out[label] for label in CATEGORY_ORDER if label in out}
