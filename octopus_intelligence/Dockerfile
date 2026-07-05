FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION="dev"
ARG BUILD_ARCH="unknown"

LABEL \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}" \
    org.opencontainers.image.title="Octopus Intelligence" \
    org.opencontainers.image.description="Octopus Agile price analysis for Home Assistant"

RUN apk add --no-cache python3 py3-pip

COPY app /app
RUN python3 -m venv /opt/octopus-intelligence \
    && /opt/octopus-intelligence/bin/pip install --no-cache-dir '/app[ai]'

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]

