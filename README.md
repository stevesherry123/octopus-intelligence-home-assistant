# Octopus Intelligence for Home Assistant

Local-first Octopus Agile price analysis with historical comparisons, a 48-hour
dashboard, short announcement text, and optional OpenAI commentary.

## Home Assistant app installation

Add this repository to the Home Assistant App/Add-on Store:

```text
https://github.com/stevesherry123/octopus-intelligence-home-assistant
```

Install **Octopus Intelligence**, configure it through the app's Configuration
tab, and start it. The app runs immediately and then at the configured interval.

The app receives a temporary Home Assistant API credential from Supervisor. It
does **not** require a long-lived Home Assistant token and does not read
`/config/secrets.yaml`. Enter the optional OpenAI API key in the app Configuration
tab, where it is treated as a password field.

The configured forecast entity must expose an `ai_feed` attribute such as:

```text
05/07 00:00=18.41p; 05/07 00:30=17.93p;
```

The default source is `sensor.octopus_price_feed_clean`. See the app documentation
in Home Assistant for every option and troubleshooting guidance.

## Dashboard

The example dashboard is in `home_assistant/dashboard-card.yaml`. Its dependency-
free chart is `home_assistant/www/octopus-intelligence-chart.js`.

1. Copy the JavaScript file to `/config/www`.
2. Register `/local/octopus-intelligence-chart.js` as a JavaScript module dashboard
   resource.
3. Add the dashboard YAML as a manual card.

## Recorder

The analysis sensor carries the full forecast in its attributes. Excluding it from
Recorder prevents unnecessary database growth while retaining the current
dashboard:

```yaml
recorder:
  exclude:
    entities:
      - sensor.octopus_intelligence
```

## Standalone development

The reusable Python engine remains runnable outside the native app:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev,ai]'
python -m unittest discover -s tests -v
```

Standalone deployments may supply `HA_TOKEN` and `OPENAI_API_KEY` as environment
variables. This is a development/advanced path; ordinary Home Assistant app users
should use Supervisor authentication and the app Configuration tab.

## Security

Never commit Home Assistant tokens, OpenAI keys, `secrets.yaml`, cached history, or
generated analysis files. OpenAI API usage is billed separately from ChatGPT
subscriptions.

No software licence has been selected yet. Choose one before redistributing or
accepting external contributions.
