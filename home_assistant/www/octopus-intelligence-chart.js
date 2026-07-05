class OctopusIntelligenceChart extends HTMLElement {
  constructor() {
    super();
    this._root = this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this.config = {
      entity: "sensor.octopus_intelligence",
      title: "48-hour price outlook",
      height: 320,
      ...config,
    };
    if (!this.config.entity) throw new Error("An entity is required");
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  getCardSize() {
    return 5;
  }

  static getStubConfig() {
    return { entity: "sensor.octopus_intelligence" };
  }

  escape(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  render() {
    if (!this._hass || !this.config) return;
    const entity = this._hass.states[this.config.entity];
    if (!entity) {
      this._root.innerHTML = `<ha-card><div class="missing">Entity ${this.escape(this.config.entity)} is unavailable.</div></ha-card>`;
      return;
    }

    const periods = Array.isArray(entity.attributes.periods)
      ? entity.attributes.periods
      : [];
    if (periods.length < 2) {
      this._root.innerHTML = "<ha-card><div class=\"missing\">No forecast periods are available.</div></ha-card>";
      return;
    }

    const width = 900;
    const height = Number(this.config.height) || 320;
    const margin = { top: 22, right: 22, bottom: 54, left: 58 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const forecast = periods.map((row) => Number(row.price_p_per_kwh));
    const baseline = periods.map((row) =>
      row.baseline_p_per_kwh == null ? null : Number(row.baseline_p_per_kwh)
    );
    const numeric = [...forecast, ...baseline.filter((value) => value != null), 0];
    let minimum = Math.floor(Math.min(...numeric) / 5) * 5;
    let maximum = Math.ceil(Math.max(...numeric) / 5) * 5;
    if (minimum === maximum) maximum = minimum + 5;

    const x = (index) => margin.left + (index / (periods.length - 1)) * plotWidth;
    const y = (value) =>
      margin.top + ((maximum - value) / (maximum - minimum)) * plotHeight;
    const pathFor = (values) => {
      let started = false;
      return values
        .map((value, index) => {
          if (value == null || !Number.isFinite(value)) {
            started = false;
            return "";
          }
          const command = started ? "L" : "M";
          started = true;
          return `${command}${x(index).toFixed(1)},${y(value).toFixed(1)}`;
        })
        .join(" ");
    };

    const grid = Array.from({ length: 5 }, (_, index) => {
      const value = maximum - (index * (maximum - minimum)) / 4;
      const position = y(value);
      return `<line class="grid" x1="${margin.left}" x2="${width - margin.right}" y1="${position}" y2="${position}" />
        <text class="axis y-axis" x="${margin.left - 10}" y="${position + 4}" text-anchor="end">${value.toFixed(0)}p</text>`;
    }).join("");

    const labelStep = Math.max(1, Math.ceil(periods.length / 8));
    const labels = periods
      .map((row, index) => {
        if (index % labelStep !== 0 && index !== periods.length - 1) return "";
        const date = new Date(row.start_utc);
        const label = new Intl.DateTimeFormat(undefined, {
          weekday: "short",
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        }).format(date);
        const anchor = index === 0 ? "start" : index === periods.length - 1 ? "end" : "middle";
        return `<text class="axis" x="${x(index)}" y="${height - 22}" text-anchor="${anchor}">${this.escape(label)}</text>`;
      })
      .join("");

    const cheap = entity.attributes.cheapest_windows?.["2_hours"];
    let cheapBand = "";
    if (cheap) {
      const start = periods.findIndex((row) => row.start_utc === cheap.start_utc);
      const endTime = new Date(cheap.end_utc).getTime();
      let end = periods.findIndex((row) => new Date(row.start_utc).getTime() >= endTime);
      if (start >= 0) {
        if (end < 0) end = periods.length - 1;
        const left = x(start);
        const right = x(Math.max(start + 1, end));
        cheapBand = `<rect class="cheap-band" x="${left}" y="${margin.top}" width="${right - left}" height="${plotHeight}" />`;
      }
    }

    const points = periods
      .map((row, index) => {
        const value = forecast[index];
        const local = new Intl.DateTimeFormat(undefined, {
          weekday: "short",
          hour: "2-digit",
          minute: "2-digit",
        }).format(new Date(row.start_utc));
        const baselineText = baseline[index] == null ? "unavailable" : `${baseline[index].toFixed(2)}p`;
        return `<circle class="hit ${value <= 0 ? "negative" : ""}" cx="${x(index)}" cy="${y(value)}" r="${value <= 0 ? 4 : 7}">
          <title>${this.escape(local)}: ${value.toFixed(2)}p/kWh; baseline ${baselineText}</title>
        </circle>`;
      })
      .join("");

    this._root.innerHTML = `
      <style>
        ha-card { padding: 18px 18px 12px; overflow: hidden; }
        .heading { font-size: 1.2rem; font-weight: 500; margin: 0 0 4px; }
        .subheading { color: var(--secondary-text-color); margin-bottom: 8px; font-size: .9rem; }
        .chart { display: block; width: 100%; height: auto; }
        .grid { stroke: var(--divider-color, #ddd); stroke-width: 1; }
        .axis { fill: var(--secondary-text-color); font: 12px sans-serif; }
        .y-axis { font-size: 11px; }
        .forecast { fill: none; stroke: var(--primary-color, #03a9f4); stroke-width: 3; stroke-linejoin: round; }
        .baseline { fill: none; stroke: var(--secondary-text-color, #777); stroke-width: 2; stroke-dasharray: 7 6; opacity: .75; }
        .zero { stroke: var(--error-color, #db4437); stroke-width: 1; opacity: .6; }
        .cheap-band { fill: var(--success-color, #43a047); opacity: .12; }
        .hit { fill: transparent; stroke: transparent; }
        .hit.negative { fill: var(--error-color, #db4437); stroke: white; stroke-width: 1.5; }
        .legend { display: flex; gap: 18px; flex-wrap: wrap; margin: 4px 0 0 40px; color: var(--secondary-text-color); font-size: .85rem; }
        .key::before { content: ""; display: inline-block; width: 22px; margin-right: 6px; vertical-align: middle; border-top: 3px solid var(--primary-color); }
        .key.baseline-key::before { border-top: 2px dashed var(--secondary-text-color); }
        .key.cheap-key::before { height: 10px; border: 0; background: var(--success-color, #43a047); opacity: .25; }
        .missing { padding: 24px; color: var(--error-color); }
      </style>
      <ha-card>
        <div class="heading">${this.escape(this.config.title)}</div>
        <div class="subheading">Forecast versus the matching half-hours from the previous 14 days</div>
        <svg class="chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Electricity price forecast chart">
          ${grid}
          ${cheapBand}
          ${minimum < 0 && maximum > 0 ? `<line class="zero" x1="${margin.left}" x2="${width - margin.right}" y1="${y(0)}" y2="${y(0)}" />` : ""}
          <path class="baseline" d="${pathFor(baseline)}" />
          <path class="forecast" d="${pathFor(forecast)}" />
          ${points}
          ${labels}
        </svg>
        <div class="legend">
          <span class="key">Forecast</span>
          <span class="key baseline-key">14-day baseline</span>
          <span class="key cheap-key">Cheapest 2 hours</span>
        </div>
      </ha-card>`;
  }
}

customElements.define("octopus-intelligence-chart", OctopusIntelligenceChart);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "octopus-intelligence-chart",
  name: "Octopus Intelligence Chart",
  description: "Forecast Agile prices compared with their recent baseline.",
  preview: true,
});
