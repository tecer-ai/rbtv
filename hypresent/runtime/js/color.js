/**
 * runtime/js/color.js
 *
 * Palette token mutation + per-element override + inline-style color.
 *
 * Public contract (module-map 03 §4):
 *   readPalette() → {tokens[], inlineSites[]}
 *   applyToken(name, value)
 *   applyElement(hypId, prop, value)
 *
 * Decision D6: BOTH palette + per-element. Inline-style colors outside the
 * variable system are handled by the per-element path (prop = the inline
 * property name, e.g. 'background').
 */

import { byId, idOf } from "./element-registry.js";
import { colorToken, colorElement, colorBorder } from "./commands.js";
import { push as historyPush } from "./history.js";

// --- Constants ---

const COLOR_PROPERTIES = [
  "color",
  "background-color",
  "background",
  "border-color",
  "border-top-color",
  "border-right-color",
  "border-bottom-color",
  "border-left-color",
  "fill",
  "stroke",
];

// Canvas used to test whether a string parses as a valid CSS color.
const canvas = document.createElement("canvas");
const ctx = canvas.getContext("2d");

// --- Helpers ---

/**
 * Test whether a raw string is a parseable CSS color.
 * Uses canvas fillStyle as a parser; if it stays black we do a secondary
 * check for known black-ish literals so we don't falsely reject black.
 */
function isColorString(str) {
  if (!str || typeof str !== "string") return false;
  const s = str.trim();
  if (s.length === 0) return false;

  ctx.fillStyle = "#000000";
  ctx.fillStyle = s;
  const parsed = ctx.fillStyle;

  if (parsed !== "#000000") return true;

  const lower = s.toLowerCase();
  return (
    lower === "black" ||
    lower === "#000" ||
    lower === "#000000" ||
    lower === "rgb(0, 0, 0)" ||
    lower === "rgba(0, 0, 0, 1)" ||
    lower === "hsl(0, 0%, 0%)" ||
    lower === "hsla(0, 0%, 0%, 1)"
  );
}

/**
 * Extract all :root custom properties whose value looks like a color.
 * H9 fallback: we filter by value, not by a manifest.
 */
function extractRootVars() {
  const tokens = [];
  const seen = new Set();

  // 1. Read from stylesheets
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules || []) {
        if (rule.type !== CSSRule.STYLE_RULE) continue;
        if (!rule.selectorText || !/^:root$/.test(rule.selectorText.trim()))
          continue;
        for (const prop of rule.style) {
          if (!prop.startsWith("--")) continue;
          const value = rule.style.getPropertyValue(prop).trim();
          if (isColorString(value)) {
            if (!seen.has(prop)) {
              seen.add(prop);
              tokens.push({ name: prop, value });
            }
          }
        }
      }
    } catch (e) {
      // Cross-origin stylesheets are inaccessible; skip silently.
    }
  }

  // 2. Read from documentElement inline style (runtime overrides)
  const inlineStyle = document.documentElement.style;
  for (const prop of inlineStyle) {
    if (!prop.startsWith("--")) continue;
    const value = inlineStyle.getPropertyValue(prop).trim();
    if (isColorString(value)) {
      if (!seen.has(prop)) {
        seen.add(prop);
        tokens.push({ name: prop, value });
      } else {
        const existing = tokens.find((t) => t.name === prop);
        if (existing) existing.value = value;
      }
    }
  }

  return tokens;
}

/**
 * Discover elements that carry inline style attributes with color-valued
 * properties. Only records elements that have a data-hyp-id.
 */
function discoverInlineSites() {
  const sites = [];
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_ELEMENT
  );
  while (walker.nextNode()) {
    const el = walker.currentNode;
    if (!el.hasAttribute("style")) continue;

    const style = el.style;
    for (const prop of COLOR_PROPERTIES) {
      const value = style.getPropertyValue(prop);
      if (value && value.trim().length > 0) {
        const hypId = idOf(el);
        if (hypId) {
          sites.push({ hypId, prop, value: value.trim() });
        }
      }
    }
  }
  return sites;
}

// --- Public API ---

export function readPalette() {
  const tokens = extractRootVars().map((t) => ({ ...t, hex: normalizeHex(t.value) }));
  return {
    tokens,
    inlineSites: discoverInlineSites(),
  };
}

export function applyToken(name, value) {
  const cmd = colorToken(name, value);
  historyPush(cmd);
}

export function applyElement(hypId, prop, value) {
  if (prop === "border-color") {
    historyPush(colorBorder(hypId, value));
    return;
  }
  historyPush(colorElement(hypId, prop, value));
}

export function rgbToHex(rgb) {
  // Accept "rgb(r, g, b)" / "rgba(r, g, b, a)"; return #rrggbb (ignore alpha).
  const m = /rgba?\((\d+),\s*(\d+),\s*(\d+)/.exec(rgb || "");
  if (!m) return rgb || "";
  const h = (n) => parseInt(n, 10).toString(16).padStart(2, "0");
  return `#${h(m[1])}${h(m[2])}${h(m[3])}`;
}

// R6 (V3-S14): normalize any token value to #rrggbb. Hex passes through (3→6
// digit expand, lower-case); named/hsl/rgb/var() resolve through a probe element's
// computed `color` in the document CSS context (so 'red' → '#ff0000'). An
// unparseable value falls back to itself.
//
// The probe is APPENDED to document.body, hidden (visibility:hidden; absolute;
// pointer-events:none), at module init. This is REQUIRED (RV11): a DETACHED element
// does NOT resolve CSS var() chains (e.g. `var(--brand-color)`) — getComputedStyle on
// a detached node computes against the UA stylesheet only and returns '' for a var()
// reference, so the copy button would copy the raw `var(...)` string. Attached to the
// live document, the probe inherits the document's :root cascade and var() chains
// resolve to a concrete rgb(...).
const _hexProbe = document.createElement("span");
_hexProbe.style.visibility = "hidden";
_hexProbe.style.position = "absolute";
_hexProbe.style.pointerEvents = "none";
if (document.body) {
  document.body.appendChild(_hexProbe);
} else {
  document.addEventListener("DOMContentLoaded", () => {
    if (!_hexProbe.isConnected && document.body) document.body.appendChild(_hexProbe);
  });
}
export function normalizeHex(value) {
  const v = (value || "").trim();
  if (/^#[0-9a-fA-F]{6}$/.test(v)) return v.toLowerCase();
  if (/^#[0-9a-fA-F]{3}$/.test(v)) {
    return ("#" + v.slice(1).split("").map((c) => c + c).join("")).toLowerCase();
  }
  // Lazily ensure the probe is attached (covers the rare case where the module
  // evaluated before document.body existed and DOMContentLoaded already fired).
  if (!_hexProbe.isConnected && document.body) document.body.appendChild(_hexProbe);
  _hexProbe.style.color = "";
  _hexProbe.style.color = v;
  const resolved = getComputedStyle(_hexProbe).color; // 'rgb(r, g, b)' or '' if invalid
  return resolved ? rgbToHex(resolved) : v;
}

export function readElementBorder(hypId) {
  const el = byId(hypId);
  if (!el) return { color: "", mixed: false };
  const cs = getComputedStyle(el);
  const SIDES = ["top", "right", "bottom", "left"];
  const colors = SIDES.map((s) => cs.getPropertyValue(`border-${s}-color`).trim());
  const mixed = new Set(colors).size > 1;
  return { color: mixed ? "" : rgbToHex(colors[0]), mixed };
}

export function readElementColors(hypId) {
  const el = byId(hypId);
  if (!el) return { color: "", background: "", borderColor: "", borderMixed: false };
  const inline = el.style;
  const border = readElementBorder(hypId);
  return {
    color: inline.getPropertyValue("color") || "",
    background:
      inline.getPropertyValue("background-color") ||
      inline.getPropertyValue("background") ||
      "",
    borderColor: border.color,
    borderMixed: border.mixed,
  };
}
