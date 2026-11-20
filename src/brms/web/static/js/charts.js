// ECharts wrappers: one y-axis per chart, thin lines, crosshair tooltips, legend + end labels.

/* global echarts */
import { legend } from "./ui.js";

// Categorical slots, dark steps, validated as a set against the panel surface (#171a1e).
export const SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767"];
const INK = { text: "#e4e7eb", text2: "#b3b9c2", muted: "#7f8792", grid: "#24282e", axis: "#3a3f47", panel: "#171a1e" };

// Tooltips are HTML: everything interpolated into them (series names come from user labels) is escaped.
export function escapeHtml(text) {
  return String(text ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

const live = new Set();
const observers = new Set();

export function disposeAll() {
  for (const observer of observers) observer.disconnect();
  observers.clear();
  for (const chart of live) chart.dispose();
  live.clear();
}

function mount(el) {
  const chart = echarts.init(el, null, { renderer: "canvas" });
  live.add(chart);
  const observer = new ResizeObserver(() => { if (!chart.isDisposed()) chart.resize(); });
  observer.observe(el);
  observers.add(observer);
  return chart;
}

function tooltipBase(format) {
  return {
    trigger: "axis",
    axisPointer: { type: "line", lineStyle: { color: INK.muted, width: 1, type: "dashed" } },
    backgroundColor: "#23282e",
    borderColor: "#3a4049",
    borderWidth: 1,
    padding: [6, 9],
    textStyle: { color: INK.text, fontSize: 11 },
    extraCssText: "box-shadow:0 6px 20px rgba(0,0,0,.45);border-radius:2px;",
    formatter(params) {
      const rows = (Array.isArray(params) ? params : [params]).filter((p) => p.value !== null && p.value !== undefined);
      if (!rows.length) return "";
      const head = `<div style="color:${INK.muted};margin-bottom:3px">${escapeHtml(rows[0].axisValueLabel)}</div>`;
      return head + rows.map((p) => {
        const value = Array.isArray(p.value) ? p.value[1] : p.value;
        return `<div style="display:flex;gap:14px;justify-content:space-between"><span>`
          + `<span style="display:inline-block;width:8px;height:2px;background:${p.color};margin-right:6px;vertical-align:middle"></span>`
          + `${escapeHtml(p.seriesName)}</span><span style="font-variant-numeric:tabular-nums">`
          + `${escapeHtml(format(value))}</span></div>`;
      }).join("");
    },
  };
}

function axisLabel(format) {
  return { color: INK.muted, fontSize: 10.5, formatter: format };
}

/**
 * Line (or stacked area) chart over dates.
 * spec: {dates, series: [{name, values, color?}], format(v) -> string, axisFormat?, stacked?, area?, zero?,
 *        endLabels?, markLine?: {date, label}}
 */
export function lineChart(container, spec) {
  const host = container.querySelector(".chart") || container;
  const chart = mount(host);
  const colors = spec.series.map((s, i) => s.color || SERIES[i % SERIES.length]);
  const many = spec.series.length > 1;
  const endLabels = spec.endLabels ?? (many && spec.series.length <= 4 && !spec.stacked);
  chart.setOption({
    animation: false,
    color: colors,
    grid: { left: 8, right: endLabels ? 76 : 14, top: 12, bottom: 4, containLabel: true },
    tooltip: tooltipBase(spec.format),
    xAxis: {
      type: "category", data: spec.dates, boundaryGap: false,
      axisLine: { lineStyle: { color: INK.axis } }, axisTick: { show: false },
      axisLabel: { ...axisLabel((v) => shortDate(v)), hideOverlap: true },
    },
    yAxis: {
      type: "value", scale: !spec.stacked && !spec.zero,
      splitLine: { lineStyle: { color: INK.grid } },
      axisLabel: axisLabel(spec.axisFormat || spec.format),
    },
    series: spec.series.map((s, i) => ({
      id: `s${i}`, name: s.name, type: "line", data: s.values, showSymbol: false, symbolSize: 8,
      lineStyle: { width: 2 }, emphasis: { focus: "series" }, connectNulls: Boolean(spec.connectNulls),
      labelLayout: { moveOverlap: "shiftY" },
      stack: spec.stacked ? "total" : undefined,
      areaStyle: spec.stacked || spec.area ? { opacity: spec.stacked ? 0.85 : 0.12 } : undefined,
      endLabel: endLabels ? { show: true, color: INK.text2, fontSize: 10.5, formatter: () => s.name,
        distance: 6 } : undefined,
      markLine: i === 0 ? markLine(Boolean(spec.zero), null) : undefined,
    })),
  });
  chart.brmsZero = Boolean(spec.zero);
  if (many) container.prepend(legend(spec.series.map((s, i) => ({ name: s.name, color: colors[i] }))));
  return chart;
}

function markLine(zero, date) {
  return {
    symbol: "none", silent: true, animation: false, label: { show: false },
    lineStyle: { color: INK.axis, type: "solid", width: 1 },
    data: [zero ? { yAxis: 0 } : null,
      date ? { xAxis: date, lineStyle: { color: "#f0a92e", type: "dashed", width: 1 } } : null].filter(Boolean),
  };
}

/** Mark the selected day on a date chart (amber dashed line). */
export function setMarker(chart, date) {
  if (!chart || chart.isDisposed() || chart.brmsZero === undefined) return;
  const axis = chart.getOption().xAxis[0].data;
  chart.setOption({ series: [{ id: "s0", markLine: markLine(chart.brmsZero, axis.includes(date) ? date : null) }] });
}

/** Horizontal bars for a single measure across categories (one hue). */
export function barChart(container, { labels, values, format, color = SERIES[0] }) {
  const host = container.querySelector(".chart") || container;
  const chart = mount(host);
  chart.setOption({
    animation: false,
    grid: { left: 8, right: 60, top: 6, bottom: 4, containLabel: true },
    tooltip: { ...tooltipBase(format), trigger: "item", axisPointer: undefined,
      formatter: (p) => `${escapeHtml(p.name)}: <b>${escapeHtml(format(p.value))}</b>` },
    xAxis: { type: "value", splitLine: { lineStyle: { color: INK.grid } }, axisLabel: axisLabel(format) },
    yAxis: { type: "category", data: labels, inverse: true, axisTick: { show: false },
      axisLine: { lineStyle: { color: INK.axis } }, axisLabel: { color: INK.text2, fontSize: 11 } },
    series: [{ type: "bar", data: values, barMaxWidth: 14, itemStyle: { color, borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: "right", color: INK.text2, fontSize: 10.5, formatter: (p) => format(p.value) } }],
  });
  return chart;
}

export function shortDate(text) {
  const d = new Date(`${text}T00:00:00`);
  return d.toLocaleDateString("en-GB", { month: "short", year: "2-digit" });
}

export function chartBox(cls = "") {
  return Object.assign(document.createElement("div"), { className: `chart ${cls}` });
}
