let lastPointer = { x: 0, y: 0 };

export function initShortcuts(handlers) {
  document.addEventListener("mousemove", (e) => {
    lastPointer = { x: e.clientX, y: e.clientY };
  });

  document.addEventListener("keydown", (e) => {
    const ctrl = e.ctrlKey || e.metaKey;
    if (!ctrl) return;

    const ed = document.activeElement;
    const editing = !!(ed && ed.getAttribute && ed.getAttribute("contenteditable") === "true");

    // Bold
    if ((e.key === "b" || e.key === "B") && !e.altKey && !e.shiftKey) {
      e.preventDefault();
      handlers.bold();
      return;
    }

    // Italic
    if ((e.key === "i" || e.key === "I") && !e.altKey && !e.shiftKey) {
      e.preventDefault();
      handlers.italic();
      return;
    }

    // Comment for agents (Ctrl+Shift+M) — checked BEFORE plain Comment so Shift wins
    if ((e.key === "m" || e.key === "M") && !e.altKey && e.shiftKey) {
      e.preventDefault();
      handlers.requestAgentComment();
      return;
    }

    // Comment
    if ((e.key === "m" || e.key === "M") && !e.altKey && !e.shiftKey) {
      e.preventDefault();
      handlers.requestComment();
      return;
    }

    // Save (Ctrl+Shift+Q) — checked BEFORE Save As so Shift wins
    if ((e.key === "q" || e.key === "Q") && !e.altKey && e.shiftKey) {
      e.preventDefault();
      handlers.requestSave();
      return;
    }

    // Save As (Ctrl+Q)
    if ((e.key === "q" || e.key === "Q") && !e.altKey && !e.shiftKey) {
      e.preventDefault();
      handlers.requestSaveAs();
      return;
    }

    // Show shortcuts help
    if (e.key === "/" && !e.altKey && !e.shiftKey) {
      e.preventDefault();
      handlers.requestShortcutsHelp();
      return;
    }

    // Delete component (Ctrl+Del) — only when a component is selected and NOT editing
    if ((e.key === "Delete" || e.key === "Del" || e.code === "Delete") && !e.altKey && !e.shiftKey) {
      if (!editing) {
        e.preventDefault();
        handlers.deleteComponent();
      }
      return;
    }

    const textSelected = !!(window.getSelection() && !window.getSelection().isCollapsed);

    // Copy (Ctrl+C) — only when a component is selected and NOT editing and no real text selection
    if ((e.key === "c" || e.key === "C") && !e.altKey && !e.shiftKey) {
      if (!editing && !textSelected && handlers.copy && handlers.copy()) {
        e.preventDefault();
      }
      return;
    }

    // Paste float (Ctrl+V)
    if ((e.key === "v" || e.key === "V") && !e.altKey && !e.shiftKey) {
      if (!editing && !textSelected) {
        e.preventDefault();
        if (handlers.pasteFloat) handlers.pasteFloat(lastPointer.x, lastPointer.y);
      }
      return;
    }

    // Paste into layout (Ctrl+Shift+V)
    if ((e.key === "v" || e.key === "V") && !e.altKey && e.shiftKey) {
      if (!editing && !textSelected) {
        e.preventDefault();
        if (handlers.pasteLayout) handlers.pasteLayout(lastPointer.x, lastPointer.y);
      }
      return;
    }
  });
}
