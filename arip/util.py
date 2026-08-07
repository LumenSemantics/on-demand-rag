from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")


def parallel_map(fn: Callable[[T], R], items: Sequence[T], workers: int = 6) -> list[R]:
    """items에 fn을 병렬로 적용한다(입력 순서 유지).

    LLM/HTTP 호출처럼 I/O 대기가 큰 작업을 동시에 처리해 전체 시간을 줄인다.
    workers<=1 이거나 항목이 1개면 그냥 순차 실행한다.
    """
    seq = list(items)
    if not seq:
        return []
    if workers <= 1 or len(seq) == 1:
        return [fn(x) for x in seq]
    with ThreadPoolExecutor(max_workers=min(workers, len(seq))) as ex:
        return list(ex.map(fn, seq))
