#!/usr/bin/env python3
"""
extract-subtle-refs — Extract motion and interaction character from a reference URL.

Produces a structured markdown report of animations, transitions, scroll behaviors,
hover states, and micro-interactions observed on the live page.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError as exc:
    print("ERROR: playwright is required. Install: python -m pip install playwright", file=sys.stderr)
    sys.exit(1)


def settle_page(page, timeout_ms=15000):
    """Wait for the page to reach a reasonably settled state."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except PWTimeout:
        pass
    # Extra safety sleep for late-loading SPA content
    time.sleep(2)
    # Try to wait for common animation containers to appear
    try:
        page.wait_for_selector("body", timeout=5000)
    except PWTimeout:
        pass


def extract_motion_data(page):
    """Run JS in the page to harvest motion/interaction metadata."""
    return page.evaluate("""() => {
        const results = [];
        const seen = new Set();

        function keyFor(el, type, prop) {
            return `${type}::${el.tagName}::${el.className}::${prop}`;
        }

        function pushObservation(pattern, anchor, values, note = "") {
            results.push({
                pattern,
                anchor,
                values,
                where_seen: window.location.href,
                note
            });
        }

        // 1. Computed transitions on all elements
        const allEls = document.querySelectorAll("*");
        allEls.forEach(el => {
            const cs = getComputedStyle(el);
            const tProp = cs.transitionProperty;
            const tDur = cs.transitionDuration;
            const tEase = cs.transitionTimingFunction;
            const tDelay = cs.transitionDelay;
            if (tProp && tProp !== "none" && tDur !== "0s") {
                const k = keyFor(el, "transition", tProp);
                if (!seen.has(k)) {
                    seen.add(k);
                    pushObservation(
                        "css-transition",
                        el.tagName.toLowerCase() + (el.id ? "#" + el.id : "") + (el.className && typeof el.className === "string" ? "." + el.className.split(/\\s+/).filter(Boolean).join(".") : ""),
                        { property: tProp, duration: tDur, easing: tEase, delay: tDelay },
                        "computed style"
                    );
                }
            }
        });

        // 2. Computed animations on all elements
        allEls.forEach(el => {
            const cs = getComputedStyle(el);
            const aName = cs.animationName;
            const aDur = cs.animationDuration;
            const aEase = cs.animationTimingFunction;
            const aDelay = cs.animationDelay;
            const aIter = cs.animationIterationCount;
            if (aName && aName !== "none" && aDur !== "0s") {
                const k = keyFor(el, "animation", aName);
                if (!seen.has(k)) {
                    seen.add(k);
                    pushObservation(
                        "css-animation",
                        el.tagName.toLowerCase() + (el.id ? "#" + el.id : "") + (el.className && typeof el.className === "string" ? "." + el.className.split(/\\s+/).filter(Boolean).join(".") : ""),
                        { name: aName, duration: aDur, easing: aEase, delay: aDelay, iteration_count: aIter },
                        "computed style"
                    );
                }
            }
        });

        // 3. @keyframes rules from stylesheets
        const keyframes = [];
        try {
            for (const sheet of document.styleSheets) {
                for (const rule of sheet.cssRules || []) {
                    if (rule.type === CSSRule.KEYFRAMES_RULE) {
                        keyframes.push({ name: rule.name, cssText: rule.cssText.substring(0, 400) });
                    }
                }
            }
        } catch (e) {
            // cross-origin stylesheets block cssRules access
        }
        if (keyframes.length > 0) {
            pushObservation(
                "keyframes-catalog",
                "document.stylesheets",
                { count: keyframes.length, names: keyframes.map(k => k.name) },
                "CSS @keyframes definitions"
            );
        }

        // 4. Scroll behavior
        const htmlCs = getComputedStyle(document.documentElement);
        const bodyCs = getComputedStyle(document.body);
        const scrollBehav = htmlCs.scrollBehavior || bodyCs.scrollBehavior || "auto";
        pushObservation(
            "scroll-behavior",
            "html / body",
            { scroll_behavior: scrollBehav },
            "computed style"
        );

        // 5. Hover-interaction scan: find rules that change on :hover
        const hoverTargets = [];
        try {
            for (const sheet of document.styleSheets) {
                for (const rule of sheet.cssRules || []) {
                    if (rule.selectorText && rule.selectorText.includes(":hover")) {
                        const hasMotion = /transform|opacity|transition|animation/.test(rule.cssText);
                        hoverTargets.push({
                            selector: rule.selectorText,
                            has_motion: hasMotion,
                            snippet: rule.cssText.substring(0, 300)
                        });
                    }
                }
            }
        } catch (e) {}
        if (hoverTargets.length > 0) {
            const motionHovers = hoverTargets.filter(h => h.has_motion);
            pushObservation(
                "hover-rules",
                "document.stylesheets",
                { total_hover_rules: hoverTargets.length, motion_hover_rules: motionHovers.length, examples: hoverTargets.slice(0, 5).map(h => h.selector) },
                "CSS :hover selectors"
            );
        }

        // 6. Detect common animation libraries
        const libs = [];
        if (window.gsap) libs.push("GSAP");
        if (window.anime) libs.push("anime.js");
        if (window.ScrollReveal) libs.push("ScrollReveal");
        if (window.AOS) libs.push("AOS");
        if (window.Velocity) libs.push("Velocity");
        if (window.motion) libs.push("Framer Motion");
        if (libs.length > 0) {
            pushObservation(
                "js-animation-library",
                "window",
                { detected: libs },
                "global library detection"
            );
        }

        // 7. IntersectionObserver / ResizeObserver presence (hints at scroll-triggered motion)
        // We can't detect existing observers, but we can check for common attributes
        const ioHints = document.querySelectorAll('[data-aos], [data-sr], [data-scroll]').length;
        if (ioHints > 0) {
            pushObservation(
                "scroll-trigger-hints",
                "DOM attributes",
                { elements_with_scroll_trigger_attrs: ioHints },
                "data-aos / data-sr / data-scroll attributes"
            );
        }

        // 8. Explicit no-motion flag when nothing meaningful is found
        const hasMotion = results.some(r =>
            ["css-transition", "css-animation", "keyframes-catalog", "hover-rules", "js-animation-library", "scroll-trigger-hints"].includes(r.pattern)
        );
        if (!hasMotion) {
            pushObservation(
                "no-detectable-motion",
                "page",
                {},
                "No CSS transitions, animations, hover motion rules, keyframes, JS animation libraries, or scroll-trigger attributes were detected."
            );
        }

        return results;
    }
    """)


def generate_markdown_report(url, observations):
    """Build a markdown report section for one URL."""
    lines = []
    lines.append(f"## {url}")
    lines.append("")
    if not observations:
        lines.append("**No motion or interaction patterns detected.**")
        lines.append("")
        return "\n".join(lines)

    # Group by pattern type
    groups = {}
    for obs in observations:
        groups.setdefault(obs["pattern"], []).append(obs)

    for pattern, items in groups.items():
        lines.append(f"### {pattern}")
        lines.append("")
        for obs in items:
            lines.append(f"- **Anchor:** `{obs['anchor']}`")
            lines.append(f"  - **Values:** `{json.dumps(obs['values'])}`")
            lines.append(f"  - **Note:** {obs['note']}")
            lines.append("")
    return "\n".join(lines)


def process_url(url, headless=True):
    """Load a URL and extract motion data. Returns (observations, error_string)."""
    observations = []
    error = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            settle_page(page)
            observations = extract_motion_data(page)
        except PWTimeout:
            error = f"Timeout loading {url}"
        except Exception as exc:
            error = f"Error loading {url}: {exc}"
        finally:
            browser.close()
    return observations, error


def main():
    parser = argparse.ArgumentParser(description="Extract motion/interaction character from reference URLs.")
    parser.add_argument("--url", action="append", required=True, help="URL to analyze (can be given multiple times)")
    parser.add_argument("--out", required=True, help="Output report path (.md)")
    parser.add_argument("--json-out", default=None, help="Optional JSON output path")
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode (for debugging)")
    args = parser.parse_args()

    out_path = Path(args.out)
    headless = not args.headed

    all_results = []
    any_error = False

    for url in args.url:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url

        observations, error = process_url(url, headless=headless)
        if error:
            print(f"ERROR: {error}", file=sys.stderr)
            any_error = True
            all_results.append({"url": url, "error": error, "observations": []})
        else:
            print(f"OK: {url} — {len(observations)} observation(s)", file=sys.stderr)
            all_results.append({"url": url, "observations": observations})

    # Determine if any URL succeeded
    any_success = any("error" not in r for r in all_results)

    if any_success:
        # Write markdown report
        md_lines = ["# Subtle Refs Report — Motion & Interaction Character", ""]
        md_lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append("")

        for result in all_results:
            if "error" in result:
                md_lines.append(f"## {result['url']}")
                md_lines.append("")
                md_lines.append(f"**ERROR:** {result['error']}")
                md_lines.append("")
            else:
                md_lines.append(generate_markdown_report(result["url"], result.get("observations", [])))

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(md_lines), encoding="utf-8")
        print(f"Report written to {out_path}", file=sys.stderr)

        # Optional JSON
        if args.json_out:
            json_path = Path(args.json_out)
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
            print(f"JSON written to {json_path}", file=sys.stderr)
    else:
        print("No report written — all URLs failed.", file=sys.stderr)

    if any_error:
        sys.exit(1)


if __name__ == "__main__":
    main()
