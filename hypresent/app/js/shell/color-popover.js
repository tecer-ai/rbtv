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
        font-size: 0.8125rem;
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
      }
      .hyp-color-header {
        font-weight: 600;
        color: #444;
        text-transform: uppercase;
        letter-spacing: 0.02em;
        font-size: 0.75rem;
        margin-bottom: 0.25rem;
      }
      .hyp-token-list {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        max-height: 40vh;
        overflow-y: auto;
      }
      .hyp-token-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.125rem 0;
      }
      .hyp-token-name {
        flex: 1;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.75rem;
        color: #333;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .hyp-token-row .clr-field {
        flex-shrink: 0;
      }
      .hyp-token-row .clr-field input {
        width: 5rem;
        font-size: 0.6875rem;
        padding: 0.125rem 0.25rem;
        border: 1px solid #ccc;
        border-radius: 0.25rem;
      }
      .hyp-element-section {
        border-top: 1px solid #eee;
        padding-top: 0.75rem;
      }
      .hyp-color-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.125rem 0;
      }
      .hyp-color-row label {
        width: 4.5rem;
        font-size: 0.75rem;
        color: #555;
      }
      .hyp-color-row .clr-field input {
        width: 5rem;
        font-size: 0.6875rem;
        padding: 0.125rem 0.25rem;
        border: 1px solid #ccc;
        border-radius: 0.25rem;
      }
      .hyp-no-selection {
        color: #888;
        font-size: 0.75rem;
        font-style: italic;
        padding: 0.25rem 0;
      }
    </style>
    <div class="hyp-color-panel">
      <div>
        <div class="hyp-color-header">Palette Tokens</div>
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
  `;

  const tokenListEl = container.querySelector(".hyp-token-list");
  const elementBodyEl = container.querySelector(".hyp-element-body");

  function renderTokens(tokens) {
    tokenListEl.innerHTML = "";

    if (!tokens || tokens.length === 0) {
      tokenListEl.innerHTML = `<p class="hyp-no-selection">No color tokens found</p>`;
      return;
    }

    for (const token of tokens) {
      const row = document.createElement("div");
      row.className = "hyp-token-row";
      row.innerHTML = `
        <span class="hyp-token-name" title="${token.name}">${token.name}</span>
        <input type="text"
               class="hyp-coloris-input"
               data-coloris
               data-scope="token"
               data-target="${token.name}"
               value="${escapeHtml(token.value)}"
               aria-label="Color for ${token.name}">
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

    const textRow = document.createElement("div");
    textRow.className = "hyp-color-row";
    textRow.innerHTML = `
      <label>Text</label>
      <input type="text"
             class="hyp-coloris-input"
             data-coloris
             data-scope="element"
             data-target="${info.hypId}"
             data-prop="color"
             placeholder="none"
             aria-label="Text color">
    `;
    elementBodyEl.appendChild(textRow);

    const bgRow = document.createElement("div");
    bgRow.className = "hyp-color-row";
    bgRow.innerHTML = `
      <label>Background</label>
      <input type="text"
             class="hyp-coloris-input"
             data-coloris
             data-scope="element"
             data-target="${info.hypId}"
             data-prop="background-color"
             placeholder="none"
             aria-label="Background color">
    `;
    elementBodyEl.appendChild(bgRow);

    Coloris.wrap(".hyp-coloris-input");
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

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
