# Email Automation Toolkit

A local Python utility that sends one separate email per recipient. Its initial delivery target is Mailpit, which captures messages locally and never delivers them to real recipients. Gmail integration is not included.

## Prerequisites and setup

Install Python 3.12, [uv](https://docs.astral.sh/uv/), and Docker Desktop. From this directory:

```powershell
uv python pin 3.12
uv sync
```

`uv.lock` records the resolved development tools. The application uses Python's standard library at runtime. `config.json` is intentionally local and ignored by Git. Create it from the example, then edit sender, recipients, subject, body, and optional attachments:

```powershell
Copy-Item config.example.json config.json
```

Put private documents in `attachments/`; that directory is ignored apart from its placeholder file. Attachment paths are resolved relative to the configuration file. Keep `campaign_id` stable for one batch so the send log can identify successful prior sends.

## Start Mailpit

```powershell
docker compose up -d
docker compose ps
```

Mailpit SMTP binds only to `127.0.0.1:1025`; its web interface is at [http://127.0.0.1:8025](http://127.0.0.1:8025). Stop it with `docker compose down`. The Python app runs on the host and defaults to `127.0.0.1:1025`. If the app is later run in a container on the same Compose network, use the service hostname `mailpit` and port `1025` instead.

## Validate, preview, send

```powershell
uv run email-tool --check
uv run email-tool --preview
uv run email-tool --send
```

`--check` validates config and attachments, then checks SMTP connectivity; it does not send. `--preview` shows recipients, subject, attachment names, and body; it does not send. `--send` displays the batch and requires typing `SEND`. Each recipient gets their own message with no other recipients in CC or BCC. The default log is `send-log.csv`; select another config or log with `--config` / `--log`.

Successful recipients are skipped on another run with the same campaign ID. SMTP failures are recorded as `uncertain`: a timeout or disconnect can happen after the server accepted a message, so inspect Mailpit before manually retrying. Local CSV logging is crash-conscious but is not a transactional database; SMTP cannot guarantee exactly-once delivery.

## Development

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

The Mailpit integration test is opt-in and only targets localhost:

```powershell
$env:EMAIL_TOOL_MAILPIT = "1"
uv run pytest tests/integration
```

## Troubleshooting

- **SMTP connection refused:** confirm Docker Desktop is running and `docker compose ps` reports Mailpit healthy.
- **Missing attachment:** paths in the JSON are relative to the config file; verify the file exists and can be read.
- **Recipient validation error:** correct the address in `config.json`; invalid and repeated addresses are rejected explicitly.
- **Recipient marked uncertain:** check Mailpit's inbox and the CSV error before retrying. Do not assume the server did not accept the message.

This local setup is for development and message inspection. Mailpit does not deliver messages. A future Gmail integration would be a separate delivery implementation and is intentionally absent here.
