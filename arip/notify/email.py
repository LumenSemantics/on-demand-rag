from __future__ import annotations

import smtplib
from email.mime.text import MIMEText


def send(
    host: str,
    port: str,
    user: str,
    password: str,
    to_addr: str,
    subject: str,
    body: str,
) -> None:
    """SMTP(STARTTLS)로 이메일을 보낸다."""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr

    with smtplib.SMTP(host, int(port)) as server:
        server.starttls()
        if user and password:
            server.login(user, password)
        server.sendmail(user, [to_addr], msg.as_string())
