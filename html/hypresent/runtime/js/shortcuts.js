export function initShortcuts(handlers) {
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

    // Comment
    if ((e.key === "c" || e.key === "C") && e.altKey && !e.shiftKey) {
      e.preventDefault();
      handlers.requestComment();
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
  });
}
