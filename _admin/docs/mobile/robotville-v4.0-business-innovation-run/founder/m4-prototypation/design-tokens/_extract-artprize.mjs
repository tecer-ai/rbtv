// Design Token Extractor for artprize-shadows.com
// Uses Playwright to navigate, interact, and extract all CSS/computed styles

import { chromium } from 'playwright';
import { writeFileSync, mkdirSync } from 'fs';
import { dirname } from 'path';

const OUTPUT_PATH = 'H:/repos/BMAD/_bmad/rbtv/_admin-output/design-tokens/artprize-shadows.dom-deep-scan.json';
const URL = 'https://artprize-shadows.com/';
const VIEWPORT = { width: 1440, height: 900 };

function log(msg) { console.log(`[EXTRACT] ${msg}`); }

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: VIEWPORT });
  const page = await context.newPage();

  log('Navigating to ' + URL);
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 60000 });
  await sleep(3000);
  log('Page loaded.');

  // --- Phase 1: Discover content ---
  const interactionNotes = [];

  // Look for entry CTAs
  log('Looking for entry CTAs...');
  const ctaSelectors = [
    'text=/start exploring/i',
    'text=/scroll to know more/i',
    'text=/enter/i',
    'text=/begin/i',
    'text=/explore/i',
    'text=/discover/i',
    'text=/start/i',
    'button',
    'a[href="#"]',
    '.cta',
    '[class*="cta"]',
    '[class*="enter"]',
    '[class*="start"]',
  ];

  for (const sel of ctaSelectors) {
    try {
      const els = await page.$$(sel);
      for (const el of els) {
        const text = (await el.textContent())?.trim() || '';
        const visible = await el.isVisible();
        if (visible && text.length < 50) {
          log(`  Found CTA: "${text}" (${sel})`);
          interactionNotes.push(`Clicked CTA: "${text}"`);
          try {
            await el.click({ timeout: 3000 });
            await sleep(2000);
          } catch (e) {
            log(`  Click failed: ${e.message}`);
          }
        }
      }
    } catch (e) { /* selector not found */ }
  }

  // Scroll through entire page slowly
  log('Scrolling through entire page...');
  const scrollHeight = await page.evaluate(() => document.body.scrollHeight);
  const viewportHeight = VIEWPORT.height;
  let scrollPos = 0;
  let sectionCount = 0;

  while (scrollPos < scrollHeight) {
    await page.evaluate(y => window.scrollTo({ top: y, behavior: 'smooth' }), scrollPos);
    await sleep(1500);
    scrollPos += Math.floor(viewportHeight * 0.7);
    sectionCount++;

    // Check for new content that may have loaded
    const newHeight = await page.evaluate(() => document.body.scrollHeight);
    if (newHeight > scrollHeight) {
      log(`  Page grew from ${scrollHeight} to ${newHeight}px`);
    }
  }
  interactionNotes.push(`Scrolled through ${sectionCount} viewport increments, total height: ${scrollHeight}px`);
  log(`Scrolled through ${sectionCount} sections.`);

  // Scroll back to top
  await page.evaluate(() => window.scrollTo(0, 0));
  await sleep(1000);

  // Look for artwork cards/panels
  log('Looking for artwork cards...');
  const artworkArtists = ['Jumairy', 'YOKOMAE', 'BOUAYAD', 'Rintaro Fuse', 'Hamra Abbas', 'Ahmed Al-Aqra', 'Ryoichi Kurokawa'];
  for (const artist of artworkArtists) {
    try {
      const el = await page.$(`text=${artist}`);
      if (el) {
        const visible = await el.isVisible();
        log(`  Found "${artist}" (visible: ${visible})`);
        if (visible) {
          interactionNotes.push(`Found artwork by ${artist}`);
          try {
            await el.click({ timeout: 3000 });
            await sleep(2000);
            interactionNotes.push(`Clicked artwork "${artist}" - detail view`);
            // Go back / close overlay
            await page.keyboard.press('Escape');
            await sleep(1000);
          } catch (e) {
            log(`  Click on ${artist} failed: ${e.message}`);
          }
        }
      }
    } catch (e) { /* not found */ }
  }

  // Also try clicking any card-like elements
  const cardSelectors = [
    '[class*="card"]', '[class*="artwork"]', '[class*="piece"]',
    '[class*="project"]', '[class*="item"]', '[class*="slide"]',
    'article', '.swiper-slide',
  ];
  for (const sel of cardSelectors) {
    try {
      const els = await page.$$(sel);
      if (els.length > 0) {
        log(`  Found ${els.length} elements matching ${sel}`);
        interactionNotes.push(`Found ${els.length} elements matching ${sel}`);
        // Click first visible one
        for (const el of els.slice(0, 3)) {
          const visible = await el.isVisible();
          if (visible) {
            try {
              await el.click({ timeout: 2000 });
              await sleep(2000);
              await page.keyboard.press('Escape');
              await sleep(1000);
            } catch (e) { /* */ }
            break;
          }
        }
      }
    } catch (e) { /* */ }
  }

  // Check navigation menus
  log('Checking navigation...');
  const navSelectors = ['nav', '[class*="nav"]', '[class*="menu"]', 'header', '[class*="header"]', '[role="navigation"]'];
  for (const sel of navSelectors) {
    try {
      const els = await page.$$(sel);
      if (els.length > 0) {
        interactionNotes.push(`Found ${els.length} ${sel} elements`);
        log(`  Found ${els.length} elements matching ${sel}`);
      }
    } catch (e) { /* */ }
  }

  // Scroll through page once more to trigger any lazy-loaded content
  log('Second scroll pass for lazy content...');
  for (let y = 0; y < scrollHeight; y += viewportHeight) {
    await page.evaluate(pos => window.scrollTo(0, pos), y);
    await sleep(800);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await sleep(1000);

  // --- Phase 2: Extract ALL styles ---
  log('Extracting styles from DOM...');

  const extractionResult = await page.evaluate(() => {
    // Helper: rgb/rgba to hex
    function rgbToHex(color) {
      if (!color || color === 'transparent' || color === 'rgba(0, 0, 0, 0)') return color;
      const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
      if (!match) return color;
      const r = parseInt(match[1]);
      const g = parseInt(match[2]);
      const b = parseInt(match[3]);
      const a = match[4] !== undefined ? parseFloat(match[4]) : 1;
      const hex = '#' + [r, g, b].map(x => x.toString(16).padStart(2, '0')).join('');
      if (a < 1) return hex + Math.round(a * 255).toString(16).padStart(2, '0');
      return hex;
    }

    const result = {
      cssCustomProperties: {},
      stylesheetRules: {
        colors: [],
        typography: [],
        spacing: [],
        layout: [],
        effects: [],
      },
      computedStyles: {
        typography: [],
        colors: [],
        borderRadius: [],
        boxShadow: [],
        transitions: [],
      },
      mediaQueries: [],
      zIndexLayers: [],
    };

    // --- 1. Extract stylesheet rules ---
    const colorProps = ['color', 'background-color', 'background', 'border-color'];
    const typoProps = ['font-family', 'font-size', 'font-weight', 'line-height', 'letter-spacing', 'text-transform'];
    const spacingProps = ['padding', 'margin', 'gap', 'padding-top', 'padding-bottom', 'padding-left', 'padding-right', 'margin-top', 'margin-bottom', 'margin-left', 'margin-right'];
    const layoutProps = ['max-width', 'width', 'display', 'grid-template-columns', 'grid-template-rows', 'flex-direction', 'justify-content', 'align-items'];
    const effectProps = ['border-radius', 'box-shadow', 'opacity', 'transition', 'animation', 'transform', 'filter', 'backdrop-filter', 'border'];

    const seenRules = new Set();
    const mediaQuerySet = new Set();
    const zIndexMap = new Map();

    function processRule(rule) {
      if (rule instanceof CSSStyleRule) {
        const selector = rule.selectorText;
        const style = rule.style;

        for (let i = 0; i < style.length; i++) {
          const prop = style[i];
          const val = style.getPropertyValue(prop).trim();
          if (!val) continue;

          const key = `${selector}|${prop}|${val}`;
          if (seenRules.has(key)) continue;
          seenRules.add(key);

          const entry = { selector, property: prop, value: val };

          if (colorProps.includes(prop)) result.stylesheetRules.colors.push(entry);
          else if (typoProps.includes(prop)) result.stylesheetRules.typography.push(entry);
          else if (spacingProps.includes(prop)) result.stylesheetRules.spacing.push(entry);
          else if (layoutProps.includes(prop)) result.stylesheetRules.layout.push(entry);
          else if (effectProps.includes(prop)) result.stylesheetRules.effects.push(entry);

          // CSS custom properties in values
          if (prop.startsWith('--')) {
            result.cssCustomProperties[prop] = val;
          }

          // Z-index
          if (prop === 'z-index') {
            if (!zIndexMap.has(val)) zIndexMap.set(val, []);
            zIndexMap.get(val).push(selector);
          }
        }
      } else if (rule instanceof CSSMediaRule) {
        mediaQuerySet.add(rule.conditionText || rule.media.mediaText);
        for (const childRule of rule.cssRules) {
          processRule(childRule);
        }
      } else if (rule instanceof CSSKeyframesRule) {
        result.stylesheetRules.effects.push({
          selector: `@keyframes ${rule.name}`,
          property: 'animation',
          value: Array.from(rule.cssRules).map(r => `${r.keyText}: ${r.style.cssText}`).join(' | ')
        });
      }
    }

    for (const sheet of document.styleSheets) {
      try {
        for (const rule of sheet.cssRules) {
          processRule(rule);
        }
      } catch (e) {
        // Cross-origin stylesheet, skip
      }
    }

    // --- 2. CSS custom properties from root/html/body ---
    const rootStyle = getComputedStyle(document.documentElement);
    for (let i = 0; i < rootStyle.length; i++) {
      const prop = rootStyle[i];
      if (prop.startsWith('--')) {
        result.cssCustomProperties[prop] = rootStyle.getPropertyValue(prop).trim();
      }
    }

    // Check inline styles for custom properties
    document.querySelectorAll('[style]').forEach(el => {
      const inlineStyle = el.getAttribute('style') || '';
      const matches = inlineStyle.matchAll(/(--[\w-]+)\s*:\s*([^;]+)/g);
      for (const m of matches) {
        result.cssCustomProperties[m[1]] = m[2].trim();
      }
    });

    // --- 3. Computed font stacks ---
    const fontCombos = new Set();
    const colorSet = new Set();
    const bgColorSet = new Set();
    const borderColorSet = new Set();
    const borderRadiusSet = new Set();
    const boxShadowSet = new Set();
    const transitionSet = new Set();
    const animationSet = new Set();

    const allElements = document.querySelectorAll('*');
    for (const el of allElements) {
      const cs = getComputedStyle(el);

      // Font combos - only for elements with visible text
      if (el.childNodes.length > 0) {
        let hasText = false;
        for (const child of el.childNodes) {
          if (child.nodeType === 3 && child.textContent.trim()) {
            hasText = true;
            break;
          }
        }
        if (hasText) {
          const combo = JSON.stringify({
            fontFamily: cs.fontFamily,
            fontSize: cs.fontSize,
            fontWeight: cs.fontWeight,
            lineHeight: cs.lineHeight,
            letterSpacing: cs.letterSpacing,
            color: rgbToHex(cs.color),
            textTransform: cs.textTransform,
          });
          fontCombos.add(combo);
        }
      }

      // Colors
      const color = rgbToHex(cs.color);
      if (color && color !== 'transparent' && color !== 'rgba(0, 0, 0, 0)') colorSet.add(color);

      const bgColor = rgbToHex(cs.backgroundColor);
      if (bgColor && bgColor !== 'transparent' && bgColor !== 'rgba(0, 0, 0, 0)') bgColorSet.add(bgColor);

      const bdrColor = rgbToHex(cs.borderColor);
      if (bdrColor && bdrColor !== 'transparent' && bdrColor !== 'rgba(0, 0, 0, 0)') borderColorSet.add(bdrColor);

      // Border radius
      const br = cs.borderRadius;
      if (br && br !== '0px') borderRadiusSet.add(br);

      // Box shadow
      const bs = cs.boxShadow;
      if (bs && bs !== 'none') boxShadowSet.add(bs);

      // Transitions
      const tr = cs.transition;
      if (tr && tr !== 'all 0s ease 0s' && tr !== 'none 0s ease 0s' && tr !== 'none') transitionSet.add(tr);

      // Animations
      const an = cs.animationName;
      if (an && an !== 'none') {
        animationSet.add(JSON.stringify({
          name: an,
          duration: cs.animationDuration,
          timingFunction: cs.animationTimingFunction,
          delay: cs.animationDelay,
          iterationCount: cs.animationIterationCount,
        }));
      }

      // Z-index from computed
      const zi = cs.zIndex;
      if (zi && zi !== 'auto') {
        const tag = el.tagName.toLowerCase();
        const cls = el.className ? (typeof el.className === 'string' ? '.' + el.className.split(' ').join('.') : '') : '';
        const id = el.id ? '#' + el.id : '';
        const selector = tag + id + cls;
        if (!zIndexMap.has(zi)) zIndexMap.set(zi, []);
        const arr = zIndexMap.get(zi);
        if (!arr.includes(selector)) arr.push(selector);
      }
    }

    // --- 4. Layout containers ---
    const layoutContainers = [];
    for (const el of allElements) {
      const cs = getComputedStyle(el);
      const display = cs.display;
      const maxWidth = cs.maxWidth;
      const hasGrid = display === 'grid' || display === 'inline-grid';
      const hasFlex = display === 'flex' || display === 'inline-flex';

      if (hasGrid || hasFlex || (maxWidth !== 'none' && maxWidth !== '0px')) {
        const tag = el.tagName.toLowerCase();
        const cls = el.className ? (typeof el.className === 'string' ? el.className.split(' ').slice(0, 3).join('.') : '') : '';
        const container = {
          element: tag + (cls ? '.' + cls : ''),
          display,
        };
        if (maxWidth !== 'none') container.maxWidth = maxWidth;
        if (hasGrid) {
          container.gridTemplateColumns = cs.gridTemplateColumns;
          container.gridTemplateRows = cs.gridTemplateRows;
          container.gap = cs.gap;
        }
        if (hasFlex) {
          container.flexDirection = cs.flexDirection;
          container.justifyContent = cs.justifyContent;
          container.alignItems = cs.alignItems;
          container.gap = cs.gap;
        }
        layoutContainers.push(container);
      }
    }

    // Deduplicate layout containers by stringified key
    const layoutSeen = new Set();
    const dedupedLayout = [];
    for (const lc of layoutContainers) {
      const key = JSON.stringify(lc);
      if (!layoutSeen.has(key)) {
        layoutSeen.add(key);
        dedupedLayout.push(lc);
      }
    }

    // Assemble computed styles
    result.computedStyles.typography = [...fontCombos].map(c => JSON.parse(c));
    result.computedStyles.colors = [
      ...([...colorSet].map(c => ({ value: c, usage: 'text-color' }))),
      ...([...bgColorSet].map(c => ({ value: c, usage: 'background-color' }))),
      ...([...borderColorSet].map(c => ({ value: c, usage: 'border-color' }))),
    ];

    // Deduplicate colors by value+usage
    const colorSeen = new Set();
    result.computedStyles.colors = result.computedStyles.colors.filter(c => {
      const key = c.value + '|' + c.usage;
      if (colorSeen.has(key)) return false;
      colorSeen.add(key);
      return true;
    });

    result.computedStyles.borderRadius = [...borderRadiusSet];
    result.computedStyles.boxShadow = [...boxShadowSet];
    result.computedStyles.transitions = [...transitionSet];
    result.computedStyles.animations = [...animationSet].map(a => JSON.parse(a));

    result.mediaQueries = [...mediaQuerySet];
    result.zIndexLayers = [...zIndexMap.entries()].map(([value, selectors]) => ({
      zIndex: value,
      selectors: selectors.slice(0, 10), // limit for readability
    })).sort((a, b) => parseInt(a.zIndex) - parseInt(b.zIndex));

    result.layoutContainers = dedupedLayout.slice(0, 200); // limit

    return result;
  });

  log('Extraction complete.');

  // Build final output
  const output = {
    url: URL,
    timestamp: new Date().toISOString(),
    viewport: VIEWPORT,
    cssCustomProperties: extractionResult.cssCustomProperties,
    stylesheetRules: extractionResult.stylesheetRules,
    computedStyles: extractionResult.computedStyles,
    mediaQueries: extractionResult.mediaQueries,
    zIndexLayers: extractionResult.zIndexLayers,
    layoutContainers: extractionResult.layoutContainers,
    interactionNotes: interactionNotes.join('\n'),
  };

  // Save
  mkdirSync(dirname(OUTPUT_PATH), { recursive: true });
  writeFileSync(OUTPUT_PATH, JSON.stringify(output, null, 2), 'utf-8');
  log(`Saved to ${OUTPUT_PATH}`);

  // Print summary
  const allUniqueColors = new Set(output.computedStyles.colors.map(c => c.value));
  const allFontFamilies = new Set(output.computedStyles.typography.map(t => t.fontFamily));
  const allFontSizes = new Set(output.computedStyles.typography.map(t => t.fontSize));

  console.log('\n=== SUMMARY ===');
  console.log(`Unique colors: ${allUniqueColors.size}`);
  console.log(`Unique font families: ${allFontFamilies.size}`);
  console.log(`Unique font sizes: ${allFontSizes.size}`);
  console.log(`Media query breakpoints: ${output.mediaQueries.length}`);
  console.log(`CSS custom properties: ${Object.keys(output.cssCustomProperties).length}`);
  console.log(`Z-index layers: ${output.zIndexLayers.length}`);
  console.log(`Stylesheet color rules: ${output.stylesheetRules.colors.length}`);
  console.log(`Stylesheet typography rules: ${output.stylesheetRules.typography.length}`);
  console.log(`Stylesheet effect rules: ${output.stylesheetRules.effects.length}`);
  console.log(`Layout containers: ${output.layoutContainers?.length || 0}`);
  console.log(`Typography combos: ${output.computedStyles.typography.length}`);
  console.log(`Box shadows: ${output.computedStyles.boxShadow.length}`);
  console.log(`Border radii: ${output.computedStyles.borderRadius.length}`);
  console.log(`Transitions: ${output.computedStyles.transitions.length}`);
  console.log(`Animations: ${output.computedStyles.animations?.length || 0}`);
  console.log(`\nInteraction notes:\n${interactionNotes.join('\n')}`);

  await browser.close();
  log('Done.');
}

main().catch(e => {
  console.error('FATAL:', e);
  process.exit(1);
});
