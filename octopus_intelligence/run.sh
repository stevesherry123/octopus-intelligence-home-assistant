#!/usr/bin/with-contenv bashio
set -euo pipefail

export HA_URL="http://supervisor/core"
export HA_TOKEN="${SUPERVISOR_TOKEN}"
export OPENAI_API_KEY="$(bashio::config 'openai_api_key')"
export OPENAI_MODEL="$(bashio::config 'openai_model')"
export OIE_FORECAST_ENTITY="$(bashio::config 'forecast_entity')"
export OIE_FORECAST_READY_ENTITY="$(bashio::config 'forecast_ready_entity')"
export OIE_ANALYSIS_ENTITY="$(bashio::config 'analysis_entity')"
export OIE_ANNOUNCEMENT_ENTITY="$(bashio::config 'announcement_entity')"
export OIE_LOOKBACK_DAYS="$(bashio::config 'lookback_days')"
export OIE_HISTORY_CACHE_HOURS="$(bashio::config 'history_cache_hours')"
export OIE_TIMEZONE="$(bashio::config 'timezone')"
export OIE_HISTORY_FILE="/data/agile-history.json"
export OIE_OUTPUT_FILE="/data/latest-analysis.json"

interval_hours="$(bashio::config 'interval_hours')"
arguments=(schedule --interval-hours "${interval_hours}")

if ! bashio::config.has_value 'openai_api_key'; then
    arguments+=(--no-ai)
    bashio::log.warning "No OpenAI API key configured; AI commentary is disabled"
fi

if ! bashio::config.true 'publish_announcement'; then
    arguments+=(--no-announce)
fi

bashio::log.info "Starting Octopus Intelligence; interval ${interval_hours} hours"
bashio::log.info "Forecast entity: ${OIE_FORECAST_ENTITY}"
bashio::log.info "Trigger entity: ${OIE_FORECAST_READY_ENTITY}"
exec /opt/octopus-intelligence/bin/octopus-intelligence "${arguments[@]}"
