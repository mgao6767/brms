// Import a bank: from a US Call Report (FDIC) or from a bank file (JSON).

import { api } from "../api.js";
import { errorBox, h, panel, toast } from "../ui.js";

const EXAMPLE = {
  name: "Example Bank",
  as_of: "2021-12-31",
  regulatory: { aoci_filter: true },
  cash: 1500000,
  deposits: [
    { id: "dda", name: "Demand deposits", balance: 6000000, interest_rate: 0.0, runoff_rate: 0.1 },
    { id: "sav", name: "Savings", balance: 3000000, interest_rate: 0.002, beta: 0.35 },
  ],
  positions: [
    { id: "ust", type: "treasury_note", face_value: 2000000, coupon_rate: 0.0125, issue_date: "2021-08-15",
      maturity_date: "2026-08-15", issuer: { name: "US Treasury", issuer_type: "SOVEREIGN", credit_rating: "AA_PLUS" },
      basis: "FVOCI", amortized_cost: 2000000, fair_value: 1985000 },
    { id: "mbs", type: "mortgage_backed_security", face_value: 3000000, coupon_rate: 0.02, issue_date: "2021-12-31",
      maturity: "25Y", issuer: { name: "Agency", issuer_type: "PSE", credit_rating: "AA_PLUS" },
      basis: "AMORTIZED_COST", amortized_cost: 3000000, fair_value: 2970000 },
    { id: "mtg", type: "residential_mortgage", face_value: 4500000, interest_rate: 0.031, issue_date: "2021-12-31",
      maturity: "30Y", ltv: 0.75, issuer: { name: "Households", issuer_type: "INDIVIDUAL" },
      basis: "AMORTIZED_COST", amortized_cost: 4500000 },
  ],
};

export async function render(main, ctx) {
  ctx.setTitle("Import a bank");
  main.append(
    h("div", { class: "page-head" }, h("h1", {}, "Import a bank"),
      h("span", { class: "meta" }, "Build a balance sheet the lab can run")),
    h("div", { class: "grid cols-2" }, callReportPanel(), bankFilePanel()),
  );
}

function callReportPanel() {
  const status = h("div");
  const cert = h("input", { type: "text", inputmode: "numeric", id: "cr-cert", value: "24735", required: true,
    pattern: "[0-9]+", "aria-describedby": "cr-cert-hint" });
  const when = h("select", { id: "cr-date" }, quarterEnds().map((d) => h("option", { value: d }, d)));
  when.value = "2021-12-31";
  const ltv = h("input", { type: "number", id: "cr-ltv", value: "0.8", min: "0.05", max: "1.5", step: "0.05" });
  const aoci = h("input", { type: "checkbox", id: "cr-aoci", checked: true });
  const submit = h("button", { class: "btn primary", type: "submit" }, "Build from Call Report");
  const form = h("form", { class: "form" },
    h("div", { class: "row" },
      h("div", { class: "field" }, h("label", { for: "cr-cert" }, "FDIC certificate"), cert,
        h("span", { class: "hint", id: "cr-cert-hint" }, "Find it on FDIC BankFind. SVB is 24735.")),
      h("div", { class: "field" }, h("label", { for: "cr-date" }, "Quarter end"), when)),
    h("div", { class: "row" },
      h("div", { class: "field" }, h("label", { for: "cr-ltv" }, "Mortgage loan-to-value"), ltv),
      h("label", { class: "check", style: { marginTop: "16px" } }, aoci, "Exclude AOCI from CET1 (AOCI filter)")),
    h("div", { class: "notice" }, "Securities and loans come from the report's maturity buckets; each class splits "
      + "between HTM and AFS in the bank's overall proportion. Deposits get no pass-through or run-off: edit the bank "
      + "file afterwards if you need them. Values are in USD thousands."),
    h("div", { class: "row" }, submit), status);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!/^\d+$/.test(cert.value.trim())) {
      status.replaceChildren(errorBox("The FDIC certificate is a number"));
      return;
    }
    submit.disabled = true;
    status.replaceChildren();
    try {
      const bank = await api.callReport({ cert: Number(cert.value.trim()), date: when.value,
        ltv: Number(ltv.value), aoci_filter: aoci.checked });
      toast("Fetching the Call Report and building the bank…");
      location.hash = `#/banks/${encodeURIComponent(bank.id)}`;
    } catch (error) {
      status.replaceChildren(errorBox(error));
    } finally {
      submit.disabled = false;
    }
  });
  return panel("From a US Call Report", form, { note: "FDIC BankFind" });
}

function bankFilePanel() {
  const status = h("div");
  const text = h("textarea", { id: "bf-json", spellcheck: "false", rows: "18", "aria-label": "Bank file JSON" },
    JSON.stringify(EXAMPLE, null, 2));
  const file = h("input", { type: "file", accept: ".json,application/json", hidden: true });
  const drop = h("div", { class: "drop", tabindex: "0", role: "button" }, "Drop a bank.json here, or click to choose a file");
  drop.addEventListener("click", () => file.click());
  drop.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); file.click(); } });
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  async function load(f) { if (f) text.value = await f.text(); }
  drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); load(e.dataTransfer.files[0]); });
  file.addEventListener("change", () => load(file.files[0]));
  const submit = h("button", { class: "btn primary", type: "submit" }, "Build from bank file");
  const form = h("form", { class: "form" }, drop, file, text,
    h("div", { class: "notice" }, "Positions as of one date, with clean amortised cost and/or fair value. Equity is "
      + "the balancing figure. Types: treasury_note, fixed_rate_bond, mortgage_backed_security, residential_mortgage, "
      + "amortizing_fixed_rate_loan, variable_rate_loan."),
    h("div", { class: "row" }, submit), status);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    let bank;
    try { bank = JSON.parse(text.value); } catch (error) {
      status.replaceChildren(errorBox(`Not valid JSON: ${error.message}`));
      return;
    }
    submit.disabled = true;
    status.replaceChildren();
    try {
      const created = await api.createBank(bank);
      toast("Building the bank…");
      location.hash = `#/banks/${encodeURIComponent(created.id)}`;
    } catch (error) {
      status.replaceChildren(errorBox(error));
    } finally {
      submit.disabled = false;
    }
  });
  return panel("From a bank file", form, { note: "JSON" });
}

function quarterEnds() {
  const out = [];
  const now = new Date();
  for (let year = now.getFullYear(); year >= 2001; year -= 1) {
    for (const md of ["12-31", "09-30", "06-30", "03-31"]) {
      const d = `${year}-${md}`;
      if (new Date(`${d}T00:00:00`) < now) out.push(d);
    }
  }
  return out;
}
