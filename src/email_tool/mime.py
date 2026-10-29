import mimetypes
from email.message import EmailMessage
from email.utils import formataddr

from email_tool.domain import EmailConfig


def build_message(config: EmailConfig, recipient: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = formataddr((config.sender_name, config.sender_email))
    message["To"] = recipient
    message["Subject"] = config.subject
    message.set_content(config.text_body)
    if config.html_body:
        message.add_alternative(config.html_body, subtype="html")
    for path in config.attachments:
        content_type, _ = mimetypes.guess_type(path.name)
        maintype, subtype = (content_type or "application/octet-stream").split("/", 1)
        message.add_attachment(
            path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name
        )
    return message
