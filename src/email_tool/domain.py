from dataclasses import dataclass
from pathlib import Path


class EmailToolError(Exception):
    """Base error suitable for display to a CLI user."""


class ConfigurationError(EmailToolError):
    pass


class DeliveryError(EmailToolError):
    pass


@dataclass(frozen=True)
class SmtpSettings:
    host: str = "127.0.0.1"
    port: int = 1025
    timeout: float = 10.0


@dataclass(frozen=True)
class EmailConfig:
    sender_name: str
    sender_email: str
    recipients: tuple[str, ...]
    subject: str
    text_body: str
    html_body: str | None
    attachments: tuple[Path, ...]
    smtp: SmtpSettings
    campaign_id: str


@dataclass(frozen=True)
class SendResult:
    recipient: str
    status: str
    error: str = ""
