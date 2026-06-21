import { copyThemeAssets, libraryAsset, resolveLibrary } from "/app/js/api-client.js";

export function createThemeControls({
  bridge,
  els,
  getDeckPath,
  setStatus = () => {},
  markDirty = () => {},
}) {
  if (!els || !els.container || !els.select) {
    throw new Error("createThemeControls requires container and select elements");
  }

  const state = {
    deckPath: "",
    stamp: null,
    libraryPath: "",
    libraryRef: "",
    themes: [],
    applying: false,
    manualLibrary: false,
  };

  function currentBridge() {
    return typeof bridge === "function" ? bridge() : bridge;
  }

  function showMessage(text, type = "") {
    if (!els.message) return;
    if (!text) {
      els.message.hidden = true;
      els.message.textContent = "";
      els.message.className = "theme-message";
      return;
    }
    els.message.hidden = false;
    els.message.textContent = text;
    els.message.className = "theme-message" + (type ? " " + type : "");
  }

  function setLibraryLabel(text) {
    if (!els.library) return;
    if (!text) {
      els.library.hidden = true;
      els.library.textContent = "";
      els.library.removeAttribute("title");
      return;
    }
    els.library.hidden = false;
    els.library.textContent = text;
    els.library.title = text;
  }

  function setPickVisible(visible) {
    if (els.pickLibrary) els.pickLibrary.hidden = !visible;
  }

  function resetSelect() {
    els.select.innerHTML = "";
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "Theme";
    els.select.appendChild(option);
    els.select.disabled = true;
  }

  function setDisabled(disabled) {
    els.select.disabled = !!disabled;
    els.container.classList.toggle("is-disabled", !!disabled);
  }

  function resetForOpen() {
    state.deckPath = getDeckPath ? getDeckPath() || "" : "";
    state.stamp = null;
    state.libraryPath = "";
    state.libraryRef = "";
    state.themes = [];
    state.applying = false;
    state.manualLibrary = false;
    els.container.hidden = true;
    resetSelect();
    setLibraryLabel("");
    setPickVisible(false);
    showMessage("");
  }

  function renderThemes(currentTheme) {
    resetSelect();
    const themes = Array.isArray(state.themes) ? state.themes : [];
    for (const theme of themes) {
      if (!theme || !theme.name) continue;
      const option = document.createElement("option");
      option.value = theme.name;
      option.textContent = theme.name === "default" ? "[default]" : (theme.label || theme.name);
      option.dataset.contract = theme.contract_version || "";
      els.select.appendChild(option);
    }
    const wanted = currentTheme || "default";
    if (themes.some((theme) => theme && theme.name === wanted)) {
      els.select.value = wanted;
    } else if (themes.length > 0) {
      els.select.value = themes[0].name;
    }
    setDisabled(themes.length === 0);
  }

  function markLegacy() {
    // Pin the legacy flag so the apply-theme finally-guard (which re-enables the
    // select when hasStamp !== false) keeps the switcher disabled on a late
    // {ok:false, legacy:true} return — not just on the boot hasStamp:false signal.
    state.stamp = { ...(state.stamp || {}), hasStamp: false };
    els.container.hidden = false;
    resetSelect();
    setDisabled(true);
    setLibraryLabel("");
    setPickVisible(false);
    showMessage("this deck predates theme-switching", "warning");
  }

  async function resolveFromRef(libraryRef, manual = false) {
    const deckPath = state.deckPath || (getDeckPath ? getDeckPath() || "" : "");
    if (!deckPath) {
      resetSelect();
      setPickVisible(true);
      showMessage("Save this deck before switching themes.", "warning");
      return;
    }
    if (!libraryRef) {
      resetSelect();
      setPickVisible(true);
      showMessage("Pick a library to switch themes.", "warning");
      return;
    }

    showMessage("Resolving library...");
    const resolved = await resolveLibrary(deckPath, libraryRef);
    if (!resolved || !resolved.resolved) {
      resetSelect();
      setLibraryLabel("");
      setPickVisible(true);
      showMessage(resolved && resolved.reason ? resolved.reason : "Pick a library to switch themes.", "warning");
      return;
    }

    state.libraryPath = resolved.library_path || "";
    state.libraryRef = libraryRef;
    state.manualLibrary = !!manual;
    state.themes = Array.isArray(resolved.themes) ? resolved.themes : [];
    setLibraryLabel(manual ? state.libraryPath : libraryRef);
    setPickVisible(false);
    showMessage("");
    renderThemes(state.stamp && state.stamp.theme ? state.stamp.theme : resolved.default_theme || "default");
  }

  async function handleThemeStamp(payload) {
    state.deckPath = getDeckPath ? getDeckPath() || "" : "";
    state.stamp = payload || {};
    els.container.hidden = false;
    setLibraryLabel("");
    setPickVisible(false);
    showMessage("");

    if (!payload || payload.hasStamp === false) {
      markLegacy();
      return;
    }

    const libraryRef = payload.library || "";
    try {
      await resolveFromRef(libraryRef, false);
    } catch (err) {
      resetSelect();
      setPickVisible(true);
      showMessage("Library resolution failed: " + err.message, "error");
    }
  }

  async function pickLibrary() {
    let path = "";
    try {
      const response = await fetch("/api/dialog-folder", { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || response.statusText);
      if (data && data.cancelled) return;
      path = data && data.path ? data.path : "";
    } catch (err) {
      showMessage("Library picker failed: " + err.message, "error");
      return;
    }
    if (!path) return;
    try {
      await resolveFromRef(path, true);
    } catch (err) {
      resetSelect();
      setPickVisible(true);
      showMessage("Library resolution failed: " + err.message, "error");
    }
  }

  function selectedTheme(name) {
    return state.themes.find((theme) => theme && theme.name === name) || null;
  }

  async function applySelectedTheme() {
    if (state.applying) return;
    const themeName = els.select.value;
    if (!themeName) return;
    const theme = selectedTheme(themeName);
    if (!theme || !state.libraryPath) return;

    const currentTheme = state.stamp && state.stamp.theme ? state.stamp.theme : "default";
    if (themeName === currentTheme && !state.manualLibrary) {
      showMessage("");
      return;
    }

    state.applying = true;
    setDisabled(true);
    showMessage("Applying theme...");
    try {
      const assetName = themeName === "default" ? "theme.css" : "themes/" + themeName + ".css";
      const asset = await libraryAsset(state.libraryPath, assetName);
      const payload = {
        themeCss: asset.content || "",
        themeName,
        themeContract: theme.contract_version || "",
      };
      if (state.manualLibrary) payload.libraryRef = state.libraryRef;
      const runtimeBridge = currentBridge();
      if (!runtimeBridge) throw new Error("No document bridge is available");
      const result = await runtimeBridge.command("apply-theme", payload);
      if (result && result.blocked) {
        showMessage(result.reason || "Theme contract mismatch.", "warning");
        els.select.value = currentTheme;
        return;
      }
      if (result && result.legacy) {
        markLegacy();
        return;
      }
      if (!result || result.ok !== true) {
        throw new Error(result && result.reason ? result.reason : "Theme apply failed");
      }

      const assetResult = await copyThemeAssets(state.deckPath, state.libraryPath, themeName);
      state.stamp = {
        theme: themeName,
        contract: theme.contract_version || "",
        library: state.libraryRef,
        hasStamp: true,
      };
      state.manualLibrary = false;
      markDirty();
      setStatus("");
      if (assetResult && Array.isArray(assetResult.missing) && assetResult.missing.length > 0) {
        showMessage("Missing theme assets: " + assetResult.missing.join(", "), "warning");
      } else {
        showMessage("");
      }
      setLibraryLabel(state.libraryRef);
    } catch (err) {
      showMessage("Theme switch failed: " + err.message, "error");
      els.select.value = currentTheme;
    } finally {
      state.applying = false;
      if (!(state.stamp && state.stamp.hasStamp === false) && state.themes.length > 0) {
        setDisabled(false);
      }
    }
  }

  els.select.addEventListener("change", applySelectedTheme);
  if (els.pickLibrary) els.pickLibrary.addEventListener("click", pickLibrary);

  resetForOpen();

  return {
    resetForOpen,
    handleThemeStamp,
  };
}
