// One run: headline figures, charts over the horizon, and any day's positions, statements and journal.

import { api } from "../api.js";
import { chartBox, lineChart, setMarker } from "../charts.js";
import { BASIS, GROUP, date, full, humanType, last, money, pct, setUnit, signAt, signClass, unitNote, years } from "../format.js";
import { chip, dataTable, errorBox, h, kpi, loading, panel, seg, toast } from "../ui.js";

const RATE_TENORS = [["3 Mo", "3M"], ["2 Yr", "2Y"], ["10 Yr", "10Y"]];
const MAX_STACK = 6;

export async function render(main, ctx) {
  const [id] = ctx.params;
  main.append(loading("Loading run"));
  let timer = null;
  let disposeDay = null;

  async function refresh() {
    let data;
    try {
      data = await api.run(id);
    } catch (error) {
      if (ctx.alive()) main.replaceChildren(errorBox(error));
      return;
    }
    if (!ctx.alive()) return;
    const { meta } = data;
    ctx.setTitle(meta.label || meta.spec.description);
    setUnit(meta.unit);
    if (meta.status === "queued" || meta.status === "running") {
      main.replaceChildren(head(meta), panel("In progress", h("div", { class: "form" },
        h("div", {}, chip(meta.status)),
        loading(`Running ${meta.spec.months} months of ${meta.spec.description.toLowerCase()} for ${meta.bank_name}`))));
      timer = setTimeout(refresh, 1500);
      return;
    }
    if (meta.status === "failed") {
      main.replaceChildren(head(meta), panel("Run failed", errorBox(meta.error || "Unknown error")));
      return;
    }
    const view = dashboard(data);
    main.replaceChildren(head(meta, true), view.node);
    disposeDay = view.start();
  }

  await refresh();
  return () => { clearTimeout(timer); if (disposeDay) disposeDay(); };
}

function head(meta, done = false) {
  const actions = [];
  if (done) actions.push(h("a", { class: "btn", href: api.metricsCsvUrl(meta.id), download: "" }, "Metrics CSV"));
  actions.push(h("a", { class: "btn", href: `#/banks/${encodeURIComponent(meta.bank_id)}` }, "Run another"));
  if (meta.status === "done" || meta.status === "failed") {
    const del = h("button", { class: "btn ghost danger", type: "button" }, "Delete");
    del.addEventListener("click", async () => {
      if (!window.confirm("Delete this run?")) return;
      try { await api.deleteRun(meta.id); toast("Run deleted"); location.hash = "#/runs"; } catch (error) {
        toast(error.message, { error: true });
      }
    });
    actions.push(del);
  }
  const spec = meta.spec;
  const details = [`${spec.months} months`, spec.reinvest ? "maturities reinvested" : null,
    spec.aoci_filter === undefined ? null : `AOCI filter ${spec.aoci_filter ? "on" : "off"}`].filter(Boolean).join(" · ");
  return h("div", { class: "page-head" },
    h("span", { class: "crumbs" }, h("a", { href: "#/runs" }, "Runs"), " / ",
      h("a", { href: `#/banks/${encodeURIComponent(meta.bank_id)}` }, meta.bank_name), " / "),
    h("h1", {}, meta.label ? `${meta.label}` : spec.description),
    h("span", { class: "meta" }, meta.label ? `${spec.description} · ${details}` : details),
    h("div", { class: "actions" }, actions));
}

function dashboard(data) {
  const { summary, dates, metrics, unrealised, composition, yields, positions } = data;
  const charts = [];

  function chartPanel(title, build, { note, cls = "" } = {}) {
    const box = h("div", {}, chartBox(cls));
    const node = panel(title, box, { note, cls: "chart-panel" });
    charts.push({ box, build });
    return node;
  }

  const m = (name) => metrics[name] || [];
  const same = (a, b) => a.length === b.length && a.every((v, i) => (v === null && b[i] === null)
    || (v !== null && b[i] !== null && Math.abs(v - b[i]) < 1e-12));
  const available = (values) => values.some((v) => v !== null && v !== undefined);
  const unavailable = (box, text) => box.replaceChildren(h("div", { class: "empty" }, text));

  const start = (name) => m(name).find((v) => v !== null && v !== undefined) ?? null;
  const cet1End = summary.cet1_ratio_end;
  const cet1Start = start("CET1_RATIO");
  const tiles = h("div", { class: "kpis" },
    kpi("CET1 ratio, end", pct(cet1End), { sub: cet1Start !== null && cet1End !== null
      ? `${pct(cet1End - cet1Start, { sign: true })} since start` : "", cls: "" }),
    kpi("CET1 ratio, low", pct(summary.cet1_ratio_min), { sub: summary.cet1_ratio_min_date ? `on ${date(summary.cet1_ratio_min_date)}` : "" }),
    kpi("Total capital ratio", pct(last(m("TOTAL_CAPITAL_RATIO"))), { sub: `Tier 1 ${pct(last(m("TIER1_RATIO")))}` }),
    kpi("Leverage ratio", pct(last(m("LEVERAGE_RATIO")))),
    kpi("Worst ΔEVE / Tier 1", pct(summary.worst_delta_eve_to_tier1), { cls: signClass(summary.worst_delta_eve_to_tier1),
      title: "Change in economic value of equity under the worst of the six Basel shocks, on the last day" }),
    kpi("Net income", money(summary.net_income, { sign: true }), { cls: signClass(summary.net_income),
      sub: `${data.meta.spec.months} months to ${date(dates[dates.length - 1])}` }),
    ...["htm", "afs"].filter((b) => summary.unrealised_end?.[b] !== undefined).map((b) =>
      kpi(`${b.toUpperCase()} unrealised`, money(summary.unrealised_end[b], { sign: true }),
        { cls: signClass(summary.unrealised_end[b]), sub: "vs amortised cost, end" })),
  );

  const rateCharts = h("div", { class: "grid cols-3" },
    chartPanel("Treasury yields", (box) => lineChart(box, {
      dates: yields.dates, format: (v) => `${v.toFixed(2)}%`,
      series: RATE_TENORS.filter(([t]) => yields.values[t]).map(([t, label]) => ({ name: label, values: yields.values[t] })),
    }), { note: "CMT, % (the scenario's path)" }),
    chartPanel("Capital ratios", (box) => lineChart(box, {
      dates, format: (v) => pct(v), axisFormat: (v) => pct(v, { digits: 0 }),
      series: [["CET1_RATIO", "CET1"], ["TOTAL_CAPITAL_RATIO", "Total capital"], ["LEVERAGE_RATIO", "Leverage"]]
        .filter(([k]) => available(m(k)) && !(k === "TOTAL_CAPITAL_RATIO" && same(m(k), m("CET1_RATIO"))))
        .map(([k, name]) => ({ name, values: m(k) })),
    }), { note: same(m("TOTAL_CAPITAL_RATIO"), m("CET1_RATIO")) ? "% of RWA (total capital = CET1); leverage %"
      : "% of RWA; leverage % of exposure" }),
    chartPanel("Unrealised gains and losses", (box) => {
      const books = Object.keys(unrealised);
      if (!books.length) return unavailable(box, "No securities or loans with a fair value");
      return lineChart(box, { dates, zero: true, format: (v) => money(v, { sign: true }),
        series: books.map((b) => ({ name: GROUP[b] || b, values: unrealised[b] })) });
    }, { note: "fair value less amortised cost" }),
    chartPanel("Assets", (box) => lineChart(box, { dates, stacked: true, format: (v) => money(v),
      series: stackSeries(composition.assets) }), { note: "balance sheet, stacked" }),
    chartPanel("Worst ΔEVE / Tier 1", (box) => (available(m("DELTA_EVE_WORST_TO_TIER1"))
      ? lineChart(box, { dates, zero: true, format: (v) => pct(v, { sign: true }),
        series: [{ name: "Worst ΔEVE / Tier 1", values: m("DELTA_EVE_WORST_TO_TIER1") }] })
      : unavailable(box, "Not available")), { note: "six Basel shocks, banking book" }),
    chartPanel("Asset duration", (box) => (available(m("ASSET_DURATION"))
      ? lineChart(box, { dates, format: (v) => years(v), series: [{ name: "Duration", values: m("ASSET_DURATION") }] })
      : unavailable(box, "Not available")), { note: "effective, years" }),
    chartPanel("NII sensitivity, 12 months", (box) => (available(m("NII_SENSITIVITY_UP"))
      ? lineChart(box, { dates, zero: true, format: (v) => money(v, { sign: true }),
        series: [{ name: "+200bp", values: m("NII_SENSITIVITY_UP") }, { name: "−200bp", values: m("NII_SENSITIVITY_DOWN") }] })
      : unavailable(box, "Not available")), { note: "repricing gap" }),
    chartPanel("Net interest margin", (box) => (available(m("NET_INTEREST_MARGIN"))
      ? lineChart(box, { dates, format: (v) => pct(v), series: [{ name: "NIM", values: m("NET_INTEREST_MARGIN") }] })
      : unavailable(box, "Needs 30 days of history")), { note: "trailing, annualised" }),
    chartPanel("Credit RWA", (box) => (available(m("CREDIT_RWA"))
      ? lineChart(box, { dates, format: (v) => money(v), series: [{ name: "Credit RWA", values: m("CREDIT_RWA") }] })
      : unavailable(box, "Not available")), { note: "standardised approach" }),
  );

  // Day detail: positions at the end, statements and journal on a chosen day.
  let day = dates[dates.length - 1];
  let mode = "statements";
  const scrubDate = h("span", { class: "date" }, day);
  const slider = h("input", { type: "range", min: "0", max: String(dates.length - 1), value: String(dates.length - 1),
    "aria-label": "Day" });
  const prev = h("button", { class: "btn", type: "button", "aria-label": "Previous day" }, "‹");
  const next = h("button", { class: "btn", type: "button", "aria-label": "Next day" }, "›");
  const filter = h("input", { type: "text", placeholder: "Filter accounts or descriptions", "aria-label": "Filter journal",
    style: { maxWidth: "240px" } });
  const dayBody = h("div", {}, loading("Loading day"));
  const scrub = h("div", { class: "scrub" }, prev, slider, next, scrubDate, filter);
  let dayData = null;
  let pending = null;
  let token = 0;

  async function loadDay() {
    const mine = ++token;
    try {
      const result = await api.day(data.meta.id, day);
      if (mine !== token) return;
      dayData = result;
      drawDay();
    } catch (error) {
      if (mine === token) dayBody.replaceChildren(errorBox(error));
    }
  }

  function setDay(index, { immediate = false } = {}) {
    const i = Math.max(0, Math.min(dates.length - 1, index));
    day = dates[i];
    slider.value = String(i);
    scrubDate.textContent = day;
    for (const chart of liveCharts) setMarker(chart, day);
    clearTimeout(pending);
    pending = setTimeout(loadDay, immediate ? 0 : 160);
  }
  slider.addEventListener("input", () => setDay(Number(slider.value)));
  prev.addEventListener("click", () => setDay(dates.indexOf(day) - 1, { immediate: true }));
  next.addEventListener("click", () => setDay(dates.indexOf(day) + 1, { immediate: true }));
  filter.addEventListener("input", () => drawDay());

  function drawDay() {
    filter.hidden = mode !== "journal";
    scrub.hidden = mode === "positions";
    if (mode === "positions") { dayBody.replaceChildren(positionsTable(positions)); return; }
    if (!dayData) { dayBody.replaceChildren(loading("Loading day")); return; }
    dayBody.replaceChildren(mode === "statements" ? statements(dayData) : journal(dayData, filter.value.trim().toLowerCase()));
  }

  const tabs = seg([["statements", "Statements"], ["journal", "Journal"], ["positions", "Positions at end"]], mode, (v) => {
    mode = v;
    drawDay();
  });
  const detail = panel("Books", h("div", {}, scrub, dayBody), { flush: true, tools: tabs,
    note: ["drag the slider or click a chart to pick a day", unitNote()].filter(Boolean).join(" \u00B7 ") });

  const liveCharts = [];
  const node = h("div", {}, tiles, rateCharts, h("div", { style: { height: "6px" } }), detail);

  return {
    node,
    start() {
      for (const { box, build } of charts) {
        const chart = build(box);
        if (!chart) continue;
        liveCharts.push(chart);
        chart.getZr().on("click", (event) => {
          const point = chart.convertFromPixel({ xAxisIndex: 0 }, [event.offsetX, event.offsetY]);
          const index = Array.isArray(point) ? point[0] : point;
          const label = chart.getOption().xAxis[0].data[Math.round(index)];
          const at = dates.indexOf(label);
          if (at >= 0) setDay(at, { immediate: true });
        });
        setMarker(chart, day);
      }
      loadDay();
      return () => clearTimeout(pending);
    },
  };
}

function stackSeries(assets) {
  const entries = Object.entries(assets).map(([name, values]) => ({ name, values,
    size: Math.max(...values.map((v) => Math.abs(v ?? 0))) })).sort((a, b) => b.size - a.size);
  if (entries.length <= MAX_STACK) return entries;
  const top = entries.slice(0, MAX_STACK - 1);
  const rest = entries.slice(MAX_STACK - 1);
  const other = rest[0].values.map((_, i) => rest.reduce((sum, e) => sum + (e.values[i] ?? 0), 0));
  return [...top, { name: "Other", values: other, color: "#5b6470" }];
}

function positionsTable(positions) {
  const rows = positions.filter((p) => p.side === "LONG" && p.basis !== "NA");
  return dataTable([
    { key: "name", label: "Instrument", name: true },
    { key: "type", label: "Type", render: (p) => humanType(p.type) },
    { key: "group", label: "Book", render: (p) => GROUP[p.group] || BASIS[p.basis] || p.basis },
    { key: "status", label: "Status", render: (p) => (p.status === "OPEN" ? "Open" : "Closed") },
    { key: "carrying", label: "Carrying value", num: true, render: (p) => full(p.carrying, 0) },
    { key: "amortized", label: "Amortised cost", num: true, render: (p) => full(p.amortized, 0) },
    { key: "fair", label: "Fair value", num: true, render: (p) => full(p.fair, 0) },
    { key: "unrealised", label: "Unrealised", num: true, render: (p) => full(p.unrealised, 0), cls: (p) => signAt(p.unrealised) },
    { key: "as_of", label: "Last valued", render: (p) => date(p.as_of) },
  ], rows, { sortKey: "unrealised", sortDir: "asc" });
}

function statementTable(sections, totals) {
  const rows = [];
  for (const [label, lines, totalLabel, total] of sections) {
    rows.push(h("tr", { class: "group" }, h("td", { colspan: "2" }, label)));
    for (const line of lines.filter((l) => Math.abs(l.balance) > 0.005)) {
      rows.push(h("tr", {}, h("td", { class: "indent" }, line.account),
        h("td", { class: `num ${line.balance < 0 ? "down" : ""}` }, full(line.balance))));
    }
    if (totalLabel) rows.push(h("tr", { class: "total" }, h("td", {}, totalLabel), h("td", { class: "num" }, full(total))));
  }
  for (const [label, value, cls] of totals) {
    rows.push(h("tr", { class: "total" }, h("td", {}, label), h("td", { class: `num ${cls || ""}` }, full(value))));
  }
  return h("table", { class: "data" }, h("tbody", {}, rows));
}

function statements(d) {
  const t = d.totals;
  const note = d.statement_date !== d.date ? ` (last market day ${d.statement_date})` : "";
  return h("div", { class: "grid cols-2", style: { padding: "6px" } },
    panel(`Balance sheet${note}`, statementTable([
      ["Assets", d.balance_sheet.assets, "Total assets", t.total_assets],
      ["Liabilities", d.balance_sheet.liabilities, "Total liabilities", t.total_liabilities],
      ["Equity", d.balance_sheet.equity, "Total equity", t.total_equity],
    ], [["Liabilities and equity", t.total_liabilities + t.total_equity]]), { flush: true, note: d.statement_date }),
    panel("Income statement since start", statementTable([
      ["Income", d.income_statement.income, "Total income", t.total_income],
      ["Expenses", d.income_statement.expenses, "Total expenses", t.total_expenses],
    ], [["Net income", t.net_income, signClass(t.net_income)]]), { flush: true, note: `to ${d.statement_date}` }));
}

function journal(d, query) {
  const matches = (e) => !query || e.description.toLowerCase().includes(query)
    || (e.instrument || "").toLowerCase().includes(query) || e.lines.some((l) => l.account.toLowerCase().includes(query));
  const entries = d.journal.filter(matches);
  if (!d.journal.length) return h("div", { class: "empty" }, `No entries on ${date(d.date)}`);
  if (!entries.length) return h("div", { class: "empty" }, "No entries match the filter");
  const amount = (value) => h("td", { class: "num", style: { width: "130px" } }, value ? full(value) : "");
  return h("div", { class: "table-wrap" },
    h("table", { class: "data" }, h("thead", {}, h("tr", {},
      h("th", {}, `${entries.length} of ${d.journal.length} entries on ${date(d.date)}`),
      h("th", { class: "num", style: { width: "130px" } }, "Debit"),
      h("th", { class: "num", style: { width: "130px" } }, "Credit")))),
    entries.map((e) => h("div", { class: "entry" },
      h("div", { class: "entry-head" }, h("span", { class: "tag mono" }, `#${e.entry}`),
        e.kind !== "NORMAL" ? h("span", { class: "tag" }, e.kind.toLowerCase()) : null,
        h("span", { class: "desc", title: e.description }, e.description),
        e.instrument ? h("span", { class: "muted desc", title: e.instrument }, `\u00B7 ${e.instrument}`) : null),
      h("table", {}, h("tbody", {}, e.lines.map((l) => h("tr", {},
        h("td", { class: l.credit ? "cr" : "" }, l.account), amount(l.debit), amount(l.credit))))))));
}
