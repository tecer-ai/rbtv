# G1 Panel-Survival — Confirmation (v2)

The fix is present. The popover renders into `.hyp-color-popover-container`, which is inserted as the first child of `.shell-panel` via `insertBefore`; it never sets `panelEl.innerHTML`.

## Verified container-creation block (lines 21–26 of `app/js/shell/color-popover.js`)

```js
  // Dedicated child container so we never wipe sibling panels (outline, comments).
  let container = panelEl.querySelector(".hyp-color-popover-container");
  if (container) container.remove();
  container = document.createElement("div");
  container.className = "hyp-color-popover-container";
  panelEl.insertBefore(container, panelEl.firstChild);
```

## Final `.shell-panel` DOM structure (document open, popover mounted)

```
<aside class="shell-panel" id="shell-panel">
  <div class="hyp-color-popover-container">   (firstChild, owned solely by color-popover.js)
    <style>…</style>
    <div class="hyp-color-panel">
      <div>…Palette Tokens…<div class="hyp-token-list">…</div></div>
      <div class="hyp-element-section">
        <div class="hyp-color-header">Selected Element</div>
        <div class="hyp-element-body">…Text / Background rows (+ Border row after F4)…</div>
      </div>
    </div>
  </div>
  <div class="outline-panel">…<div class="outline-list" id="outline-list">…</div></div>   (SURVIVES)
  <div class="comment-panel">…<div class="comment-threads" id="comment-threads">…</div>
       <div class="comment-unanchored" id="comment-unanchored"></div></div>                (SURVIVES)
</aside>
```

**Invariant:** `color-popover.js` only ever touches its own `.hyp-color-popover-container`; `#outline-list`, `#comment-threads`, `#comment-unanchored` are never wiped.
