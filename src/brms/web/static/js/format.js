// Number and date formatting for dense financial tables.

const MINUS = "−";
let scale = 1;

/** Set the currency amount one unit of the current bank's figures stands for (1000 for Call Reports). */
export function setUnit(unit) { scale = Number(unit) || 1; }

/** A note for tables that show figures as reported, e.g. "USD thousands". */
export function unitNote(unit = scale) {
  return { 1: "", 1000: "USD thousands", 1000000: "USD millions" }[unit] ?? `×${unit}`;
}

/** Compact money, scaled to currency units (by *unit*, else the current bank's). */
export function money(raw, { compact = true, sign = false, digits, unit } = {}) {
  if (raw === null || raw === undefined || Number.isNaN(raw)) return "–";
  const value = raw * (unit ?? scale);
  const abs = Math.abs(value);
  let text;
  if (compact && abs >= 1e3) {
    const units = [[1e12, "T"], [1e9, "B"], [1e6, "M"], [1e3, "K"]];
    const [size, suffix] = units.find(([s]) => abs >= s);
    const scaled = abs / size;
    const d = digits ?? (scaled >= 100 ? 1 : 2);
    text = scaled.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }) + suffix;
  } else {
    const d = digits ?? (abs >= 100 ? 0 : 2);
    text = abs.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  if (value < 0) return MINUS + text;
  return sign && value > 0 ? "+" + text : text;
}

export function full(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  const text = Math.abs(value).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  return value < 0 && /[1-9]/.test(text) ? MINUS + text : text;  // no "−0" for amounts that round to zero
}

/** Sign class for a value shown at *digits* decimals: nothing for amounts that round to zero. */
export function signAt(value, digits = 0) {
  if (value === null || value === undefined) return "";
  return Math.abs(value) < 0.5 * 10 ** -digits ? "" : signClass(value);
}

export function pct(value, { digits = 2, sign = false } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  const text = Math.abs(value * 100).toFixed(digits) + "%";
  if (value < 0) return MINUS + text;
  return sign && value > 0 ? "+" + text : text;
}

export function years(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  return value.toFixed(2) + "y";
}

export function signClass(value) {
  if (value === null || value === undefined || value === 0) return "";
  return value > 0 ? "up" : "down";
}

export function date(text) {
  if (!text) return "–";
  const d = new Date(text.length <= 10 ? text + "T00:00:00" : text);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

export function datetime(text) {
  if (!text) return "–";
  return new Date(text).toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function last(values) {
  for (let i = values.length - 1; i >= 0; i -= 1) if (values[i] !== null && values[i] !== undefined) return values[i];
  return null;
}

export function humanType(type) {
  return (type || "").toLowerCase().replaceAll("_", " ").replace(/^\w/, (c) => c.toUpperCase());
}

export const BASIS = { AMORTIZED_COST: "Amortised cost", FVOCI: "FVOCI", FVTPL: "FVTPL", NA: "–" };
export const GROUP = { htm: "HTM securities", afs: "AFS securities", loans: "Loans" };
