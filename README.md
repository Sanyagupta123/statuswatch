# StatusWatch

StatusWatch is a local website and API reliability monitor built with Flask, SQLite, Requests, APScheduler, and a responsive HTML dashboard. It stores sampled check results and incident history on the machine where it runs.

## Requirements

- Python 3.11 or newer
- pip

## Run on Windows

From the project directory in PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again. Open [http://127.0.0.1:5000](http://127.0.0.1:5000). The server intentionally binds only to loopback. The default database is `instance/statuswatch.sqlite3`; set `STATUSWATCH_DATABASE` is not currently supported, but the database path can be selected through `create_app({"DATABASE": "..."})` when embedding the app or writing tests.

## Architecture

- `app.py`: local development entry point; starts the background scheduler and Flask server.
- `statuswatch/__init__.py`: app factory and JSON API routes.
- `database.py`: SQLite schema and parameterized persistence helpers. Timestamps are UTC ISO 8601 strings.
- `monitor.py`: URL validation and bounded streamed HTTP checks. Redirects are disabled and response bodies are not consumed.
- `incidents.py`: opens an incident after two consecutive failures and resolves it after two consecutive successes.
- `analytics.py`: sampled check success rate and successful-response latency statistics.
- `scheduler.py`: per-monitor background interval jobs with one in-flight instance per job.
- `templates/` and `static/`: responsive dark dashboard, forms, actions, incident history, and Chart.js latency graph.
- `tests/`: isolated pytest coverage using temporary SQLite databases and mocked HTTP.

## API

All endpoints return JSON except the dashboard at `/`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Service health |
| GET | `/api/monitors` | Monitors and latest sampled summary |
| POST | `/api/monitors` | Create a monitor (`name`, `url`, optional `interval_seconds`, 15–86400) |
| POST | `/api/monitors/<id>/check` | Run a manual check |
| GET | `/api/monitors/<id>/checks` | Latest 100 check results |
| GET | `/api/monitors/<id>/analytics` | Sampled success rate, successful latency range/average, and recent history |
| GET | `/api/monitors/<id>/incidents` | Latest incident and recovery records |

Monitor names must contain 1–80 characters. URLs must use HTTP or HTTPS, resolve to public IP addresses, and cannot contain embedded credentials. Private, loopback, link-local, reserved, localhost, `.local`, and `.localhost` targets are rejected. Redirects are not followed. Success means HTTP status 200–399; HTTP errors and transport failures count as failed samples.

## Tests

```powershell
python -m pytest -q
```

The test app receives a temporary database path and HTTP calls are mocked, so tests do not change the development database or depend on public websites.

## Security and limitations

This is a single-user local prototype, not a public URL checking service. Binding to `127.0.0.1` limits remote access. URL validation also rejects non-public DNS results and the checker disables redirects and environment proxies. DNS validation and the subsequent network connection are separate operations, so a hostile DNS change can still create a time-of-check/time-of-use risk. A public deployment needs network-level egress controls (for example, an outbound proxy/firewall that blocks private and metadata ranges), DNS rebinding defenses, authentication, rate limits, audit logging, resource limits, and operational hardening. Do not expose this development server directly to the internet.

Availability is reported as observed sampled check success rate, not continuous wall-clock uptime. Checks can miss short outages between intervals. The dashboard loads Chart.js from a CDN; an internet connection is needed for the chart library, while the backend works without the CDN. HTTPS certificate verification remains enabled.

## Future improvements

Authentication and multiple user workspaces, monitor editing/disabling, configurable success rules, retention policies, alert delivery, migrations, and network-enforced SSRF protection are natural next steps.

## Publish to GitHub

Create an empty repository on GitHub, then run (replace the remote URL):

```powershell
git init
git add .
git commit -m "Build StatusWatch reliability monitor"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/statuswatch.git
git push -u origin main
```
