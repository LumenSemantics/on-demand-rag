from arip.collectors.rss import _clean


def test_clean_strips_html_tags_and_entities():
    assert _clean("<p>Hello&nbsp;<b>world</b>.</p>") == "Hello world."


def test_clean_collapses_whitespace():
    assert _clean("  a\n\n  b   c  ") == "a b c"


def test_clean_removes_image_credit_boilerplate():
    # 국내 매체가 붙이는 이미지 크레딧 주석은 기사 내용이 아니라 제거 대상.
    abs1 = "/챗GPT의 도움을 받아 제작한 이미지입니다. 실제 기사 본문이다."
    assert _clean(abs1) == "실제 기사 본문이다."


def test_clean_removes_credit_variant_with_extra_text():
    # "받아"와 "제작" 사이에 문구가 끼는 변형도 걷어낸다.
    abs2 = ("본문 앞부분이다. 챗GPT의 도움을 받아 시각화하고 기자가 최종 "
            "검토·확인 과정을 거쳐 제작한 이미지입니다. 이어지는 본문.")
    out = _clean(abs2)
    assert "챗GPT" not in out
    assert "본문 앞부분이다." in out
    assert "이어지는 본문." in out


def test_clean_removes_credit_inside_img_alt():
    # 크레딧이 <img alt="..."> 안에 오면 태그 제거로 함께 사라진다.
    abs3 = '<img alt="챗GPT의 도움을 받아 제작한 이미지입니다." src="http://x/a.jpg" /> 순수 본문.'
    out = _clean(abs3)
    assert "챗GPT" not in out
    assert "순수 본문." in out


def test_clean_keeps_legitimate_ai_mentions():
    # 정상적인 AI 언급(제작 크레딧이 아닌)은 보존한다.
    text = "삼성전자가 AI 반도체 신제품을 공개했다."
    assert _clean(text) == text
