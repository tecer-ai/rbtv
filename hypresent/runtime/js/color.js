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

import { idOf } from "./element-registry.js";
import { colorToken, colorElement } from "./commands.js";
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
  return {
    tokens: extractRootVars(),
    inlineSites: discoverInlineSites(),
  };
}

export function applyToken(name, value) {
  const cmd = colorToken(name, value);
  historyPush(cmd);
}

export function applyElement(hypId, prop, value) {
  const cmd = colorElement(hypId, prop, value);
  historyPush(cmd);
}
