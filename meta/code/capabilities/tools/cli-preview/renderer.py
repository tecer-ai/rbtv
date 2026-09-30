"""Reusable offline-HTML renderer for a CLI output review.

Extracted from the one-off rbtv-cli-ux preview generator. Same layout, CSS,
search/navigation/copy controls; only the title, disclaimer, and screen data
are parameters now. No network, no external assets, no dependencies.
"""
from __future__ import annotations

import html
import json

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root {
    --bg: #0c0f0c;
    --panel: #12160f;
    --border: #1f2a1a;
    --green: #39ff6a;
    --green-dim: #1f9c42;
    --green-faint: #0f5c25;
    --text-muted: #7fae82;
    --focus: #baffcf;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0;
    padding: 0;
    background: var(--bg);
    color: var(--green);
    font-family: "Consolas", "Courier New", ui-monospace, monospace;
    height: 100%;
  }
  body {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }
  a { color: var(--green); }
  button, input {
    font-family: inherit;
    font-size: inherit;
  }
  button:focus-visible, input:focus-visible, a:focus-visible, [tabindex]:focus-visible {
    outline: 2px solid var(--focus);
    outline-offset: 2px;
  }

  header.top {
    border-bottom: 1px solid var(--border);
    padding: 10px 16px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    align-items: baseline;
    background: var(--panel);
  }
  header.top h1 {
    font-size: 15px;
    margin: 0;
    font-weight: bold;
    letter-spacing: 0.02em;
  }
  header.top .disclaimer {
    color: var(--text-muted);
    font-size: 12px;
  }

  .layout {
    display: flex;
    flex: 1;
    min-height: 0;
  }

  #sidebar-toggle {
    display: none;
  }

  aside.sidebar {
    width: 300px;
    flex: 0 0 300px;
    border-right: 1px solid var(--border);
    background: var(--panel);
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .sidebar-search {
    padding: 10px;
    border-bottom: 1px solid var(--border);
  }
  .sidebar-search input {
    width: 100%;
    background: var(--bg);
    border: 1px solid var(--green-dim);
    color: var(--green);
    padding: 6px 8px;
  }
  .sidebar-search input::placeholder { color: var(--text-muted); }
  .sidebar-count {
    color: var(--text-muted);
    font-size: 11px;
    margin-top: 4px;
  }
  nav.screen-list {
    overflow-y: auto;
    flex: 1;
    padding: 4px 0 16px;
  }
  nav.screen-list h2 {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    margin: 14px 10px 4px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 2px;
  }
  .screen-entry {
    display: block;
    width: 100%;
    text-align: left;
    background: none;
    border: none;
    color: var(--green-dim);
    padding: 5px 10px;
    cursor: pointer;
    font-size: 12.5px;
    line-height: 1.3;
  }
  .screen-entry:hover { background: #16210f; color: var(--green); }
  .screen-entry.active {
    background: #16210f;
    color: var(--green);
    border-left: 3px solid var(--green);
    padding-left: 7px;
  }
  .screen-entry .num { color: var(--text-muted); margin-right: 4px; }
  .no-results {
    color: var(--text-muted);
    padding: 10px;
    font-size: 12px;
  }

  main.detail {
    flex: 1;
    overflow-y: auto;
    padding: 18px 22px 40px;
    min-width: 0;
  }
  .meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 18px;
    color: var(--text-muted);
    font-size: 12px;
    margin-bottom: 10px;
  }
  .meta-row strong { color: var(--green-dim); }
  h2.screen-title {
    margin: 0 0 6px;
    font-size: 18px;
    color: var(--green);
  }
  .field-block {
    margin: 12px 0;
  }
  .field-label {
    color: var(--text-muted);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
  }
  .cmd-block {
    background: var(--panel);
    border: 1px solid var(--border);
    padding: 8px 10px;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 13px;
  }
  .scenario-text {
    color: #b9e6be;
    font-size: 13px;
    line-height: 1.5;
  }
  .copy-row {
    display: flex;
    gap: 8px;
    margin-top: 6px;
  }
  button.copy-btn {
    background: var(--bg);
    border: 1px solid var(--green-dim);
    color: var(--green);
    padding: 3px 9px;
    cursor: pointer;
    font-size: 11px;
  }
  button.copy-btn:hover { background: #16210f; }
  button.copy-btn[data-state="ok"] { border-color: var(--green); }
  button.copy-btn[data-state="fail"] { border-color: #ff6a6a; color: #ff9a9a; }

  .terminal-wrap {
    display: inline-block;
    max-width: 100%;
    overflow-x: auto;
    border: 1px solid var(--green-faint);
    background: #060906;
    box-shadow: 0 0 12px rgba(57,255,106,0.06) inset;
  }
  pre.terminal-content {
    margin: 0;
    padding: 12px 14px;
    color: var(--green);
    font-size: 13px;
    line-height: 1.45;
    white-space: pre;
  }

  .nav-controls {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    margin-top: 24px;
    border-top: 1px solid var(--border);
    padding-top: 14px;
  }
  button.pager {
    background: var(--panel);
    border: 1px solid var(--green-dim);
    color: var(--green);
    padding: 8px 16px;
    cursor: pointer;
  }
  button.pager:hover:not(:disabled) { background: #16210f; }
  button.pager:disabled {
    color: var(--text-muted);
    border-color: var(--border);
    cursor: not-allowed;
  }

  footer.status {
    border-top: 1px solid var(--border);
    padding: 6px 16px;
    font-size: 11px;
    color: var(--text-muted);
    background: var(--panel);
  }

  @media (max-width: 760px) {
    #sidebar-toggle {
      display: inline-block;
      background: var(--panel);
      border: 1px solid var(--green-dim);
      color: var(--green);
      padding: 6px 12px;
      cursor: pointer;
    }
    aside.sidebar {
      position: fixed;
      top: 0;
      left: 0;
      bottom: 0;
      z-index: 20;
      transform: translateX(-100%);
      transition: transform 0.15s ease;
      width: 82vw;
      max-width: 320px;
    }
    aside.sidebar.open { transform: translateX(0); }
    main.detail { padding: 14px; }
    .layout { position: relative; }
  }
</style>
</head>
<body>

<header class="top">
  <button id="sidebar-toggle" aria-expanded="false" aria-controls="sidebar">☰ Screens</button>
  <h1>__TITLE__</h1>
  <span class="disclaimer">__DISCLAIMER__</span>
</header>

<div class="layout">
  <aside class="sidebar" id="sidebar">
    <div class="sidebar-search">
      <label for="search-input" class="field-label">Search screens</label>
      <input id="search-input" type="text" placeholder="id, title, command, category..." autocomplete="off">
      <div class="sidebar-count" id="result-count"></div>
    </div>
    <nav class="screen-list" id="screen-list" aria-label="Screen navigation"></nav>
  </aside>

  <main class="detail" id="detail" tabindex="-1"></main>
</div>

<footer class="status" id="status-bar"></footer>

<script type="application/json" id="screen-data">__SCREEN_DATA__</script>
<script>
(function () {
  "use strict";
  var screens = JSON.parse(document.getElementById("screen-data").textContent);
  var byId = {};
  var idxById = {};
  screens.forEach(function (s, i) { byId[s.id] = s; idxById[s.id] = i; });

  var state = { currentId: screens[0].id, query: "" };

  var sidebar = document.getElementById("sidebar");
  var sidebarToggle = document.getElementById("sidebar-toggle");
  var screenList = document.getElementById("screen-list");
  var searchInput = document.getElementById("search-input");
  var resultCount = document.getElementById("result-count");
  var detail = document.getElementById("detail");
  var statusBar = document.getElementById("status-bar");

  function matches(s, q) {
    if (!q) return true;
    var hay = (s.id + " " + s.title + " " + s.category + " " + s.command).toLowerCase();
    return hay.indexOf(q) !== -1;
  }

  function groupByCategory(list) {
    var groups = [];
    var seen = {};
    list.forEach(function (s) {
      if (!seen[s.category]) {
        seen[s.category] = { category: s.category, items: [] };
        groups.push(seen[s.category]);
      }
      seen[s.category].items.push(s);
    });
    return groups;
  }

  function renderList() {
    var q = state.query.trim().toLowerCase();
    var filtered = screens.filter(function (s) { return matches(s, q); });
    screenList.innerHTML = "";
    resultCount.textContent = filtered.length + " of " + screens.length + " screens";

    if (filtered.length === 0) {
      var empty = document.createElement("div");
      empty.className = "no-results";
      empty.textContent = "No screens match that search.";
      screenList.appendChild(empty);
      return;
    }

    var groups = groupByCategory(filtered);
    groups.forEach(function (g) {
      var h = document.createElement("h2");
      h.textContent = g.category;
      screenList.appendChild(h);
      g.items.forEach(function (s) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "screen-entry" + (s.id === state.currentId ? " active" : "");
        btn.setAttribute("data-id", s.id);
        if (s.id === state.currentId) btn.setAttribute("aria-current", "true");
        var numSpan = document.createElement("span");
        numSpan.className = "num";
        numSpan.textContent = String(s.id).padStart(2, "0") + ".";
        btn.appendChild(numSpan);
        btn.appendChild(document.createTextNode(s.title));
        btn.addEventListener("click", function () {
          selectScreen(s.id, true);
          sidebar.classList.remove("open");
          sidebarToggle.setAttribute("aria-expanded", "false");
        });
        screenList.appendChild(btn);
      });
    });
  }

  function copyText(text, btn) {
    function ok() {
      btn.setAttribute("data-state", "ok");
      btn.textContent = "Copied";
      setTimeout(function () { btn.setAttribute("data-state", ""); btn.textContent = btn.dataset.label; }, 1400);
    }
    function fail() {
      btn.setAttribute("data-state", "fail");
      btn.textContent = "Copy failed";
      setTimeout(function () { btn.setAttribute("data-state", ""); btn.textContent = btn.dataset.label; }, 1800);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(ok, fail);
      return;
    }
    try {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      var success = document.execCommand("copy");
      document.body.removeChild(ta);
      success ? ok() : fail();
    } catch (e) {
      fail();
    }
  }

  function makeCopyButton(label, text) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "copy-btn";
    b.textContent = label;
    b.dataset.label = label;
    b.addEventListener("click", function () { copyText(text, b); });
    return b;
  }

  function renderDetail(s) {
    detail.innerHTML = "";

    var title = document.createElement("h2");
    title.className = "screen-title";
    title.textContent = "Screen " + String(s.id).padStart(2, "0") + " — " + s.title;
    detail.appendChild(title);

    var meta = document.createElement("div");
    meta.className = "meta-row";
    function metaItem(label, value) {
      var span = document.createElement("span");
      var strong = document.createElement("strong");
      strong.textContent = label + ": ";
      span.appendChild(strong);
      span.appendChild(document.createTextNode(value));
      return span;
    }
    meta.appendChild(metaItem("Category", s.category));
    meta.appendChild(metaItem("Terminal width", s.width));
    meta.appendChild(metaItem("Exit code", s.exitCode));
    meta.appendChild(metaItem("Output format", s.type === "json" ? "JSON (undecorated)" : "plain text"));
    if (s.stream && s.stream !== "stdout" && !s.stderrContent) {
      meta.appendChild(metaItem("Stream", s.stream));
    }
    detail.appendChild(meta);

    var cmdBlock = document.createElement("div");
    cmdBlock.className = "field-block";
    var cmdLabel = document.createElement("div");
    cmdLabel.className = "field-label";
    cmdLabel.textContent = "Command(s)";
    cmdBlock.appendChild(cmdLabel);
    var cmdPre = document.createElement("div");
    cmdPre.className = "cmd-block";
    cmdPre.textContent = s.command;
    cmdBlock.appendChild(cmdPre);
    var cmdCopyRow = document.createElement("div");
    cmdCopyRow.className = "copy-row";
    cmdCopyRow.appendChild(makeCopyButton("Copy command", s.command.replace(/`/g, "")));
    cmdBlock.appendChild(cmdCopyRow);
    detail.appendChild(cmdBlock);

    if (s.scenario) {
      var scBlock = document.createElement("div");
      scBlock.className = "field-block";
      var scLabel = document.createElement("div");
      scLabel.className = "field-label";
      scLabel.textContent = "Scenario / fixture notes";
      scBlock.appendChild(scLabel);
      var scText = document.createElement("div");
      scText.className = "scenario-text";
      scText.textContent = s.scenario;
      scBlock.appendChild(scText);
      detail.appendChild(scBlock);
    }

    function terminalWrap(text) {
      var wrap = document.createElement("div");
      wrap.className = "terminal-wrap";
      var pre = document.createElement("pre");
      pre.className = "terminal-content";
      var widthNum = parseInt(s.width, 10);
      if (!isNaN(widthNum)) {
        pre.style.width = widthNum + "ch";
      }
      pre.textContent = text;
      wrap.appendChild(pre);
      return wrap;
    }

    if (s.stderrContent) {
      var outStdout = document.createElement("div");
      outStdout.className = "field-block";
      var lblOut = document.createElement("div");
      lblOut.className = "field-label";
      lblOut.textContent = "Simulated terminal output — stdout";
      outStdout.appendChild(lblOut);
      outStdout.appendChild(terminalWrap(s.content));
      var rowOut = document.createElement("div");
      rowOut.className = "copy-row";
      rowOut.appendChild(makeCopyButton("Copy stdout", s.content));
      outStdout.appendChild(rowOut);
      detail.appendChild(outStdout);

      var outStderr = document.createElement("div");
      outStderr.className = "field-block";
      var lblErr = document.createElement("div");
      lblErr.className = "field-label";
      lblErr.textContent = "Simulated terminal output — stderr";
      outStderr.appendChild(lblErr);
      outStderr.appendChild(terminalWrap(s.stderrContent));
      var rowErr = document.createElement("div");
      rowErr.className = "copy-row";
      rowErr.appendChild(makeCopyButton("Copy stderr", s.stderrContent));
      outStderr.appendChild(rowErr);
      detail.appendChild(outStderr);
    } else {
      var outBlock = document.createElement("div");
      outBlock.className = "field-block";
      var outLabel = document.createElement("div");
      outLabel.className = "field-label";
      outLabel.textContent = "Simulated terminal output";
      outBlock.appendChild(outLabel);
      outBlock.appendChild(terminalWrap(s.content));

      var outCopyRow = document.createElement("div");
      outCopyRow.className = "copy-row";
      outCopyRow.appendChild(makeCopyButton("Copy output", s.content));
      outBlock.appendChild(outCopyRow);
      detail.appendChild(outBlock);
    }

    var navRow = document.createElement("div");
    navRow.className = "nav-controls";
    var prevBtn = document.createElement("button");
    prevBtn.type = "button";
    prevBtn.className = "pager";
    prevBtn.textContent = "← Previous";
    var curIdx = idxById[s.id];
    var prevScreen = curIdx > 0 ? screens[curIdx - 1] : null;
    prevBtn.disabled = !prevScreen;
    prevBtn.addEventListener("click", function () { if (prevScreen) selectScreen(prevScreen.id, true); });
    var nextBtn = document.createElement("button");
    nextBtn.type = "button";
    nextBtn.className = "pager";
    nextBtn.textContent = "Next →";
    var nextScreen = curIdx < screens.length - 1 ? screens[curIdx + 1] : null;
    nextBtn.disabled = !nextScreen;
    nextBtn.addEventListener("click", function () { if (nextScreen) selectScreen(nextScreen.id, true); });
    navRow.appendChild(prevBtn);
    navRow.appendChild(nextBtn);
    detail.appendChild(navRow);
  }

  function selectScreen(id, focusDetail) {
    if (!byId[id]) return;
    state.currentId = id;
    renderList();
    renderDetail(byId[id]);
    statusBar.textContent = "Screen " + (idxById[id] + 1) + " of " + screens.length + " — " + byId[id].category;
    if (focusDetail) {
      detail.focus();
    }
    if (window.location.hash !== "#" + id) {
      try {
        history.replaceState(null, "", "#" + id);
      } catch (e) {
        // Some contexts (e.g. a file:// origin) refuse hash-only history
        // writes; deep-linking is a nice-to-have, so fail silently.
      }
    }
  }

  searchInput.addEventListener("input", function () {
    state.query = searchInput.value;
    renderList();
  });

  sidebarToggle.addEventListener("click", function () {
    var open = sidebar.classList.toggle("open");
    sidebarToggle.setAttribute("aria-expanded", open ? "true" : "false");
  });

  var startId = screens[0].id;
  var hashId = parseInt((window.location.hash || "").replace("#", ""), 10);
  if (byId[hashId]) startId = hashId;

  renderList();
  selectScreen(startId, false);
})();
</script>
</body>
</html>
"""


def render(title: str, disclaimer: str, screens: list[dict]) -> str:
    """Render the offline preview HTML for a list of screen dicts.

    Each screen dict needs: id (int), title, category, command, width,
    scenario, exitCode, type ("text"|"json"), content, and optionally
    stream ("stdout"|"stderr") and stderrContent (present only for a
    two-stream screen; content then holds the stdout half). Title and
    disclaimer are escaped for safe HTML-context embedding; screen fields
    are rendered client-side via textContent (see template script), so they
    are embedded as JSON, never string-interpolated into the surrounding
    markup. Every "<" in that JSON is escaped to "\\u003c" (not just
    "</script>") so no payload byte can trigger the HTML parser's script
    end-tag or comment-open states (e.g. a payload literally containing
    "<!--<script>").
    """
    ordered = sorted(screens, key=lambda s: s["id"])
    data_json = json.dumps(ordered, ensure_ascii=False).replace("<", "\\u003c")
    out = HTML_TEMPLATE.replace("__TITLE__", html.escape(title))
    out = out.replace("__DISCLAIMER__", html.escape(disclaimer))
    out = out.replace("__SCREEN_DATA__", data_json)
    return out
