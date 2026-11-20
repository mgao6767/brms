// Compare runs: the same measures overlaid, one line per run, and a summary table.

import { api } from "../api.js";
import { SERIES, chartBox, lineChart } from "../charts.js";
import { money, pct, signClass } from "../format.js";
import { chip, dataTable, errorBox, h, loading, panel } from "../ui.js";

const MAX_RUNS = SERIES.length;

export async function render(main, ctx) {
  const query = new URLSearchParams(ctx.params[0] || "");
  const ids = (query.get("runs") || "").split(",").map((s) => s.trim()).filter(Boolean);
  ctx.setTitle(ids.length ? `Compare ${ids.length} runs` : "Compare");
  if (!ids.length) {
    main.append(h("div", { class: "page-head" }, h("h1", {}, "Compare runs")),
      panel("Nothing selected", h("div", { class: "form" },
        h("div", {}, "Pick runs on the Runs page, or open a bank and use “Run all Basel shocks”."),
        h("div", {}, h("a", { class: "btn primary", href: "#/runs" }, "Go to runs")))));
    return null;
  }
  main.append(loading("Loading runs"));
  let timer = null;

  async function refresh() {
    let runs;
    try {
      runs = await Promise.all(ids.slice(0, MAX_RUNS).map((id) => api.run(id)));
    } catch (error) {
      if (ctx.alive()) main.replaceChildren(errorBox(error));
      return;
    }
    if (!ctx.alive()) return;
    const waiting = runs.filter((r) => r.meta.status === "queued" || r.meta.status === "running");
    const done = runs.filter((r) => r.meta.status === "done");
    const headNode = h("div", { class: "page-head" }, h("h1", {}, "Compare runs"),
      h("span", { class: "meta" }, [...new Set(runs.map((r) => r.meta.bank_name))].join(", ")),
      ids.length > MAX_RUNS ? h("span", { class: "meta" }, `showing the first ${MAX_RUNS}`) : null);
    if (waiting.length) {
      main.replaceChildren(headNode, panel("Waiting for runs", dataTable([
        { key: "name", label: "Run", name: true, render: (r) => r.meta.label || r.meta.spec.description },
        { key: "status", label: "Status", render: (r) => chip(r.meta.status) },
      ], runs, { onRow: (r) => { location.hash = `#/runs/${r.meta.id}`; } }), { flush: true,
        note: `${done.length} of ${runs.length} finished` }));
      timer = setTimeout(refresh, 2000);
      return;
    }
    if (!done.length) {
      main.replaceChildren(headNode, errorBox("None of these runs finished successfully"));
      return;
    }
    main.replaceChildren(headNode, ...view(done, runs.filter((r) => r.meta.status === "failed")));
  }

  await refresh();
  return () => clearTimeout(timer);
}

function name(run) {
  return run.meta.label || run.meta.spec.description;
}

function aligned(runs, pick) {
  const all = [...new Set(runs.flatMap((r) => r.dates))].sort();
  const series = runs.map((r, i) => {
    const values = pick(r);
    const byDate = new Map(r.dates.map((d, j) => [d, values ? values[j] : null]));
    return { name: name(r), values: all.map((d) => byDate.get(d) ?? null), color: SERIES[i] };
  });
  return { dates: all, series };
}

function view(runs, failed) {
  const sumBooks = (r) => {
    const books = Object.values(r.unrealised || {});
    if (!books.length) return null;
    // In currency: runs of banks reported in different units (Call Reports are in thousands) can be compared.
    const unit = r.meta.unit || 1;
    return r.dates.map((_, j) => books.reduce((acc, values) => (values[j] === null ? acc : (acc ?? 0) + values[j] * unit),
      null));
  };
  const specs = [
    ["CET1 ratio", (r) => r.metrics.CET1_RATIO, (v) => pct(v), "% of RWA"],
    ["Unrealised gains and losses", sumBooks, (v) => money(v, { sign: true }), "securities and loans, total", true],
    ["Worst ΔEVE / Tier 1", (r) => r.metrics.DELTA_EVE_WORST_TO_TIER1, (v) => pct(v, { sign: true }), "Basel shocks", true],
    ["Net interest margin", (r) => r.metrics.NET_INTEREST_MARGIN, (v) => pct(v), "trailing, annualised"],
  ];
  const panels = specs.map(([title, pick, format, note, zero]) => {
    const box = h("div", {}, chartBox("tall"));
    requestAnimationFrame(() => {
      if (!box.isConnected) return;
      const { dates, series } = aligned(runs, pick);
      if (!series.some((s) => s.values.some((v) => v !== null))) {
        box.replaceChildren(h("div", { class: "empty" }, "Not available"));
        return;
      }
      // Shock paths have every weekday, history skips holidays: join the gaps of the shared date axis.
      lineChart(box, { dates, series, format, zero, endLabels: false, connectNulls: true });
    });
    return panel(title, box, { note });
  });
  const rates = h("div", {}, chartBox());
  requestAnimationFrame(() => {
    if (!rates.isConnected) return;
    const all = [...new Set(runs.flatMap((r) => r.yields.dates))].sort();
    lineChart(rates, { dates: all, format: (v) => `${v.toFixed(2)}%`, endLabels: false, connectNulls: true,
      series: runs.map((r, i) => {
        const byDate = new Map(r.yields.dates.map((d, j) => [d, r.yields.values["10 Yr"]?.[j] ?? null]));
        return { name: name(r), values: all.map((d) => byDate.get(d) ?? null), color: SERIES[i] };
      }) });
  });

  const table = dataTable([
    { key: "name", label: "Run", name: true, sort: (r) => name(r), render: (r) => {
      const i = runs.indexOf(r);
      return h("span", {}, h("i", { style: { display: "inline-block", width: "10px", height: "2px", marginRight: "6px",
        verticalAlign: "middle", background: SERIES[i] } }), h("a", { href: `#/runs/${r.meta.id}` }, name(r)));
    } },
    { key: "cet1_end", label: "CET1 end", num: true, sort: (r) => r.summary.cet1_ratio_end, render: (r) => pct(r.summary.cet1_ratio_end) },
    { key: "cet1_min", label: "CET1 low", num: true, sort: (r) => r.summary.cet1_ratio_min, render: (r) => pct(r.summary.cet1_ratio_min) },
    { key: "eve", label: "Worst ΔEVE/T1", num: true, sort: (r) => r.summary.worst_delta_eve_to_tier1,
      render: (r) => pct(r.summary.worst_delta_eve_to_tier1), cls: (r) => signClass(r.summary.worst_delta_eve_to_tier1) },
    { key: "ni", label: "Net income", num: true, sort: (r) => r.summary.net_income,
      render: (r) => money(r.summary.net_income, { sign: true, unit: r.meta.unit }), cls: (r) => signClass(r.summary.net_income) },
    { key: "htm", label: "HTM unrealised", num: true, sort: (r) => r.summary.unrealised_end?.htm,
      render: (r) => money(r.summary.unrealised_end?.htm, { sign: true, unit: r.meta.unit }), cls: (r) => signClass(r.summary.unrealised_end?.htm) },
    { key: "afs", label: "AFS unrealised", num: true, sort: (r) => r.summary.unrealised_end?.afs,
      render: (r) => money(r.summary.unrealised_end?.afs, { sign: true, unit: r.meta.unit }), cls: (r) => signClass(r.summary.unrealised_end?.afs) },
    { key: "assets", label: "Total assets, end", num: true, sort: (r) => r.summary.total_assets_end,
      render: (r) => money(r.summary.total_assets_end, { unit: r.meta.unit }) },
  ], runs, { sortKey: "cet1_min", sortDir: "asc" });

  return [
    failed.length ? h("div", { class: "error", style: { marginBottom: "6px" } },
      `${failed.length} run(s) failed and are left out: ${failed.map((r) => name(r)).join(", ")}`) : null,
    panel("Summary", table, { flush: true, note: "sorted by the lowest CET1 ratio" }),
    h("div", { style: { height: "6px" } }),
    h("div", { class: "grid cols-2" }, panels, panel("10-year Treasury yield", rates, { note: "%" })),
  ].filter(Boolean);
}
