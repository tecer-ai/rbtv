/**
 * app/js/shell/color-popover.js
 *
 * Color UI wrapping Coloris.
 * Renders a palette token list and per-element color overrides in the
 * provided panel element. Dispatches bridge `apply-color` commands.
 *
 * Public contract (module-map 03 §3):
 *   createColorPopover({ bridge, panelEl }) → popover API
 */

import Coloris from "/app/js/vendor/coloris.min.js";

export function createColorPopover({ bridge, panelEl }) {
  if (!panelEl) {
    throw new Error("createColorPopover requires a panel element");
  }

  let currentSelection = null;

  // Dedicated child container so we never wipe sibling panels (outline, comments).
  let container = panelEl.querySelector(".hyp-color-popover-container");
  if (container) container.remove();
  container = document.createElement("div");
  container.className = "hyp-color-popover-container";
  panelEl.insertBefore(container, panelEl.firstChild);

  container.innerHTML = `
    <style>
      .hyp-color-panel {
        font-size: 13px;
        display: flex;
        flex-direction: column;
      }
      .hyp-colors-toggle {
        display: flex; align-items: center; gap: 7px;
        width: 100%;
        padding: 14px 18px;
        background: none; border: none; border-bottom: 1px solid var(--line);
        cursor: pointer; text-align: left;
        font: inherit; font-size: 11px; font-weight: 700; letter-spacing: .09em;
        text-transform: uppercase; color: var(--ink-mut);
      }
      .hyp-colors-toggle:hover { background: var(--paper-2); }
      .hyp-colors-chevron {
        width: 13px; height: 13px; flex: none;
        transition: transform .15s ease;
      }
      .hyp-colors-toggle[aria-expanded="true"] .hyp-colors-chevron { transform: rotate(90deg); }
      .hyp-colors-collapse[hidden] { display: none; }
      .hyp-colors-collapse > div { padding: 16px 18px 18px; border-bottom: 1px solid var(--line); }
      .hyp-color-header {
        display: flex; align-items: center; gap: 7px;
        font-size: 11px; font-weight: 700; letter-spacing: .09em;
        text-transform: uppercase; color: var(--ink-mut);
        margin-bottom: 12px;
      }
      .hyp-token-list {
        display: flex;
        flex-direction: column;
        max-height: 40vh;
        overflow-y: auto;
      }
      .hyp-token-row, .hyp-color-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 6px 2px;
        border-radius: 6px;
      }
      .hyp-token-row:hover, .hyp-color-row:hover { background: var(--paper-2); }
      .hyp-token-name {
        flex: 1;
        font-size: 13px; font-weight: 600; color: var(--ink);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .hyp-color-row label { flex: 1; font-size: 12.5px; font-weight: 600; color: var(--ink-mut); }
      /* Coloris field → mock-style swatch + quiet hex text */
      .hyp-color-panel .clr-field { display: flex; align-items: center; gap: 8px; flex: none; color: transparent; }
      .hyp-color-panel .clr-field button {
        /* relative (not static): Coloris paints the swatch via an absolutely
           positioned ::after — it must anchor to the button, not the field */
        position: relative; order: -1; flex: none;
        top: auto; left: auto; right: auto; bottom: auto;
        transform: none; margin: 0;
        width: 20px; height: 20px; border-radius: 6px;
        border: 1px solid rgba(27,31,42,.14);
        overflow: hidden; cursor: pointer;
      }
      .hyp-color-panel .clr-field button:after { border-radius: 5px; box-shadow: none; }
      .hyp-color-panel .clr-field input {
        width: 70px;
        border: none; background: transparent;
        font-family: ui-monospace, "Cascadia Mono", Consolas, monospace;
        font-size: 11.5px; color: var(--ink-mut);
        padding: 2px 0;
      }
      .hyp-no-selection {
        color: var(--ink-faint);
        font-size: 12.5px;
        font-style: italic;
        padding: 2px 0;
      }
      .hyp-token-info {
        width: 17px; height: 17px; border-radius: 50%;
        display: inline-flex; align-items: center; justify-content: center;
        border: 1px solid var(--line-2); color: var(--ink-faint);
        font-size: 10.5px; font-weight: 700; font-style: normal;
        margin-left: auto; cursor: help;
      }
      .hyp-token-copy {
        flex: none;
        width: 24px; height: 24px; border-radius: 5px;
        display: inline-flex; align-items: center; justify-content: center;
        border: none; background: transparent;
        color: var(--ink-faint); cursor: pointer;
        font-size: 12px; line-height: 1;
        opacity: 0; transition: opacity .12s ease, background .12s ease, color .12s ease;
      }
      .hyp-token-row:hover .hyp-token-copy { opacity: 1; }
      .hyp-token-copy:hover { background: var(--line); color: var(--ink); }
      .hyp-token-copied { color: var(--ok) !important; opacity: 1 !important; }
    </style>
    <div class="hyp-color-panel">
      <button type="button" class="hyp-colors-toggle" aria-expanded="false" aria-controls="hyp-colors-body">
        <svg class="hyp-colors-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>
        <span>Colors</span>
      </button>
      <div class="hyp-colors-collapse" id="hyp-colors-body" hidden>
        <div>
          <div class="hyp-color-header">Palette Tokens<span class="hyp-token-info" title="Changing a palette token recolors every element using that color across the whole document.">i</span></div>
          <div class="hyp-token-list">
            <p class="hyp-no-selection">Open a file to see palette tokens</p>
          </div>
        </div>
        <div class="hyp-element-section">
          <div class="hyp-color-header">Selected Element</div>
          <div class="hyp-element-body">
            <p class="hyp-no-selection">No element selected</p>
          </div>
        </div>
      </div>
    </div>
  `;

  const tokenListEl = container.querySelector(".hyp-token-list");
  const elementBodyEl = container.querySelector(".hyp-element-body");

  // Collapsible color section — collapsed by default.
  const collapseToggle = container.querySelector(".hyp-colors-toggle");
  const collapseBody = container.querySelector(".hyp-colors-collapse");
  collapseToggle.addEventListener("click", () => {
    const expanded = collapseToggle.getAttribute("aria-expanded") === "true";
    collapseToggle.setAttribute("aria-expanded", expanded ? "false" : "true");
    collapseBody.hidden = expanded;
  });

  function renderTokens(tokens) {
    tokenListEl.innerHTML = "";

    if (!tokens || tokens.length === 0) {
      tokenListEl.innerHTML = `<p class="hyp-no-selection">No color tokens found</p>`;
      return;
    }

    for (const token of tokens) {
      const row = document.createElement("div");
      row.className = "hyp-token-row";
      const hex = token.hex || token.value;
      row.innerHTML = `
        <span class="hyp-token-name" title="${token.name}">${token.name}</span>
        <input type="text"
               class="hyp-coloris-input"
               data-coloris
               data-scope="token"
               data-target="${token.name}"
               value="${escapeHtml(token.value)}"
               aria-label="Color for ${token.name}">
        <button type="button"
                class="hyp-token-copy"
                data-hex="${escapeHtml(hex)}"
                title="Copy HEX"
                aria-label="Copy ${token.name} hex">⧉</button>
      `;
      tokenListEl.appendChild(row);
    }

    Coloris.wrap(".hyp-coloris-input");
  }

  function renderElement(info) {
    elementBodyEl.innerHTML = "";
    if (!info || !info.hypId) {
      elementBodyEl.innerHTML = `<p class="hyp-no-selection">No element selected</p>`;
      return;
    }

    const rows = [
      { label: "Text", prop: "color" },
      { label: "Background", prop: "background-color" },
      { label: "Border", prop: "border-color" },
    ];
    for (const r of rows) {
      const row = document.createElement("div");
      row.className = "hyp-color-row";
      row.innerHTML = `
        <label>${r.label}</label>
        <input type="text"
               class="hyp-coloris-input"
               data-coloris
               data-scope="element"
               data-target="${info.hypId}"
               data-prop="${r.prop}"
               placeholder="none"
               aria-label="${r.label} color">
      `;
      elementBodyEl.appendChild(row);
    }

    Coloris.wrap(".hyp-coloris-input");

    // Pre-fill the three inputs from one read.
    bridge
      .command("element-color-read", { hypId: info.hypId })
      .then((c) => {
        const setVal = (prop, value, placeholder) => {
          const inp = elementBodyEl.querySelector(
            `.hyp-coloris-input[data-prop="${prop}"]`
          );
          if (!inp) return;
          if (placeholder) {
            inp.value = "";
            inp.placeholder = placeholder;
          } else {
            inp.value = value || "";
          }
        };
        setVal("color", c.color);
        setVal("background-color", c.background);
        if (c.borderMixed) {
          setVal("border-color", "", "mixed");
        } else {
          setVal("border-color", c.borderColor);
        }
      })
      .catch(() => {
        // read may fail before a document is open; leave inputs empty.
      });
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // R6: delegated copy-HEX handler. Writes the normalized #rrggbb to the
  // clipboard (localhost is a secure context, so writeText works) and shows a
  // transient "Copied!" affordance.
  container.addEventListener("click", (event) => {
    const btn = event.target.closest(".hyp-token-copy");
    if (!btn) return;
    const hex = btn.dataset.hex || "";
    if (!hex) return;
    navigator.clipboard
      .writeText(hex)
      .then(() => {
        const prevTitle = btn.title;
        btn.title = "Copied!";
        btn.classList.add("hyp-token-copied");
        setTimeout(() => {
          btn.title = prevTitle;
          btn.classList.remove("hyp-token-copied");
        }, 1200);
      })
      .catch((err) => console.error("copy hex failed:", err));
  });

  // Apply color changes via bridge command.
  // We listen on 'change' so each Coloris session produces one command.
  container.addEventListener("change", (event) => {
    const input = event.target;
    if (!input.classList.contains("hyp-coloris-input")) return;

    const scope = input.dataset.scope;
    const target = input.dataset.target;
    const value = input.value.trim();
    const prop = input.dataset.prop || "color";

    if (!scope || !target) return;

    if (scope === "token") {
      bridge
        .command("apply-color", { scope: "token", target, value })
        .catch((err) => console.error("apply-color token failed:", err));
    } else if (scope === "element") {
      bridge
        .command("apply-color", { scope: "element", target, value, prop })
        .catch((err) => console.error("apply-color element failed:", err));
    }
  });

  // Populate tokens from the ready payload, or explicitly read them.
  function populateTokens(payload) {
    const tokens = payload && payload.tokens ? payload.tokens : [];
    renderTokens(tokens);
  }

  bridge.on("ready", populateTokens);

  bridge.on("selection-changed", (info) => {
    currentSelection = info;
    renderElement(info);
  });

  // Explicitly fetch palette in case ready already fired before the bridge
  // listener was attached (common on fast local loads).
  bridge
    .command("palette-read")
    .then((result) => renderTokens(result.tokens || []))
    .catch(() => {
      // palette-read may fail before a document is open; ignore.
    });

  return {
    refresh() {
      bridge
        .command("palette-read")
        .then((result) => renderTokens(result.tokens || []))
        .catch((err) => console.error("palette-read failed:", err));
    },
  };
}
