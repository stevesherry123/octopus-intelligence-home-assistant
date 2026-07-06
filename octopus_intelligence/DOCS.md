# Octopus Intelligence

Octopus Intelligence compares the upcoming Agile price feed with matching
half-hour periods from recent history, detects unusually cheap or negative prices,
and optionally asks OpenAI to produce concise dashboard commentary.

Each run starts its actionable horizon at the next complete half-hour. A period
that is already in progress is excluded, so recommended cheap windows and alerts
never point into the past. The sensor exposes `source_forecast_periods` and
`excluded_elapsed_periods` for diagnostics.

## Prerequisite

The configured forecast entity must exist and expose an `ai_feed` attribute in
this format:

```text
05/07 00:00=18.41p; 05/07 00:30=17.93p;
```

The default entity is `sensor.octopus_price_feed_clean`.
The app also watches `octopus_energy_electricity_18p6302907_1300007213097_next_day_rates`
by default and triggers an immediate run when that entity changes from empty to
populated.

## Configuration

- **Interval hours:** Analysis frequency. The app also runs immediately at startup.
- **OpenAI API key:** Optional. Leave empty for deterministic analysis only.
- **OpenAI model:** A model available to the API project owning the key.
- **Forecast entity:** Source entity containing `attributes.ai_feed`.
- **Forecast ready entity:** Entity that becomes populated when the next-day rate
  feed has arrived.
- **Analysis entity:** Dashboard sensor created through the Home Assistant API.
- **Announcement entity:** Existing `input_text` helper refreshed after each run.
- **Publish announcement:** Disable to leave the announcement helper untouched.
- **Lookback days:** Historical comparison window.
- **History cache hours:** Maximum age before the external history cache refreshes.
- **Timezone:** IANA timezone used to interpret and display feed times.

The app receives a short-lived Home Assistant API credential from Supervisor. It
does not require or store a Home Assistant long-lived token.

## Dashboard

The custom chart and example dashboard are distributed in the project repository
under `home_assistant/`. Copy `octopus-intelligence-chart.js` to `/config/www`,
register it as a JavaScript module resource, and add `dashboard-card.yaml` as a
manual dashboard card.

## Recorder

The analysis sensor carries the full forecast as attributes. Exclude it from
Recorder unless you explicitly want every generated forecast stored:

```yaml
recorder:
  exclude:
    entities:
      - sensor.octopus_intelligence
```

The current forecast remains available to the dashboard when excluded.

## Troubleshooting

Check the app log first. A failed scheduled run retains the previous successful
Home Assistant state and retries at the next interval.

If the next-day rate entity remains empty, the app will keep using the normal
interval schedule.
