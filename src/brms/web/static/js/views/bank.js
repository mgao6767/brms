// One bank: its balance sheet and positions at the start, and the scenario launcher.

import { api } from "../api.js";
import { BASIS, date, datetime, full, humanType, money, pct, setUnit, signAt, signClass, unitNote } from "../format.js";
import { chip, dataTable, errorBox, h, kpi, loading, panel, toast } from "../ui.js";

const KEY_TENORS = [["3M", 0.25], ["1Y", 1], ["2Y", 2], ["5Y", 5], ["10Y", 10], ["30Y", 30]];

export async function render(main, ctx) {
  const [id] = ctx.params;
  main.append(loading("Loading bank"));
  let timer = null;

  async function refresh() {
    let bank;
    try {
      bank = await api.bank(id);
    } catch (error) {
      if (ctx.alive()) main.replaceChildren(errorBox(error));
      return;
    }
    if (!ctx.alive()) return;
    ctx.setTitle(bank.name);
    setUnit(bank.unit);
    if (bank.status !== "ready") {
      main.replaceChildren(head(bank), pendingPanel(bank));
      if (bank.status !== "failed") timer = setTimeout(refresh, 1500);
      return;
    }
    const scenarios = await api.scenarios();
    const runs = (await api.runs()).filter((r) => r.bank_id === bank.id);
    if (!ctx.alive()) return;
    main.replaceChildren(head(bank), kpis(bank),
      h("div", { class: "grid cols-3" },
        h("div", { class: "span-2 grid" }, balanceSheet(bank), positions(bank)),
        h("div", { class: "grid", style: { alignContent: "start" } }, launcher(bank, scenarios), recentRuns(runs))));
  }

  await refresh();
  return () => clearTimeout(timer);
}

function head(bank) {
  const del = bank.source !== "demo" ? h("button", { class: "btn ghost danger", type: "button" }, "Delete") : null;
  del?.addEventListener("click", async () => {
    if (!window.confirm(`Delete ${bank.name}? Its runs are kept.`)) return;
    try {
      await api.deleteBank(bank.id);
      toast(`Deleted ${bank.name}`);
      location.hash = "#/banks";
    } catch (error) { toast(error.message, { error: true }); }
  });
  return h("div", { class: "page-head" },
    h("span", { class: "crumbs" }, h("a", { href: "#/banks" }, "Banks"), " / "),
    h("h1", {}, bank.name),
    h("span", { class: "meta" }, bank.source === "call_report" ? `Call Report, FDIC #${bank.cert}` : ""),
    h("div", { class: "actions" }, del));
}

function pendingPanel(bank) {
  if (bank.status === "failed") {
    return panel("Build failed", h("div", { class: "form" }, errorBox(bank.error || "Unknown error"),
      h("div", {}, h("a", { class: "btn", href: "#/import" }, "Back to import"))));
  }
  return panel("Preparing", loading(bank.source === "demo" ? "Summarising the bank" : "Building the bank"));
}

function kpis(bank) {
  const sheet = bank.summary.balance_sheet;
  const equityRatio = sheet.total_assets ? sheet.total_equity / sheet.total_assets : null;
  return h("div", { class: "kpis" },
    kpi("Total assets", money(sheet.total_assets), { sub: full(sheet.total_assets, 0) }),
    kpi("Total liabilities", money(sheet.total_liabilities)),
    kpi("Equity", money(sheet.total_equity), { sub: `${pct(equityRatio)} of assets` }),
    kpi("Positions", String(bank.summary.positions.filter((p) => p.side === "LONG" && p.basis !== "NA").length),
      { sub: "securities and loans" }),
    kpi("Start date", date(bank.start_date), { sub: `data to ${date(bank.end_date)}` }),
    kpi("AOCI filter", bank.summary.regulatory.aoci_filter ? "On" : "Off",
      { sub: bank.summary.regulatory.aoci_filter ? "unrealised AFS excluded from CET1" : "AOCI counts in CET1" }));
}

function balanceSheet(bank) {
  const sheet = bank.summary.balance_sheet;
  const total = sheet.total_assets || 1;
  const rows = [];
  for (const [section, label, key] of [["assets", "Assets", "total_assets"],
    ["liabilities", "Liabilities", "total_liabilities"], ["equity", "Equity", "total_equity"]]) {
    rows.push(h("tr", { class: "group" }, h("td", { colspan: "3" }, label)));
    for (const line of sheet[section].filter((l) => Math.abs(l.balance) > 0.005)) {
      rows.push(h("tr", {},
        h("td", { class: "indent" }, line.account),
        h("td", { style: { width: "34%" } }, h("div", { class: "bar" },
          h("i", { style: { width: `${Math.min(100, (Math.abs(line.balance) / total) * 100)}%`,
            background: section === "assets" ? "var(--s1)" : section === "liabilities" ? "var(--s2)" : "var(--s3)" } }))),
        h("td", { class: `num ${line.balance < 0 ? "down" : ""}` }, full(line.balance, 0))));
    }
    rows.push(h("tr", { class: "total" }, h("td", {}, `Total ${label.toLowerCase()}`), h("td"),
      h("td", { class: "num" }, full(sheet[key], 0))));
  }
  return panel("Balance sheet at start", h("div", { class: "table-wrap short" },
    h("table", { class: "data" }, h("tbody", {}, rows))), { flush: true, note: [date(previousDay(bank.start_date)), unitNote()].filter(Boolean).join(" \u00B7 ") });
}

function positions(bank) {
  const rows = bank.summary.positions.filter((p) => p.side === "LONG" && p.basis !== "NA").map((p) => ({
    ...p, unrealised: p.fair !== null && p.amortized !== null ? p.fair - p.amortized : null,
  }));
  return panel("Positions", dataTable([
    { key: "name", label: "Instrument", name: true },
    { key: "type", label: "Type", render: (p) => humanType(p.type) },
    { key: "basis", label: "Basis", render: (p) => BASIS[p.basis] || p.basis },
    { key: "maturity", label: "Maturity", render: (p) => date(p.maturity) },
    { key: "carrying", label: "Carrying value", num: true, render: (p) => full(p.carrying, 0) },
    { key: "fair", label: "Fair value", num: true, render: (p) => full(p.fair, 0) },
    { key: "unrealised", label: "Unrealised", num: true, render: (p) => full(p.unrealised, 0),
      cls: (p) => signAt(p.unrealised) },
  ], rows, { sortKey: "carrying", short: true }), { flush: true, note: [`${rows.length} long positions`, unitNote()].filter(Boolean).join(" \u00B7 ") });
}

function launcher(bank, scenarios) {
  const status = h("div");
  const kind = h("select", { id: "sc-kind" },
    h("option", { value: "historical" }, "Historical rates"),
    h("optgroup", { label: "Basel IRRBB shocks" }, scenarios.basel.map((s) => h("option", { value: `basel:${s.name}` }, s.label))),
    h("option", { value: "parallel" }, "Parallel shift…"),
    h("option", { value: "key_rate" }, "Key-rate shift…"));
  const bp = h("input", { type: "number", id: "sc-bp", value: "200", step: "25", min: "-1000", max: "1000" });
  const keyInputs = KEY_TENORS.map(([label]) => h("input", { type: "number", step: "25", value: "100",
    id: `kr-${label}`, "aria-label": `${label} shift in basis points` }));
  const months = h("input", { type: "number", id: "sc-months", value: "12", min: "1", max: String(scenarios.max_months) });
  const ramp = h("input", { type: "number", id: "sc-ramp", value: "0", min: "0", max: "3650", step: "30" });
  const aoci = h("select", { id: "sc-aoci" }, h("option", { value: "" }, "As the bank (" +
    (bank.summary.regulatory.aoci_filter ? "on" : "off") + ")"), h("option", { value: "on" }, "On"),
  h("option", { value: "off" }, "Off"));
  const reinvest = h("input", { type: "checkbox", id: "sc-reinvest" });
  const label = h("input", { type: "text", id: "sc-label", maxlength: "120", placeholder: "Optional" });
  const bpField = h("div", { class: "field" }, h("label", { for: "sc-bp" }, "Shift (bp, all maturities)"), bp);
  const keyField = h("div", { class: "field" }, h("span", { class: "label" }, "Shift by maturity (bp)"),
    h("div", { class: "keyrates" }, KEY_TENORS.map(([l], i) => h("div", { class: "field" },
      h("label", { for: `kr-${l}` }, l), keyInputs[i]))));
  const rampField = h("div", { class: "field" }, h("label", { for: "sc-ramp" }, "Phase in over (days)"), ramp);

  function sync() {
    bpField.hidden = kind.value !== "parallel";
    keyField.hidden = kind.value !== "key_rate";
    rampField.hidden = kind.value === "historical";
  }
  kind.addEventListener("change", sync);
  sync();

  function spec() {
    const base = { bank_id: bank.id, months: Number(months.value), reinvest: reinvest.checked,
      label: label.value.trim() || undefined };
    if (aoci.value) base.aoci_filter = aoci.value === "on";
    if (kind.value === "historical") return { ...base, kind: "historical" };
    base.ramp_days = Number(ramp.value) || 0;
    if (kind.value.startsWith("basel:")) return { ...base, kind: "basel", name: kind.value.slice(6) };
    if (kind.value === "parallel") return { ...base, kind: "parallel", bp: Number(bp.value) };
    return { ...base, kind: "key_rate", points: KEY_TENORS.map(([, t], i) => [t, Number(keyInputs[i].value) || 0]) };
  }

  const submit = h("button", { class: "btn primary", type: "submit" }, "Run scenario");
  const basel = h("button", { class: "btn", type: "button", title: "Run the six Basel shocks and historical rates, then compare" },
    "Run all Basel shocks");
  const form = h("form", { class: "form" },
    h("div", { class: "field" }, h("label", { for: "sc-kind" }, "Scenario"), kind),
    bpField, keyField,
    h("div", { class: "row" },
      h("div", { class: "field" }, h("label", { for: "sc-months" }, "Horizon (months)"), months), rampField),
    h("div", { class: "row" },
      h("div", { class: "field" }, h("label", { for: "sc-aoci" }, "AOCI filter"), aoci)),
    h("label", { class: "check" }, reinvest, "Roll maturing bonds into new par bonds"),
    h("div", { class: "field" }, h("label", { for: "sc-label" }, "Label"), label),
    h("div", { class: "row" }, submit, basel), status);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    submit.disabled = true;
    status.replaceChildren();
    try {
      const created = await api.createRun(spec());
      location.hash = `#/runs/${encodeURIComponent(created.id)}`;
    } catch (error) {
      status.replaceChildren(errorBox(error));
    } finally { submit.disabled = false; }
  });

  basel.addEventListener("click", async () => {
    basel.disabled = true;
    status.replaceChildren();
    const common = { bank_id: bank.id, months: Number(months.value), reinvest: reinvest.checked,
      ramp_days: Number(ramp.value) || 0 };
    if (aoci.value) common.aoci_filter = aoci.value === "on";
    try {
      const ids = [];
      ids.push((await api.createRun({ ...common, kind: "historical", ramp_days: 0 })).id);
      for (const s of scenarios.basel) ids.push((await api.createRun({ ...common, kind: "basel", name: s.name })).id);
      toast(`Started ${ids.length} runs`);
      location.hash = `#/compare?runs=${ids.join(",")}`;
    } catch (error) {
      status.replaceChildren(errorBox(error));
    } finally { basel.disabled = false; }
  });

  return panel("Run a scenario", form);
}

function recentRuns(runs) {
  return panel("Runs of this bank", dataTable([
    { key: "created", label: "Started", render: (r) => datetime(r.created) },
    { key: "scenario", label: "Scenario", name: true, sort: (r) => r.spec.description,
      render: (r) => r.label || r.spec.description },
    { key: "status", label: "", render: (r) => chip(r.status) },
  ], runs, { sortKey: "created", onRow: (r) => { location.hash = `#/runs/${r.id}`; }, empty: "No runs yet", short: true }),
  { flush: true });
}

function previousDay(text) {
  const d = new Date(`${text}T00:00:00`);
  d.setDate(d.getDate() - 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
