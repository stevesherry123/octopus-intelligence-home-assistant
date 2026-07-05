# Octopus Intelligence

A local-first analysis engine for Octopus Agile electricity prices. Numerical
analysis is deliberately separate from Home Assistant and AI commentary so the
same core can later be packaged as an add-on, custom integration, or standalone
service.

## Current first slice

- Downloads and locally caches the Agile Buddy historic feed.
- Stores timestamps as timezone-aware UTC.
- Converts to `Europe/London` only for human-facing grouping and display.
- Compares a forecast with matching half-hour slots from the preceding 7–14 days.
- Detects free/negative periods and cheapest consecutive windows.
- Produces structured JSON suitable for a Home Assistant dashboard or an AI prompt.
- Parses the Home Assistant `ai_feed` format, including negative prices and UK
  daylight-saving transitions.
- Includes a local Home Assistant REST adapter for reading the forecast, publishing
  rich dashboard attributes, and retaining `input_text.announce_text` compatibility.
- Audits forecast continuity, missing periods, and historical baseline coverage.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
octopus-intelligence download-history --output data/agile-history.json
pytest
```

Dry-run the full pipeline without changing Home Assistant or calling OpenAI:

```bash
export OIE_HISTORY_FILE=/path/to/history.json
octopus-intelligence run --feed-file tests/fixtures/sample-ai-feed.txt --dry-run --no-ai
```

For live operation, supply secrets as environment variables rather than committing
them to this project:

```bash
export HA_TOKEN='...'
export OPENAI_API_KEY='...'
octopus-intelligence run
```

When running in the Jupyter add-on, credentials can instead remain in Home
Assistant's `/config/secrets.yaml`:

```yaml
oie_ha_token: "your-long-lived-access-token"
oie_openai_api_key: "your-OpenAI-API-key"
oie_openai_model: "gpt-4o-mini"
```

Only those two named entries are read. Environment variables take precedence, and
the names/file can be overridden with `OIE_HA_TOKEN_SECRET`,
`OIE_OPENAI_API_KEY_SECRET`, and `OIE_SECRETS_FILE`.

For the first controlled write, publish only the dashboard sensor:

```bash
octopus-intelligence run --no-ai --no-announce
```

Run continuously every three hours:

```bash
octopus-intelligence schedule --interval-hours 3
```

The scheduler runs immediately, retains the previous good Home Assistant state if
a later run fails, and writes health to `data/scheduler-status.json`. Only one
scheduler can run per data directory. Running it inside the Jupyter add-on does not
survive an add-on/container restart; native add-on packaging is the planned durable
deployment.

`home_assistant/dashboard-card.yaml` contains the dashboard. The forecast chart is
a dependency-free custom card included at
`home_assistant/www/octopus-intelligence-chart.js`; it requires no HACS download.
Copy that file into `/config/www`, register `/local/octopus-intelligence-chart.js`
as a JavaScript module dashboard resource, then paste the dashboard YAML into a
manual card.

`HA_URL` defaults to `http://homeassistant.local:8123`. Every entity ID, file path,
model, timezone and lookback period can be overridden with environment variables;
see `src/octopus_intelligence/config.py`.

An OpenAI API key is separately billed API access; a ChatGPT subscription does not
itself fund API calls. If the key or AI dependency is absent, numerical analysis and
the deterministic announcement still work.

The download endpoint reports each timestamp as the end of a half-hour settlement
period. The downloader therefore subtracts 30 minutes when normalising records.
This is configurable in the library for alternative feeds.

## Jupyter: download a whole project quickly

Jupyter's file browser is awkward for nested folder downloads. From a Jupyter
terminal, archive the project folder first:

```bash
tar -czf Octopus_Intelligence_Engine.tar.gz Octopus_Intelligence_Engine/
```

Then download the single `.tar.gz` file from the Jupyter file browser. To create a
ZIP that is friendlier on Windows:

```bash
zip -r Octopus_Intelligence_Engine.zip Octopus_Intelligence_Engine/
```

Do not include notebooks or files containing unredacted tokens in an archive you
intend to share.

## Planned adapters

1. OpenAI Responses API commentary over deterministic analysis results.
2. End-to-end command and configurable scheduling.
3. Persistent Home Assistant integration/add-on and dashboard example.
