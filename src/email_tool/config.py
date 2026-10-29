import json
import re
from pathlib import Path
from typing import Any

from email_tool.domain import ConfigurationError, EmailConfig, SmtpSettings

_EMAIL = re.compile(r"^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$")


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"'{key}' must be a non-empty string")
    return value.strip()


def load_config(path: Path) -> EmailConfig:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Configuration file not found: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Cannot read configuration: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigurationError("Configuration must be a JSON object")

    sender_name = _required_string(raw, "sender_name")
    sender = _required_string(raw, "sender_email")
    if any(char in sender_name + sender for char in "\r\n"):
        raise ConfigurationError("Sender name and email must not contain line breaks")
    if not _EMAIL.fullmatch(sender):
        raise ConfigurationError(f"Invalid sender email: {sender}")
    recipients_raw = raw.get("recipients")
    if not isinstance(recipients_raw, list) or not recipients_raw:
        raise ConfigurationError("'recipients' must be a non-empty list")
    recipients: list[str] = []
    seen: set[str] = set()
    for item in recipients_raw:
        if not isinstance(item, str) or not _EMAIL.fullmatch(item.strip()):
            raise ConfigurationError(f"Invalid recipient email: {item!r}")
        address = item.strip()
        if address.casefold() in seen:
            raise ConfigurationError(f"Duplicate recipient email: {address}")
        seen.add(address.casefold())
        recipients.append(address)

    subject = _required_string(raw, "subject")
    if any(char in subject for char in "\r\n"):
        raise ConfigurationError("'subject' must not contain line breaks")
    text_body = raw.get("text_body")
    if not isinstance(text_body, str) or not text_body.strip():
        raise ConfigurationError("'text_body' must be a non-empty string")
    html_body = raw.get("html_body")
    if html_body is not None and not isinstance(html_body, str):
        raise ConfigurationError("'html_body' must be a string or null")
    attachments_raw = raw.get("attachments", [])
    if not isinstance(attachments_raw, list):
        raise ConfigurationError("'attachments' must be a list of file paths")
    attachments: list[Path] = []
    for value in attachments_raw:
        if not isinstance(value, str) or not value.strip():
            raise ConfigurationError(f"Invalid attachment path: {value!r}")
        attachment = (path.resolve().parent / value).resolve()
        if not attachment.is_file() or not attachment.suffix:
            raise ConfigurationError(f"Attachment must be a readable file: {attachment}")
        try:
            with attachment.open("rb"):
                pass
        except OSError as exc:
            raise ConfigurationError(f"Attachment is not readable: {attachment}") from exc
        attachments.append(attachment)

    smtp_raw = raw.get("smtp", {})
    if not isinstance(smtp_raw, dict):
        raise ConfigurationError("'smtp' must be an object")
    host = smtp_raw.get("host", "127.0.0.1")
    port = smtp_raw.get("port", 1025)
    timeout = smtp_raw.get("timeout", 10)
    if not isinstance(host, str) or not host.strip():
        raise ConfigurationError("SMTP host must be a non-empty string")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ConfigurationError("SMTP port must be an integer from 1 to 65535")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ConfigurationError("SMTP timeout must be a positive number")
    campaign = raw.get("campaign_id") or "default"
    if not isinstance(campaign, str) or not campaign.strip():
        raise ConfigurationError("'campaign_id' must be a non-empty string")
    return EmailConfig(
        sender_name,
        sender,
        tuple(recipients),
        subject,
        text_body,
        html_body,
        tuple(attachments),
        SmtpSettings(host.strip(), port, float(timeout)),
        campaign.strip(),
    )
