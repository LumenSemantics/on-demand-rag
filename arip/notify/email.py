from __future__ import annotations

import smtplib
from email.mime.text import MIMEText


def _recipients(to_addr: str) -> list[str]:
    """쉼표로 구분된 수신처 문자열을 주소 리스트로."""
    return [a.strip() for a in (to_addr or "").split(",") if a.strip()]


def build_message(user: str, to_addr: str, subject: str, body: str) -> tuple[list[str], str]:
    """수신처 목록과 직렬화된 메일 문자열을 만든다(순수 함수, 테스트용)."""
    recipients = _recipients(to_addr)
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = ", ".join(recipients)
    return recipients, msg.as_string()


def send(
    host: str,
    port: str,
    user: str,
    password: str,
    to_addr: str,
    subject: str,
    body: str,
) -> None:
    """SMTP(STARTTLS)로 이메일을 보낸다. to_addr는 쉼표로 여러 명 지정 가능."""
    recipients, raw = build_message(user, to_addr, subject, body)
    if not recipients:
        return

    with smtplib.SMTP(host, int(port)) as server:
        server.starttls()
        if user and password:
            server.login(user, password)
        server.sendmail(user, recipients, raw)
