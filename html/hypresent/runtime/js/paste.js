/**
 * runtime/js/paste.js
 *
 * Float-paste under the cursor, insert-paste into layout (with FLIP),
 * grid fallback, and whole-slide duplicate.
 */

import { get, bumpCascade } from "./clipboard.js";
import { paste as makePasteCommand } from "./commands.js";
import { tag, idOf, byId, roleOf } from "./element-registry.js";
import { push as historyPush } from "./history.js";
import { current, select } from "./selection.js";
import { mount } from "./interaction.js";
import { reanchorAfterMove } from "./comments.js";

// --- helpers ---

function regionInView() {
  const regions = Array.from(document.body.children).filter((c) => c.getAttribute("data-hyp-id"));
  if (regions.length === 0) return null;
  const cx = window.innerWidth / 2;
  const cy = window.innerHeight / 2;
  for (const r of regions) {
    const rect = r.getBoundingClientRect();
    if (cx >= rect.left && cx <= rect.right && cy >= rect.top && cy <= rect.bottom) {
      return r;
    }
  }
  return regions[0];
}

// --- public API ---

export function pasteFloat(x, y) {
  const slot = get();
  if (!slot) return;
  if (slot.wasRegion) return pasteRegion();

  const clone = slot.node.cloneNode(true);
  const slide =
    document.elementFromPoint(x, y)?.closest("section,.slide,[data-hyp-region]") ||
    regionInView();
  if (!slide) return;

  const cascadeAtPush = slot.cascade;
  clone.style.position = "absolute";
  const prevPos = slide.style.position;

  const cmd = makePasteCommand(clone, slide.getAttribute("data-hyp-id"), null);

  historyPush({
    do() {
      cmd.do();
      if (getComputedStyle(slide).position === "static") {
        slide.style.position = "relative";
      }
      tag();
      const cloneRect = clone.getBoundingClientRect();
      const slideRect = slide.getBoundingClientRect();
      clone.style.left = `${x - slideRect.left - cloneRect.width / 2 + cascadeAtPush * 16}px`;
      clone.style.top = `${y - slideRect.top - cloneRect.height / 2 + cascadeAtPush * 16}px`;
    },
    undo() {
      cmd.undo();
      slide.style.position = prevPos;
    },
    label: "paste-float",
  });

  const id = idOf(clone);
  if (id) {
    select(id);
    mount(id);
  }
  bumpCascade();
}

export function pasteIntoLayout(x, y) {
  const slot = get();
  if (!slot) return;
  if (slot.wasRegion) return pasteRegion();

  const info = current();
  if (!info || !info.hypId) return pasteFloat(x, y);
  const target = byId(info.hypId);
  if (!target) return pasteFloat(x, y);

  const parent = target.parentElement;
  const pd = parent ? getComputedStyle(parent).display : "";
  if (pd === "grid" || pd === "inline-grid" || roleOf(target) === "grid-child") {
    return pasteFloat(x, y);
  }

  const clone = slot.node.cloneNode(true);
  const cmd = makePasteCommand(
    clone,
    parent.getAttribute("data-hyp-id"),
    target.nextElementSibling?.getAttribute("data-hyp-id") ?? null
  );

  // FLIP FIRST snapshot — displaced siblings only (clone not yet inserted).
  const affected = Array.from(parent.children).filter((c) => c.getAttribute("data-hyp-id"));
  const first = new Map();
  for (const elx of affected) first.set(elx, elx.getBoundingClientRect());

  historyPush({
    do() {
      cmd.do();
      tag();
    },
    undo() {
      cmd.undo();
    },
    label: "paste-into-layout",
  });

  // FLIP PLAY
  requestAnimationFrame(() => {
    for (const [elx, before] of first) {
      const after = elx.getBoundingClientRect();
      const dx = before.left - after.left;
      const dy = before.top - after.top;
      if (dx || dy) {
        elx.style.transition = "none";
        elx.style.transform = `translate(${dx}px, ${dy}px)`;
        requestAnimationFrame(() => {
          elx.style.transition = "transform 180ms ease";
          elx.style.transform = "";
          setTimeout(() => {
            elx.style.transition = "";
            if (elx.style.transform === "") elx.style.removeProperty("transform");
          }, 220);
        });
      }
    }
  });

  const id = idOf(clone);
  if (id) select(id);
  reanchorAfterMove();
}

export function pasteRegion() {
  const slot = get();
  const clone = slot.node.cloneNode(true);

  const curRegion =
    byId(current()?.hypId)?.closest("section,.slide,[data-hyp-region]") ||
    regionInView();

  const cmd = makePasteCommand(
    clone,
    null,
    curRegion?.nextElementSibling?.getAttribute("data-hyp-id") ?? null
  );

  historyPush({
    do() {
      cmd.do();
      tag();
    },
    undo() {
      cmd.undo();
    },
    label: "paste-region",
  });

  const id = idOf(clone);
  if (id) select(id);
}
