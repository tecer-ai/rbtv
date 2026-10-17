#!/usr/bin/env node
'use strict';

// Suite for lib/canvas-markdown.js: a real canvas, as Slack returned it on 2026-10-17 for a canvas made from SAMPLE,
// comes back as SAMPLE; and the edge cases of the shapes it reads.

const assert = require('node:assert/strict');
const { canvasMarkdown } = require('./lib/canvas-markdown.js');

const tests = [];
const test = (name, fn) => tests.push({ name, fn });

// The Markdown the canvas was made from, and the HTML files.info's url_private_download returned for it (the guard).
const SAMPLE = "# Canvas round-trip test\n\nA paragraph with **bold**, _italic_, `code` and a [link](https://example.com).\n\n## A list\n\n- first item\n- second item with `inline code`\n  - nested item\n\n1. one\n2. two\n\n- [ ] an open task\n- [x] a done task\n\n## A table\n\n| Name | Value |\n|---|---|\n| alpha | 1 |\n| beta | 2 |\n\n```\na code block\n  with indentation\n```\n\n> A quote line.\n";
const RETURNED = "<div class=\"quip-canvas-content\"><h1 id=\"temp:C:FVYfbd3244e486b99aa7b635889c\">Fabinho canvas test</h1><h1 id=\"temp:C:FVY9f11444cc9ad7635ca0e6b8be\">Canvas round-trip test</h1><p id=\"temp:C:FVY23c7fa60a8063464142a05e01\" class=\"line\">A paragraph with <b>bold</b>, <i>italic</i>, <code>code</code> and a <lnk href=\"https://example.com\">link</lnk>.</p><h2 id=\"temp:C:FVY8fd4eb0c86ffe6eef58111151\">A list</h2><div data-section-style='5' class=\"list-numbering-restart-at\" style=\"--indent0: 0\"><ul id='temp:C:FVYc491dec6a1380827bc15dd24a'><li id='temp:C:FVY0ce3c7bd45d7cc82d62660b5c' value='1'><span id=\"temp:C:FVY0ce3c7bd45d7cc82d62660b5c\">first item</span><br/></li><li id='temp:C:FVYab9380c5ac4158987abeee5ae'><span id=\"temp:C:FVYab9380c5ac4158987abeee5ae\">second item with <code>inline code</code></span><br/></li><ul><li id='temp:C:FVY01631a59230e174f84e641a0c'><span id=\"temp:C:FVY01631a59230e174f84e641a0c\">nested item</span><br/></li></ul></ul></div><div data-section-style='6' class=\"list-numbering-restart-at\" style=\"--indent0: 0\"><ul id='temp:C:FVY8aff59571a202d88164fd7032'><li id='temp:C:FVY5266de9483f8f64d3e467cd27' value='1'><span id=\"temp:C:FVY5266de9483f8f64d3e467cd27\">one</span><br/></li><li id='temp:C:FVY419360c3d7593baff1349b637'><span id=\"temp:C:FVY419360c3d7593baff1349b637\">two</span><br/></li></ul></div><div data-section-style='7' class=\"list-numbering-restart-at\" style=\"--indent0: 0\"><ul id='temp:C:FVY48f1474d395962a91acad2bc6'><li id='temp:C:FVY7f78f23927583d656bd7c83a1' value='1'><span id=\"temp:C:FVY7f78f23927583d656bd7c83a1\">an open task</span><br/></li><li id='temp:C:FVY403914a5615eb9fd8d74bff92' class='checked'><span id=\"temp:C:FVY403914a5615eb9fd8d74bff92\">a done task</span><br/></li></ul></div><h2 id=\"temp:C:FVYcce4812c69c37b1155d7cf6ce\">A table</h2><table><tr><td><p id=\"temp:C:FVYeeb9e7849c63ca8e8caef1129\" class=\"line\">Name</p></td><td><p id=\"temp:C:FVY5c4ef05dc43c59e8102e81b2f\" class=\"line\">Value</p></td></tr><tr><td><p id=\"temp:C:FVY4d36b9188163ede100b206ac6\" class=\"line\">alpha</p></td><td><p id=\"temp:C:FVY475a711505acc3ca46c6aedba\" class=\"line\">1</p></td></tr><tr><td><p id=\"temp:C:FVY6ed3652f0c1adfc930da2a9e3\" class=\"line\">beta</p></td><td><p id=\"temp:C:FVY836c0b934d16574a9034ac83c\" class=\"line\">2</p></td></tr></table><p id=\"temp:C:FVY60a4839be4ca0b5a8c1e91e9b\" class=\"prettyprint line\">a code block<br>\u00a0\u00a0with indentation</p><p id=\"temp:C:FVYdd2a600502ffb181048df9286\" class=\"line\"></p><blockquote><p id=\"temp:C:FVY5010318eaa5ae1630e432e260\" class=\"line\">A quote line.</p></blockquote></div>";

test('a canvas made from Markdown comes back as that Markdown, its title heading dropped', () => {
  assert.equal(canvasMarkdown(RETURNED, { title: 'Fabinho canvas test' }), SAMPLE);
});

test('without the title the first heading stays', () => {
  assert.match(canvasMarkdown(RETURNED), /^# Fabinho canvas test\n\n# Canvas round-trip test\n/);
});

test('entities, strike, an unknown tag and a link without href keep their text', () => {
  const html = '<p class="line">a &amp; b &lt;c&gt; &#233; &#x41; <s>gone</s> <span>kept</span> <lnk>bare</lnk></p>';
  assert.equal(canvasMarkdown(html), 'a & b <c> é A ~~gone~~ kept bare\n');
});

test('emphasis wraps the words, not the spaces around them, and an empty paragraph is dropped', () => {
  assert.equal(canvasMarkdown('<p class="line">x<b> bold </b>y</p><p class="line"></p><p class="line">z</p>'), 'x **bold** y\n\nz\n');
});

test('a pipe inside a table cell is escaped', () => {
  assert.equal(canvasMarkdown('<table><tr><td><p>a|b</p></td><td><p>c</p></td></tr></table>'), '| a\\|b | c |\n|---|---|\n');
});

test('a divider comes back as ---', () => {
  assert.equal(canvasMarkdown("<p class=\"line\">above</p><hr style='width:100%'><h2>below</h2>"), 'above\n\n---\n\n## below\n');
});

let failed = 0;
for (const { name, fn } of tests) {
  try { fn(); console.log(`PASS ${name}`); } catch (error) { failed += 1; console.log(`FAIL ${name}: ${error.message}`); }
}
console.log(`canvas-markdown: ${tests.length - failed} passed, ${failed} failed`);
if (failed) process.exit(1);
