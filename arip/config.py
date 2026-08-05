from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    sources: dict
    db_path: str
    slack_webhook: str
    llm_provider: str
    llm_api_key: str
    llm_model: str
    smtp_host: str
    smtp_port: str
    smtp_user: str
    smtp_password: str
    email_to: str


def load_config(sources_file: str = "config/sources.yaml") -> Config:
    sources: dict = {}
    p = Path(sources_file)
    if p.exists():
        sources = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    return Config(
        sources=sources,
        db_path=os.getenv("DB_PATH", "data/seen.db"),
        slack_webhook=os.getenv("SLACK_WEBHOOK_URL", ""),
        llm_provider=os.getenv("LLM_PROVIDER", "").strip(),
        llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
        llm_model=os.getenv("LLM_MODEL", "").strip(),
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=os.getenv("SMTP_PORT", "587"),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        email_to=os.getenv("EMAIL_TO", ""),
    )
