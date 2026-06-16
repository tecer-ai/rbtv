export function createShortcutsHelp() {
  let scrim = null;
  let card = null;
  let keydownHandler = null;

  function build() {
    scrim = document.createElement("div");
    scrim.className = "shortcuts-scrim";
    scrim.setAttribute("role", "dialog");
    scrim.setAttribute("aria-modal", "true");
    scrim.setAttribute("aria-label", "Keyboard shortcuts");
    scrim.setAttribute("tabindex", "-1");

    card = document.createElement("div");
    card.className = "shortcuts-card";

    const title = document.createElement("h2");
    title.textContent = "Keyboard shortcuts";
    card.appendChild(title);

    const groups = [
      {
        heading: "Text",
        rows: [
          { keys: ["Ctrl", "B"], label: "Bold" },
          { keys: ["Ctrl", "I"], label: "Italic" },
          { keys: ["A+"], label: "Bigger" },
          { keys: ["A−"], label: "Smaller" },
        ],
      },
      {
        heading: "Components",
        rows: [
          { keys: ["Ctrl", "C"], label: "Copy" },
          { keys: ["Ctrl", "V"], label: "Paste (float)" },
          { keys: ["Ctrl", "Shift", "V"], label: "Paste into layout" },
          { keys: ["Ctrl", "Del"], label: "Delete" },
        ],
      },
      {
        heading: "Editing",
        rows: [
          { keys: ["Ctrl", "M"], label: "Comment" },
          { keys: ["Ctrl", "Shift", "M"], label: "Comment for agents" },
          { keys: ["Ctrl", "Z"], label: "Undo" },
          { keys: ["Ctrl", "Shift", "Z"], label: "Redo" },
          { keys: ["Ctrl", "/"], label: "Show shortcuts" },
        ],
      },
      {
        heading: "File",
        rows: [
          { keys: ["Ctrl", "Shift", "Q"], label: "Save" },
          { keys: ["Ctrl", "Q"], label: "Save As" },
        ],
      },
    ];

    for (const g of groups) {
      const gh = document.createElement("div");
      gh.className = "shortcuts-group-heading caps";
      gh.textContent = g.heading;
      card.appendChild(gh);

      for (const r of g.rows) {
        const row = document.createElement("div");
        row.className = "shortcuts-row";

        const kbdWrap = document.createElement("div");
        kbdWrap.className = "shortcuts-keys";
        for (let i = 0; i < r.keys.length; i++) {
          const k = document.createElement("kbd");
          k.textContent = r.keys[i];
          kbdWrap.appendChild(k);
          if (i < r.keys.length - 1) {
            const sep = document.createElement("span");
            sep.textContent = "+";
            kbdWrap.appendChild(sep);
          }
        }
        row.appendChild(kbdWrap);

        const label = document.createElement("div");
        label.className = "shortcuts-label";
        label.textContent = r.label;
        row.appendChild(label);

        card.appendChild(row);
      }
    }

    scrim.appendChild(card);
    document.body.appendChild(scrim);

    scrim.addEventListener("click", (e) => {
      if (e.target === scrim) close();
    });
  }

  function open() {
    if (!scrim) build();
    scrim.classList.add("is-open");
    scrim.focus();
    if (!keydownHandler) {
      keydownHandler = (e) => {
        if (e.key === "Escape") close();
      };
      document.addEventListener("keydown", keydownHandler);
    }
  }

  function close() {
    if (scrim) scrim.classList.remove("is-open");
    if (keydownHandler) {
      document.removeEventListener("keydown", keydownHandler);
      keydownHandler = null;
    }
  }

  return { open };
}
