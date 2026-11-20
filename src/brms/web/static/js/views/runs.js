// All runs, newest first; pick several to compare.

import { api } from "../api.js";
import { datetime, money, pct, signClass } from "../format.js";
import { chip, dataTable, errorBox, h, loading, panel } from "../ui.js";

export async function render(main, ctx) {
  ctx.setTitle("Runs");
  const picked = new Set();
  const compare = h("a", { class: "btn primary", href: "#/compare", "aria-disabled": "true" }, "Compare selected");
  const body = h("div", {}, loading("Loading runs"));
  main.append(
    h("div", { class: "page-head" }, h("h1", {}, "Runs"),
      h("span", { class: "meta" }, "Select runs of the same bank to compare them"),
      h("div", { class: "actions" }, compare)),
    panel("All runs", body, { flush: true }),
  );

  function syncCompare() {
    compare.href = `#/compare?runs=${[...picked].join(",")}`;
    compare.textContent = picked.size ? `Compare ${picked.size} selected` : "Compare selected";
    compare.style.pointerEvents = picked.size >= 1 ? "" : "none";
    compare.style.opacity = picked.size >= 1 ? "" : ".5";
  }
  syncCompare();

  let timer = null;
  const sortState = {};
  async function refresh() {
    try {
      const runs = await api.runs();
      if (!ctx.alive()) return;
      const s = (r) => r.summary || {};
      body.replaceChildren(dataTable([
        { key: "pick", label: "", sort: (r) => (picked.has(r.id) ? 1 : 0), render: (r) => {
          const box = h("input", { type: "checkbox", "aria-label": `Select run ${r.id}`, checked: picked.has(r.id),
            disabled: r.status !== "done" });
          box.addEventListener("click", (e) => {
            e.stopPropagation();
            if (box.checked) picked.add(r.id); else picked.delete(r.id);
            syncCompare();
          });
          return box;
        } },
        { key: "created", label: "Started", render: (r) => datetime(r.created) },
        { key: "bank_name", label: "Bank", name: true },
        { key: "scenario", label: "Scenario", name: true, sort: (r) => r.spec.description,
          render: (r) => (r.label ? `${r.label} · ${r.spec.description}` : r.spec.description) },
        { key: "months", label: "Months", num: true, sort: (r) => r.spec.months, render: (r) => r.spec.months },
        { key: "status", label: "Status", render: (r) => (r.status === "failed"
          ? h("span", { title: r.error || "" }, chip("failed")) : chip(r.status)) },
        { key: "cet1_end", label: "CET1 end", num: true, sort: (r) => s(r).cet1_ratio_end,
          render: (r) => pct(s(r).cet1_ratio_end) },
        { key: "cet1_min", label: "CET1 min", num: true, sort: (r) => s(r).cet1_ratio_min,
          render: (r) => pct(s(r).cet1_ratio_min) },
        { key: "eve", label: "Worst ΔEVE/T1", num: true, sort: (r) => s(r).worst_delta_eve_to_tier1,
          render: (r) => pct(s(r).worst_delta_eve_to_tier1), cls: (r) => signClass(s(r).worst_delta_eve_to_tier1) },
        { key: "ni", label: "Net income", num: true, sort: (r) => s(r).net_income,
          render: (r) => money(s(r).net_income, { unit: r.unit }), cls: (r) => signClass(s(r).net_income) },
        { key: "htm", label: "HTM unrealised", num: true, sort: (r) => s(r).unrealised_end?.htm,
          render: (r) => money(s(r).unrealised_end?.htm, { unit: r.unit }), cls: (r) => signClass(s(r).unrealised_end?.htm) },
        { key: "afs", label: "AFS unrealised", num: true, sort: (r) => s(r).unrealised_end?.afs,
          render: (r) => money(s(r).unrealised_end?.afs, { unit: r.unit }), cls: (r) => signClass(s(r).unrealised_end?.afs) },
      ], runs, {
        sortKey: "created",
        state: sortState,
        onRow: (r) => { location.hash = `#/runs/${encodeURIComponent(r.id)}`; },
        empty: "No runs yet. Open a bank and run a scenario.",
      }));
      const active = runs.some((r) => r.status === "queued" || r.status === "running");
      timer = active ? setTimeout(refresh, 2000) : null;
    } catch (error) {
      if (ctx.alive()) body.replaceChildren(errorBox(error));
    }
  }
  await refresh();
  return () => clearTimeout(timer);
}
