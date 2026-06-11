/**
 * app/js/shell/confirm-modal.js
 * In-app confirm modal for the save-before-switch step.
 *   confirmSaveOverwrite(fileName) -> Promise<"proceed" | "saveas" | "cancel">
 */
export function confirmSaveOverwrite(fileName) {
  return new Promise((resolve) => {
    const scrim = document.createElement("div");
    scrim.className = "hyp-modal-scrim";
    scrim.style.cssText =
      "position:fixed; inset:0; z-index:1000001; display:flex; align-items:center; justify-content:center; background:rgba(27,31,42,.35);";

    const card = document.createElement("div");
    card.style.cssText =
      "background:var(--white,#fff); border-radius:10px; box-shadow:0 2px 8px rgba(27,31,42,.10),0 24px 48px rgba(27,31,42,.14); width:420px; max-width:92vw; padding:22px 24px; font-family:var(--font-ui),sans-serif;";

    const title = document.createElement("div");
    title.style.cssText = "font-size:15px; font-weight:700; color:var(--ink,#1B1F2A); margin-bottom:8px;";
    title.textContent = "Save over the original file?";

    const body = document.createElement("div");
    body.style.cssText = "font-size:13px; line-height:1.5; color:var(--ink-mut,#5B6172); margin-bottom:18px;";
    body.textContent =
      "Your changes will overwrite “" + (fileName || "the file you opened") +
      "” — the file you opened initially. Proceed, or save as a new file to keep the original?";

    const actions = document.createElement("div");
    actions.style.cssText = "display:flex; gap:8px; justify-content:flex-end;";

    const saveAsBtn = document.createElement("button");
    saveAsBtn.type = "button";
    saveAsBtn.textContent = "Save As…";
    saveAsBtn.style.cssText =
      "height:34px; padding:0 14px; font-size:13px; font-weight:600; border:1px solid var(--line-2,#CFC9BA); border-radius:6px; background:var(--white,#fff); color:var(--ink,#1B1F2A); cursor:pointer;";

    const proceedBtn = document.createElement("button");
    proceedBtn.type = "button";
    proceedBtn.textContent = "Overwrite & continue";
    proceedBtn.style.cssText =
      "height:34px; padding:0 14px; font-size:13px; font-weight:600; border:1px solid var(--ink,#1B1F2A); border-radius:6px; background:var(--ink,#1B1F2A); color:var(--paper,#FAF8F4); cursor:pointer;";

    let done = false;
    function close(choice) {
      if (done) return;
      done = true;
      document.removeEventListener("keydown", onKey, true);
      if (scrim.parentNode) scrim.parentNode.removeChild(scrim);
      resolve(choice);
    }
    function onKey(e) {
      if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close("cancel"); }
    }

    saveAsBtn.addEventListener("click", () => close("saveas"));
    proceedBtn.addEventListener("click", () => close("proceed"));
    scrim.addEventListener("click", (e) => { if (e.target === scrim) close("cancel"); });
    document.addEventListener("keydown", onKey, true);

    actions.appendChild(saveAsBtn);
    actions.appendChild(proceedBtn);
    card.appendChild(title);
    card.appendChild(body);
    card.appendChild(actions);
    scrim.appendChild(card);
    document.body.appendChild(scrim);
    proceedBtn.focus();
  });
}
