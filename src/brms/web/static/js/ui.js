// Small DOM helpers and components: panels, KPI tiles, sortable data grids, chips, toasts.

export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") el.className = value;
    else if (key === "html") el.innerHTML = value;
    else if (key.startsWith("on") && typeof value === "function") el.addEventListener(key.slice(2), value);
    else if (key === "style" && typeof value === "object") Object.assign(el.style, value);
    else el.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

export function panel(title, body, { note, tools, flush = false, cls = "" } = {}) {
  return h("section", { class: `panel ${cls}` },
    h("div", { class: "panel-head" }, h("h2", {}, title), note ? h("span", { class: "note" }, note) : null,
      tools ? h("div", { class: "tools" }, tools) : null),
    h("div", { class: `panel-body${flush ? " flush" : ""}` }, body));
}

export function kpi(label, value, { sub, cls = "", title } = {}) {
  return h("div", { class: "kpi", title },
    h("div", { class: "label" }, label),
    h("div", { class: `value ${cls}` }, value),
    sub !== undefined ? h("div", { class: "sub" }, sub) : null);
}

export function chip(status) {
  return h("span", { class: `chip ${status}` }, status);
}

export function seg(options, current, onChange) {
  const box = h("div", { class: "seg", role: "tablist" });
  for (const [value, label] of options) {
    const button = h("button", { type: "button", role: "tab", "aria-selected": String(value === current),
      class: value === current ? "on" : "" }, label);
    button.addEventListener("click", () => {
      for (const b of box.children) { b.classList.remove("on"); b.setAttribute("aria-selected", "false"); }
      button.classList.add("on");
      button.setAttribute("aria-selected", "true");
      onChange(value);
    });
    box.append(button);
  }
  return box;
}

/**
 * A sortable data grid.
 * columns: [{key, label, num?, render?(row) -> Node|string, sort?(row) -> value, cls?(row) -> string, title?}]
 */
export function dataTable(columns, rows, { onRow, sortKey, sortDir = "desc", empty = "Nothing to show", rowKey,
  selected, short = false, state } = {}) {
  // Pass the same *state* object to keep the user's sort when a polling page redraws the table.
  const sort = state || {};
  if (sort.key === undefined) { sort.key = sortKey; sort.dir = sortDir; }
  let key = sort.key;
  let dir = sort.dir;
  const wrap = h("div", { class: `table-wrap${short ? " short" : ""}` });

  function draw() {
    const column = columns.find((c) => c.key === key);
    const sorted = [...rows];
    if (column) {
      const value = column.sort || ((row) => row[column.key]);
      sorted.sort((a, b) => {
        const x = value(a); const y = value(b);
        if (x === y) return 0;
        if (x === null || x === undefined) return 1;
        if (y === null || y === undefined) return -1;
        return (x < y ? -1 : 1) * (dir === "asc" ? 1 : -1);
      });
    }
    const head = h("tr", {}, columns.map((c) => {
      const th = h("th", { class: `${c.num ? "num " : ""}sortable`, scope: "col", title: c.title,
        "aria-sort": c.key === key ? (dir === "asc" ? "ascending" : "descending") : null },
        c.label, c.key === key ? h("span", { class: "arrow" }, dir === "asc" ? " ▲" : " ▼") : null);
      th.addEventListener("click", () => {
        if (key === c.key) dir = dir === "asc" ? "desc" : "asc";
        else { key = c.key; dir = c.num ? "desc" : "asc"; }
        sort.key = key;
        sort.dir = dir;
        draw();
      });
      return th;
    }));
    const body = h("tbody", {}, sorted.map((row) => {
      const tr = h("tr", { class: `${onRow ? "clickable" : ""}${rowKey && selected === row[rowKey] ? " selected" : ""}` },
        columns.map((c) => {
          const content = c.render ? c.render(row) : row[c.key];
          return h("td", { class: `${c.num ? "num " : ""}${c.name ? "name " : ""}${c.cls ? c.cls(row) : ""}`,
            title: c.name && typeof content === "string" ? content : null }, content ?? "–");
        }));
      if (onRow) tr.addEventListener("click", (event) => onRow(row, event));
      return tr;
    }));
    wrap.replaceChildren(rows.length
      ? h("table", { class: "data" }, h("thead", {}, head), body)
      : h("div", { class: "empty" }, empty));
  }

  draw();
  return wrap;
}

export function toast(message, { error = false, timeout = 4500 } = {}) {
  const box = document.getElementById("toasts");
  const el = h("div", { class: `toast${error ? " error" : ""}` }, message);
  box.append(el);
  setTimeout(() => el.remove(), timeout);
}

export function loading(text = "Loading") {
  return h("div", { class: "loading" }, h("span", { class: "spinner" }), " ", text, "…");
}

export function errorBox(error) {
  return h("div", { class: "error" }, error instanceof Error ? error.message : String(error));
}

/** An error with links back to the lists (for pages whose subject could not be loaded). */
export function errorPage(error) {
  return h("div", {}, errorBox(error), h("p", {}, h("a", { href: "#/banks" }, "Back to banks"), " \u00B7 ",
    h("a", { href: "#/runs" }, "All runs")));
}

export function legend(items) {
  return h("div", { class: "legend" }, items.map(({ name, color }) =>
    h("span", {}, h("i", { style: { background: color } }), name)));
}
