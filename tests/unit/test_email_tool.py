import json
import smtplib
from email import message_from_bytes
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from email_tool import cli
from email_tool.config import load_config
from email_tool.domain import ConfigurationError
from email_tool.log import CsvLog
from email_tool.mime import build_message
from email_tool.service import preview, send_batch


def make_config(tmp_path: Path, recipients: list[str] | None = None) -> Path:
    attachment = tmp_path / "sample.pdf"
    attachment.write_bytes(b"%PDF-1.4 test bytes")
    data = {
        "sender_name": "Sender",
        "sender_email": "sender@example.test",
        "recipients": recipients or ["a@example.test", "b@example.test"],
        "subject": "Test",
        "text_body": "Hello",
        "html_body": "<b>Hello</b>",
        "attachments": ["sample.pdf"],
        "smtp": {"host": "127.0.0.1", "port": 1025},
        "campaign_id": "campaign-1",
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_config_rejects_duplicate_recipients(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="Duplicate"):
        load_config(make_config(tmp_path, ["a@example.test", "A@example.test"]))


def test_mime_contains_alternative_and_encoded_pdf(tmp_path: Path) -> None:
    config = load_config(make_config(tmp_path))
    message = build_message(config, config.recipients[0])
    parsed = message_from_bytes(message.as_bytes())
    assert parsed["To"] == "a@example.test"
    assert parsed.get_content_type() == "multipart/mixed"
    parts = list(parsed.walk())
    assert "text/html" in [part.get_content_type() for part in parts]
    attachment = next(part for part in parts if part.get_filename() == "sample.pdf")
    assert attachment.get_payload(decode=True) == b"%PDF-1.4 test bytes"


def test_preview_does_not_connect(tmp_path: Path) -> None:
    config = load_config(make_config(tmp_path))
    with patch("email_tool.service.smtplib.SMTP") as smtp:
        rendered = preview(config)
    smtp.assert_not_called()
    assert "a@example.test" in rendered and "sample.pdf" in rendered


def test_duplicate_detection_scoped_to_campaign(tmp_path: Path) -> None:
    config = load_config(make_config(tmp_path, ["a@example.test"]))
    log = CsvLog(tmp_path / "send.csv")
    log.append("campaign-1", "a@example.test", "Test", "sent")
    with patch("email_tool.service.smtplib.SMTP") as smtp:
        result = send_batch(config, log)
    smtp.assert_not_called()
    assert result[0].status == "skipped"


def test_partial_failure_keeps_other_recipient_result(tmp_path: Path) -> None:
    config = load_config(make_config(tmp_path))
    log = CsvLog(tmp_path / "send.csv")
    first = MagicMock()
    first.__enter__.return_value.send_message.return_value = {}
    second = MagicMock()
    second.__enter__.return_value.send_message.side_effect = smtplib.SMTPConnectError(421, b"busy")
    with patch("email_tool.service.smtplib.SMTP", side_effect=[first, second]):
        results = send_batch(config, log)
    assert [r.status for r in results] == ["sent", "uncertain"]
    assert log.successful_recipients("campaign-1") == {"a@example.test"}


def test_timeout_is_recorded_as_uncertain(tmp_path: Path) -> None:
    config = load_config(make_config(tmp_path, ["a@example.test"]))
    with patch("email_tool.service.smtplib.SMTP", side_effect=TimeoutError("timed out")):
        result = send_batch(config, CsvLog(tmp_path / "send.csv"))
    assert result[0].status == "uncertain"


def test_cli_requires_explicit_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = make_config(tmp_path)
    monkeypatch.setattr("sys.argv", ["email-tool", "--send", "--config", str(config_path)])
    monkeypatch.setattr("builtins.input", lambda _: "no")
    with patch("email_tool.cli.send_batch") as send:
        assert cli.main() == 1
    send.assert_not_called()


def test_cli_confirmation_sends_and_returns_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = make_config(tmp_path)
    monkeypatch.setattr("sys.argv", ["email-tool", "--send", "--config", str(config_path)])
    monkeypatch.setattr("builtins.input", lambda _: "SEND")
    from email_tool.domain import SendResult

    with patch("email_tool.cli.send_batch", return_value=[SendResult("a@example.test", "sent")]):
        assert cli.main() == 0
