from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

import httpx

T = TypeVar("T")
R = TypeVar("R")


def http_get(url: str, *, retries: int = 3, backoff: float = 1.0, **kwargs) -> httpx.Response:
    """httpx.get + raise_for_status에 지수 백오프 재시도를 더한다.

    타임아웃·연결 오류·5xx는 재시도, 4xx(잘못된 요청·죽은 피드)는 즉시 예외.
    """
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            resp = httpx.get(url, **kwargs)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as e:
            if 400 <= e.response.status_code < 500:
                raise  # 클라이언트 오류는 재시도해도 소용없음
            last_exc = e
        except httpx.TransportError as e:  # 타임아웃·연결 실패 등
            last_exc = e
        if attempt < retries - 1:
            time.sleep(backoff * (2**attempt))
    assert last_exc is not None
    raise last_exc


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
