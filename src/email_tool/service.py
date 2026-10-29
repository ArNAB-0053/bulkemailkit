import smtplib
from collections.abc import Callable
from email.message import EmailMessage
from pathlib import Path

from email_tool.domain import EmailConfig, SendResult
from email_tool.log import CsvLog
from email_tool.mime import build_message

MessageBuilder = Callable[[EmailConfig, str], EmailMessage]


def preview(config: EmailConfig) -> str:
    lines = [
        f"From: {config.sender_name} <{config.sender_email}>",
        f"Subject: {config.subject}",
        f"Campaign: {config.campaign_id}",
        "Recipients:",
        *(f"  - {r}" for r in config.recipients),
        "Attachments:",
        *(f"  - {p.name}" for p in config.attachments),
        "",
        config.text_body,
    ]
    if config.html_body:
        lines.extend(["", "HTML alternative:", config.html_body])
    return "\n".join(lines)


def check_smtp(config: EmailConfig) -> None:
    with smtplib.SMTP(config.smtp.host, config.smtp.port, timeout=config.smtp.timeout) as client:
        client.noop()


def send_batch(
    config: EmailConfig, log: CsvLog, builder: MessageBuilder = build_message
) -> list[SendResult]:
    # Build and read every message before the first SMTP delivery attempt.
    messages = [(recipient, builder(config, recipient)) for recipient in config.recipients]
    already_sent = log.successful_recipients(config.campaign_id)
    results: list[SendResult] = []
    for recipient, message in messages:
        if recipient.casefold() in already_sent:
            results.append(SendResult(recipient, "skipped", "already sent for this campaign"))
            continue
        try:
            with smtplib.SMTP(
                config.smtp.host, config.smtp.port, timeout=config.smtp.timeout
            ) as client:
                client.send_message(message)
            result = SendResult(recipient, "sent")
        except (smtplib.SMTPException, OSError, TimeoutError) as exc:
            result = SendResult(recipient, "uncertain", f"{type(exc).__name__}: {exc}")
        log.append(config.campaign_id, recipient, config.subject, result.status, result.error)
        results.append(result)
    return results


def default_log_path() -> Path:
    return Path("send-log.csv")
