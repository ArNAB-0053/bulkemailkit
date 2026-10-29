import argparse
import smtplib
import sys
from pathlib import Path

from email_tool.config import load_config
from email_tool.domain import EmailToolError
from email_tool.log import CsvLog
from email_tool.service import check_smtp, preview, send_batch


def main() -> int:
    parser = argparse.ArgumentParser(prog="email-tool")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--preview", action="store_true")
    mode.add_argument("--send", action="store_true")
    parser.add_argument("--config", type=Path, default=Path("config.json"))
    parser.add_argument("--log", type=Path, default=Path("send-log.csv"))
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        if args.check:
            check_smtp(config)
            print(f"Configuration valid; SMTP reachable at {config.smtp.host}:{config.smtp.port}.")
            return 0
        if args.preview:
            print(preview(config))
            return 0
        print(preview(config))
        previously_sent = CsvLog(args.log).successful_recipients(config.campaign_id)
        duplicates = [r for r in config.recipients if r.casefold() in previously_sent]
        if duplicates:
            print(f"Already sent for campaign {config.campaign_id}; these will be skipped:")
            for recipient in duplicates:
                print(f"  - {recipient}")
        answer = input("Send these individual emails? Type SEND to continue: ")
        if answer != "SEND":
            print("Sending cancelled.")
            return 1
        results = send_batch(config, CsvLog(args.log))
        for result in results:
            suffix = f" ({result.error})" if result.error else ""
            print(f"{result.recipient}: {result.status}{suffix}")
        return 0 if all(r.status in {"sent", "skipped"} for r in results) else 2
    except (EmailToolError, OSError, TimeoutError, smtplib.SMTPException) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
