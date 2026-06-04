/**
 * app/js/shell/comment-composer.js
 *
 * Anchored comment composer popover, rendered in the PARENT document (A2).
 * Replaces window.prompt for new comments and replies (U7).
 *
 * Public contract:
 *   openComposer({ rect, mode, commentId, onSubmit }) -> { close }
 *     rect       : {left, top, width, height} in iframe-viewport coords (from a comment event)
 *     mode       : 'new' | 'reply'
 *     commentId  : required when mode === 'reply'
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

export function openComposer({ rect, mode = "new", commentId = null, onSubmit }) {
  closeActive();

  const pop = document.createElement("div");
  pop.className = "hyp-comment-composer";
  // Position relative to the iframe's on-screen offset within the parent page.
  const frame = document.querySelector("iframe.doc-frame");
  const fb = frame ? frame.getBoundingClientRect() : { left: 0, top: 0 };
  const left = (fb.left + (rect ? rect.left : 20));
  const top = (fb.top + (rect ? rect.top + (rect.height || 0) : 20));
  pop.style.position = "fixed";
  pop.style.left = Math.max(8, left) + "px";
  pop.style.top = Math.max(8, top) + "px";
  pop.style.zIndex = "1000000";

  const textarea = document.createElement("textarea");
  textarea.className = "hyp-composer-textarea";
  textarea.rows = 3;
  textarea.placeholder = mode === "reply" ? "Reply…" : "Comment…";

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
    if (e.key === "Escape") { e.preventDefault(); closeActive(); return; }
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); submit(); return; }
    // plain Enter falls through → inserts a newline (default textarea behavior)
  });

  // Esc anywhere closes (capture).
  onDocKeyForActive = (e) => { if (e.key === "Escape") { e.preventDefault(); closeActive(); } };
  document.addEventListener("keydown", onDocKeyForActive, true);

  document.body.appendChild(pop);
  activePopover = pop;
  textarea.focus();

  return { close: closeActive };
}
