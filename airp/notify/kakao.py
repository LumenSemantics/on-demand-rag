from __future__ import annotations

import json

import httpx

TOKEN_URL = "https://kauth.kakao.com/oauth/token"
MEMO_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
TEXT_LIMIT = 1900  # 카카오 텍스트 템플릿은 2000자 제한 → 여유 두고 자름


def _refresh_access_token(rest_api_key: str, refresh_token: str) -> str:
    """refresh token으로 단기 access token을 발급받는다."""
    r = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": rest_api_key,
            "refresh_token": refresh_token,
        },
        timeout=30.0,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def build_template(text: str, link_url: str = "") -> dict:
    """카카오 '나에게 보내기' 기본 텍스트 템플릿 객체를 만든다(순수 함수, 테스트용)."""
    if len(text) > TEXT_LIMIT:
        text = text[:TEXT_LIMIT] + "\n… (전체는 링크에서)"
    url = link_url or "https://github.com"  # link 객체는 필수라 폴백 제공
    return {
        "object_type": "text",
        "text": text,
        "link": {"web_url": url, "mobile_web_url": url},
        "button_title": "전체 보기",
    }


def send(rest_api_key: str, refresh_token: str, text: str, link_url: str = "") -> None:
    """내 카카오톡 '나와의 채팅'으로 메시지를 보낸다."""
    token = _refresh_access_token(rest_api_key, refresh_token)
    template = build_template(text, link_url)
    r = httpx.post(
        MEMO_URL,
        headers={"Authorization": f"Bearer {token}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=30.0,
    )
    r.raise_for_status()
