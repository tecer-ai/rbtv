#!/usr/bin/env node
/**
 * DOM/CSS design-token extraction for artprize-shadows.com
 * Run: node extract-dom-scan.mjs
 * Output: artprize-shadows.dom-scan.json
 */
import { chromium } from 'playwright';
import { writeFileSync, mkdirSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUTPUT_PATH = join(__dirname, 'artprize-shadows.dom-scan.json');
const URL = 'https://artprize-shadows.com/';
const VIEWPORT = { width: 1440, height: 900 };

const EXTRACT_SCRIPT = () => {
  const getComputed = (el, props) => {
    if (!el) return null;
    const s = window.getComputedStyle(el);
    const o = {};
    for (const p of props) o[p] = s.getPropertyValue(p) || s[p];
    return o;
  };

  const rootStyles = document.documentElement ? getComputed(document.documentElement,
    ['fontFamily', 'fontSize', 'fontWeight', 'lineHeight', 'letterSpacing', 'color', 'backgroundColor']) : null;
  const bodyStyles = document.body ? getComputed(document.body,
    ['fontFamily', 'fontSize', 'fontWeight', 'lineHeight', 'letterSpacing', 'color', 'backgroundColor', 'maxWidth', 'width', 'padding', 'margin']) : null;

  // CSS custom properties from :root
  const cssVars = {};
  if (document.documentElement) {
    const s = window.getComputedStyle(document.documentElement);
    for (let i = 0; i < s.length; i++) {
      const prop = s[i];
      if (prop.startsWith('--')) {
        const v = s.getPropertyValue(prop).trim();
        if (v) cssVars[prop] = v;
      }
    }
  }

  // Typography: scan elements with visible text, collect unique combos
  const typoMap = new Map();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT, null, false);
  let count = 0;
  const MAX = 2000;
  while (count < MAX && walker.nextNode()) {
    const el = walker.currentNode;
    if (el.nodeType !== 1) continue;
    const text = (el.innerText || '').trim();
    if (!text || el.offsetParent === null) continue;
    count++;
    const s = window.getComputedStyle(el);
    const key = `${s.fontFamily}|${s.fontSize}|${s.fontWeight}|${s.lineHeight}|${s.letterSpacing}|${s.color}`;
    const fontSize = parseFloat(s.fontSize) || 0;
    const existing = typoMap.get(key);
    if (!existing || existing.fontSize < fontSize) {
      typoMap.set(key, {
        fontFamily: s.fontFamily,
        fontSize: s.fontSize,
        fontWeight: s.fontWeight,
        lineHeight: s.lineHeight,
        letterSpacing: s.letterSpacing,
        color: s.color,
      });
    }
  }

  const typoEntries = Array.from(typoMap.values())
    .map(t => ({ ...t, fontSizeNum: parseFloat(t.fontSize) || 0 }))
    .sort((a, b) => b.fontSizeNum - a.fontSizeNum)
    .slice(0, 15)
    .map(({ fontSizeNum, ...rest }) => rest);

  // Color candidates
  const colorSet = new Set();
  const colorWalker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT, null, false);
  let cCount = 0;
  while (cCount < 2000 && colorWalker.nextNode()) {
    const el = colorWalker.currentNode;
    if (el.nodeType !== 1) continue;
    cCount++;
    const s = window.getComputedStyle(el);
    for (const p of ['color', 'backgroundColor', 'borderColor']) {
      const v = (s.getPropertyValue(p) || s[p] || '').trim();
      if (v && v !== 'rgba(0, 0, 0, 0)' && v !== 'transparent') colorSet.add(v);
    }
  }
  const colorCandidates = Array.from(colorSet).slice(0, 20);

  // Layout: body + largest area elements
  const layoutCandidates = [];
  if (document.body) {
    const s = window.getComputedStyle(document.body);
    layoutCandidates.push({
      selector: 'body',
      maxWidth: s.maxWidth,
      width: s.width,
      padding: s.padding,
      margin: s.margin,
      rect: document.body.getBoundingClientRect(),
    });
  }
  const all = document.querySelectorAll('*');
  const withRect = [];
  for (const el of all) {
    if (el === document.body) continue;
    const r = el.getBoundingClientRect();
    if (r.width > 100 && r.height > 100) withRect.push({ el, area: r.width * r.height, tag: el.tagName, id: el.id || '', className: (el.className || '').slice(0, 80) });
  }
  withRect.sort((a, b) => b.area - a.area);
  for (let i = 0; i < Math.min(5, withRect.length); i++) {
    const { el, tag, id, className } = withRect[i];
    const s = window.getComputedStyle(el);
    layoutCandidates.push({
      selector: `${tag}${id ? '#' + id : ''}${className ? '.' + className.split(/\s+/)[0] : ''}`,
      maxWidth: s.maxWidth,
      width: s.width,
      padding: s.padding,
      margin: s.margin,
      rect: el.getBoundingClientRect(),
    });
  }

  // Hero "Art" detection
  const bodyText = (document.body && document.body.innerText) ? document.body.innerText : '';
  const hasArtInDOM = /\bArt\b/.test(bodyText);
  const canvases = document.querySelectorAll('canvas');
  const svgs = document.querySelectorAll('svg');
  const heroSource = hasArtInDOM ? 'dom_text' : (canvases.length || svgs.length ? 'canvas_or_svg' : 'unknown');

  return {
    url: window.location.href,
    timestamp: new Date().toISOString(),
    viewport: { width: window.innerWidth, height: window.innerHeight },
    cssCustomProperties: cssVars,
    documentElement: rootStyles,
    body: bodyStyles,
    typographyCandidates: typoEntries,
    colorCandidates,
    layoutCandidates,
    heroArt: {
      inDOMText: hasArtInDOM,
      canvasCount: canvases.length,
      svgCount: svgs.length,
      inferredSource: heroSource,
    },
  };
};

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: VIEWPORT });
  const page = await context.newPage();

  try {
    await page.goto(URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1500);

    const data = await page.evaluate(EXTRACT_SCRIPT);
    data.limitations = [];

    if (Object.keys(data.cssCustomProperties).length === 0) data.limitations.push('No CSS custom properties found on :root');
    if (data.typographyCandidates.length < 3) data.limitations.push('Few typography candidates; page may be canvas/SVG-heavy');
    if (data.colorCandidates.length < 5) data.limitations.push('Few color candidates extracted');

    mkdirSync(dirname(OUTPUT_PATH), { recursive: true });
    writeFileSync(OUTPUT_PATH, JSON.stringify(data, null, 2), 'utf8');
    console.log(JSON.stringify(data, null, 2));
  } catch (e) {
    const fallback = {
      url: URL,
      timestamp: new Date().toISOString(),
      error: String(e.message),
      limitations: ['Extraction failed: ' + e.message],
      cssCustomProperties: {},
      typographyCandidates: [],
      colorCandidates: [],
      layoutCandidates: [],
      heroArt: { inDOMText: false, canvasCount: 0, svgCount: 0, inferredSource: 'unknown' },
    };
    writeFileSync(OUTPUT_PATH, JSON.stringify(fallback, null, 2), 'utf8');
    console.log(JSON.stringify(fallback, null, 2));
  } finally {
    await browser.close();
  }
}

main();
