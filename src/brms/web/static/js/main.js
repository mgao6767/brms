// Router, open-view tabs and the running-jobs indicator.

import { api } from "./api.js";
import { disposeAll } from "./charts.js";
import { setUnit } from "./format.js";
import { errorBox, h, toast } from "./ui.js";
import * as banks from "./views/banks.js";
import * as bank from "./views/bank.js";
import * as importer from "./views/import.js";
import * as runs from "./views/runs.js";
import * as run from "./views/run.js";
import * as compare from "./views/compare.js";

const ROUTES = [
  [/^#\/banks\/?$/, banks, "banks"],
  [/^#\/banks\/([^/?]+)$/, bank, "banks"],
  [/^#\/import\/?$/, importer, "import"],
  [/^#\/runs\/?$/, runs, "runs"],
  [/^#\/runs\/([^/?]+)$/, run, "runs"],
  [/^#\/compare(?:\?(.*))?$/, compare, "compare"],
];
const TAB_KEY = "brms.tabs";
const MAX_TABS = 12;

let cleanup = null;
let generation = 0;

function loadTabs() {
  try { return JSON.parse(localStorage.getItem(TAB_KEY)) || []; } catch { return []; }
}

function saveTabs(tabs) {
  try { localStorage.setItem(TAB_KEY, JSON.stringify(tabs.slice(-MAX_TABS))); } catch { /* private mode */ }
}

function drawTabs() {
  const current = location.hash || "#/banks";
  const nav = document.getElementById("tabs");
  nav.replaceChildren(...loadTabs().map((tab) => {
    const close = h("button", { type: "button", "aria-label": `Close ${tab.title}`, title: "Close" }, "×");
    close.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const remaining = loadTabs().filter((t) => t.hash !== tab.hash);
      saveTabs(remaining);
      if (tab.hash === current) location.hash = remaining.length ? remaining[remaining.length - 1].hash : "#/banks";
      else drawTabs();
    });
    return h("a", { class: `tab${tab.hash === current ? " active" : ""}`, href: tab.hash, title: tab.title },
      h("span", {}, tab.title), close);
  }));
  nav.querySelector(".active")?.scrollIntoView({ block: "nearest", inline: "nearest" });
}

function setTitle(title) {
  const hash = location.hash || "#/banks";
  document.title = `${title} · BRMS Stress Lab`;
  const tabs = loadTabs();
  const existing = tabs.find((t) => t.hash === hash);
  if (existing) existing.title = title;
  else tabs.push({ hash, title });
  saveTabs(tabs);
  drawTabs();
}

async function route() {
  const hash = location.hash || "#/banks";
  if (!location.hash) history.replaceState(null, "", "#/banks");
  const mine = ++generation;
  if (cleanup) { try { cleanup(); } catch { /* ignore */ } cleanup = null; }
  disposeAll();
  setUnit(1);
  const main = document.getElementById("view");
  main.replaceChildren();
  main.scrollTop = 0;
  const match = ROUTES.map(([re, view, section]) => [hash.match(re), view, section]).find(([m]) => m);
  for (const link of document.querySelectorAll(".rail a")) {
    link.classList.toggle("active", Boolean(match) && link.dataset.section === match[2]);
  }
  if (!match) {
    main.append(errorBox(`No page at ${hash}`));
    return;
  }
  const [m, view] = match;
  try {
    const ctx = {
      setTitle,
      alive: () => mine === generation,
      params: m.slice(1).map((p) => (p === undefined ? p : decodeURIComponent(p))),
    };
    cleanup = (await view.render(main, ctx)) || null;
    if (mine !== generation && cleanup) { cleanup(); cleanup = null; }
  } catch (error) {
    if (mine === generation) {
      main.replaceChildren(errorBox(error), h("p", {}, h("a", { href: "#/banks" }, "Back to banks"), " \u00B7 ",
        h("a", { href: "#/runs" }, "All runs")));
    }
  }
  drawTabs();
}

let stopped = false;

async function pollJobs() {
  if (stopped) return;
  const el = document.getElementById("jobs");
  try {
    const active = (await api.runs()).filter((r) => r.status === "queued" || r.status === "running");
    el.hidden = active.length === 0;
    el.textContent = active.length === 1 ? "1 run in progress" : `${active.length} runs in progress`;
  } catch {
    el.hidden = true;
  }
}

function showStopped(count) {
  stopped = true;
  disposeAll();
  const note = count === 1 ? "1 job in progress was stopped and is marked failed."
    : count > 1 ? `${count} jobs in progress were stopped and are marked failed.` : null;
  document.body.replaceChildren(h("div", { class: "stopped" },
    h("h1", {}, "The Stress Lab has stopped"),
    h("p", {}, "Your banks and runs are saved. You can close this tab."),
    note ? h("p", {}, note) : null,
    h("p", {}, "To use the lab again, run ", h("code", {}, "brms-web"), " in a terminal.")));
  document.title = "BRMS Stress Lab (stopped)";
}

async function quitLab() {
  let active = 0;
  try {
    active = (await api.runs()).filter((r) => r.status === "queued" || r.status === "running").length;
  } catch { /* the lab may already be gone: still ask */ }
  const warning = active === 1 ? "\n\n1 run in progress will be stopped."
    : active > 1 ? `\n\n${active} runs in progress will be stopped.` : "";
  if (!window.confirm(`Quit the Stress Lab?${warning}`)) return;
  try {
    const { stopped: count } = await api.quit();
    showStopped(count);
  } catch (error) {
    if (error.status === undefined) showStopped(0); // already stopped
    else toast(error.message, { error: true });
  }
}

document.getElementById("quit").addEventListener("click", quitLab);
window.addEventListener("hashchange", route);
route();
pollJobs();
setInterval(pollJobs, 3000);
