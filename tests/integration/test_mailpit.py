"""Opt-in end-to-end check: EMAIL_TOOL_MAILPIT=1 uv run pytest tests/integration."""

import json
import os
import smtplib
import urllib.request
from email import message_from_bytes
from email.message import EmailMessage

import pytest


@pytest.mark.skipif(os.getenv("EMAIL_TOOL_MAILPIT") != "1", reason="Mailpit test is opt-in")
def test_mailpit_accepts_a_local_message() -> None:
    message = EmailMessage()
    message["From"] = "sender@example.test"
    message["To"] = "recipient@example.test"
    message["Subject"] = "Mailpit integration check"
    message.set_content("Captured locally")
    message.add_attachment(
        b"%PDF-1.4 integration fixture",
        maintype="application",
        subtype="pdf",
        filename="fixture.pdf",
    )
    with smtplib.SMTP("127.0.0.1", 1025, timeout=5) as client:
        client.send_message(message)
    with urllib.request.urlopen("http://127.0.0.1:8025/api/v1/messages", timeout=5) as response:
        listing = json.loads(response.read())
    matches = [
        item for item in listing["messages"] if item.get("Subject") == "Mailpit integration check"
    ]
    assert matches
    message_id = matches[0]["ID"]
    raw_url = f"http://127.0.0.1:8025/api/v1/message/{message_id}/raw"
    with urllib.request.urlopen(raw_url, timeout=5) as response:
        captured = message_from_bytes(response.read())
    attachment = next(part for part in captured.walk() if part.get_filename() == "fixture.pdf")
    assert attachment.get_payload(decode=True) == b"%PDF-1.4 integration fixture"
