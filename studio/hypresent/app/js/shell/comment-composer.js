/**
 * app/js/shell/comment-composer.js
 *
 * Anchored comment composer popover, rendered in the PARENT document (A2).
 * Replaces window.prompt for new comments and replies (U7).
 *
 * Public contract:
 *   openComposer({ rect, mode, commentId, initialText, onSubmit }) -> { close }
 *     rect       : {left, top, width, height} in iframe-viewport coords (from a comment event)
 *     mode       : 'new' | 'reply' | 'edit'
 *     commentId  : required when mode === 'reply' or mode === 'edit'
 *     initialText: pre-filled textarea content for edit mode (default '')
 *     onSubmit   : (text:string, agentInstruction:boolean) => void  (called on save)
 *   Keys: Esc=cancel, Ctrl/Cmd+Enter=save, Enter=newline.
 */

let activePopover = null;

function closeActive() {
  if (activePopover && activePopover.parentNode) activePopover.parentNode.removeChild(activePopover);
  activePopover = null;
  document.removeEventListener("keydown", onDocKeyForActive, true);
}

let onDocKeyForActive = null;

export function openComposer({ rect, mode = "new", commentId = null, initialText = "", onSubmit }) {
  closeActive();

  const pop = document.createElement("div");
  pop.className = "hyp-comment-composer";
  // Position relative to the iframe's on-screen offset within the parent page.
  const frame = document.querySelector("iframe.doc-frame");
  const fb = frame ? frame.getBoundingClientRect() : { left: 0, top: 0 };
  const left = (fb.left + (rect ? rect.left : 20));
  // anchorTop = on-screen top of the anchored element; belowTop = composer's default
  // position just under the anchor. We may flip to ABOVE the anchor if the composer
  // would overflow the viewport bottom (it is position:fixed and cannot scroll into view).
  const anchorTop = (fb.top + (rect ? rect.top : 20));
  const belowTop = (fb.top + (rect ? rect.top + (rect.height || 0) : 20));
  pop.style.position = "fixed";
  pop.style.left = Math.max(8, left) + "px";
  pop.style.top = Math.max(8, belowTop) + "px";   // provisional; clamped after append (height known)
  // Stash for the post-append viewport clamp.
  pop.dataset.hypAnchorTop = String(anchorTop);
  pop.dataset.hypBelowTop = String(belowTop);
  pop.style.zIndex = "1000000";

  const textarea = document.createElement("textarea");
  textarea.className = "hyp-composer-textarea";
  textarea.rows = 3;
  textarea.placeholder = mode === "reply" ? "Reply…" : mode === "edit" ? "Edit comment" : "Comment…";
  if (mode === "edit") {
    textarea.value = initialText;
  }

  pop.appendChild(textarea);

  let agentCheckbox = null;
  if (mode === "new") {
    const label = document.createElement("label");
    label.className = "hyp-composer-agent";
    agentCheckbox = document.createElement("input");
    agentCheckbox.type = "checkbox";
    label.appendChild(agentCheckbox);
    label.appendChild(document.createTextNode(" For agents"));
    pop.appendChild(label);
  }

  const actions = document.createElement("div");
  actions.className = "hyp-composer-actions";
  const saveBtn = document.createElement("button");
  saveBtn.type = "button";
  saveBtn.className = "hyp-composer-save";
  saveBtn.textContent = "Save";
  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "hyp-composer-cancel";
  cancelBtn.textContent = "Cancel";
  actions.appendChild(saveBtn);
  actions.appendChild(cancelBtn);
  pop.appendChild(actions);

  function submit() {
    const text = textarea.value.trim();
    if (!text) { closeActive(); return; }
    const agent = !!(agentCheckbox && agentCheckbox.checked);
    closeActive();
    onSubmit(text, agent);
  }

  saveBtn.addEventListener("click", submit);
  cancelBtn.addEventListener("click", () => closeActive());

  // Key handling on the textarea (S17).
  textarea.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { e.stopPropagation(); e.preventDefault(); closeActive(); return; }
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.stopPropagation(); e.preventDefault(); submit(); return; }
    if (e.key === "Enter" && !e.shiftKey) { e.stopPropagation(); e.preventDefault(); submit(); return; }
    // Shift+Enter falls through → inserts a newline (default textarea behavior)
  });

  // Ctrl/Cmd+Enter anywhere in the composer submits (e.g. while the For-agents checkbox has focus).
  pop.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); submit(); }
  });

  // Esc anywhere closes (capture).
  onDocKeyForActive = (e) => { if (e.key === "Escape") { e.preventDefault(); closeActive(); } };
  document.addEventListener("keydown", onDocKeyForActive, true);

  document.body.appendChild(pop);
  // Viewport clamp (V3-T18 BLOCKER C): a position:fixed composer below the fold is
  // "visible & stable" but un-actionable (cannot scroll into view) — its agent checkbox
  // then never receives the click. Measure the real height now and keep the whole
  // composer inside the viewport: flip above the anchor on bottom overflow, else clamp.
  {
    const M = 8, GAP = 6;
    const h = pop.offsetHeight || 0;
    const vh = window.innerHeight;
    const anchorTop = parseFloat(pop.dataset.hypAnchorTop) || 0;
    let top = parseFloat(pop.style.top) || 0;
    if (top + h > vh - M) {
      const flipped = anchorTop - h - GAP;            // place composer fully above the anchor
      top = (flipped >= M) ? flipped : Math.max(M, vh - h - M);
      pop.style.top = top + "px";
    }
  }
  delete pop.dataset.hypAnchorTop;
  delete pop.dataset.hypBelowTop;
  activePopover = pop;
  textarea.focus();

  return { close: closeActive };
}
