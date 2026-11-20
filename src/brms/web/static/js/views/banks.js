// Bank list: demo banks and banks built from bank files or Call Reports.

import { api } from "../api.js";
import { date, money, pct } from "../format.js";
import { chip, dataTable, errorBox, h, loading, panel } from "../ui.js";

const SOURCE = { demo: "Demo", bank_file: "Bank file", call_report: "Call Report" };

export async function render(main, ctx) {
  ctx.setTitle("Banks");
  const body = h("div", {}, loading("Loading banks"));
  main.append(
    h("div", { class: "page-head" }, h("h1", {}, "Banks"),
      h("span", { class: "meta" }, "Balance sheets to run through rate scenarios"),
      h("div", { class: "actions" }, h("a", { class: "btn primary", href: "#/import" }, "Import a bank"))),
    panel("All banks", body, { flush: true }),
  );

  let timer = null;
  const sortState = {};
  async function refresh() {
    try {
      const banks = await api.banks();
      if (!ctx.alive()) return;
      body.replaceChildren(dataTable([
        { key: "name", label: "Bank", name: true },
        { key: "source", label: "Source", render: (b) => h("span", { class: "tag" }, SOURCE[b.source] || b.source) },
        { key: "start_date", label: "Start", render: (b) => date(b.start_date) },
        { key: "end_date", label: "Data to", render: (b) => date(b.end_date) },
        { key: "positions", label: "Positions", num: true },
        { key: "total_assets", label: "Total assets", num: true, render: (b) => money(b.total_assets, { unit: b.unit }) },
        { key: "total_equity", label: "Equity", num: true, render: (b) => money(b.total_equity, { unit: b.unit }) },
        { key: "leverage", label: "Equity / assets", num: true,
          sort: (b) => (b.total_assets ? b.total_equity / b.total_assets : null),
          render: (b) => (b.total_assets ? pct(b.total_equity / b.total_assets) : "–") },
        { key: "status", label: "Status", render: (b) => (b.status === "failed"
          ? h("span", { title: b.error || "" }, chip("failed")) : chip(b.status)) },
      ], banks, {
        state: sortState,
        onRow: (b) => { location.hash = `#/banks/${encodeURIComponent(b.id)}`; },
        empty: "No banks yet",
      }));
      const pending = banks.some((b) => b.status === "pending" || b.status === "building");
      timer = pending ? setTimeout(refresh, 1500) : null;
    } catch (error) {
      if (ctx.alive()) body.replaceChildren(errorBox(error));
    }
  }
  await refresh();
  return () => clearTimeout(timer);
}
