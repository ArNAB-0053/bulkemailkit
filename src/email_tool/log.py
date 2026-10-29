import csv
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

FIELDS = ["campaign_id", "recipient", "timestamp", "subject", "status", "error"]


class CsvLog:
    def __init__(self, path: Path):
        self.path = path

    def successful_recipients(self, campaign_id: str) -> set[str]:
        if not self.path.exists():
            return set()
        try:
            with self.path.open(newline="", encoding="utf-8") as handle:
                return {
                    row["recipient"].casefold()
                    for row in csv.DictReader(handle)
                    if row.get("campaign_id") == campaign_id and row.get("status") == "sent"
                }
        except (OSError, csv.Error, KeyError) as exc:
            raise OSError(f"Cannot read send log {self.path}: {exc}") from exc

    def append(
        self, campaign_id: str, recipient: str, subject: str, status: str, error: str = ""
    ) -> None:
        rows: list[dict[str, str]] = []
        if self.path.exists():
            with self.path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        rows.append(
            {
                "campaign_id": campaign_id,
                "recipient": recipient,
                "timestamp": datetime.now(UTC).isoformat(),
                "subject": subject,
                "status": status,
                "error": error[:500],
            }
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_name = ""
        try:
            with tempfile.NamedTemporaryFile(
                "w", newline="", encoding="utf-8", dir=self.path.parent, delete=False
            ) as handle:
                temp_name = handle.name
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)
