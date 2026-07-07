# Changelog

## 0.5.3

- Add daily pattern commentary comparing prices with the usual 08:00 and 16:00-19:00 peaks.
- Highlight variances when expected peaks are muted or the highest price falls outside the usual peak windows.

## 0.5.2

- Trigger an immediate run when the configured next-day rates entity becomes populated.
- Keep the existing timed cycle as a fallback if the trigger entity does not update.
- Expose the watched trigger entity in the add-on configuration and startup logs.
- Synchronize the trigger implementation into the packaged Home Assistant app.

## 0.5.0

- Restrict all actionable analysis to complete, upcoming half-hour periods.
- Exclude elapsed and in-progress periods from averages, comparisons, extrema,
  free/negative alerts, cheapest windows, announcements, and AI commentary.
- Publish source and excluded period counts for dashboard transparency.
- Add tests for exact-boundary and mid-period scheduler runs.

## 0.4.0

- Initial native Home Assistant app package.
- Uses Supervisor-managed Home Assistant API authentication.
- Runs analysis immediately and on a configurable interval.
- Persists history and health data under `/data`.
