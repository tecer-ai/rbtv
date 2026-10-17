'use strict';

// A Slack canvas, as files.info's url_private_download returns it (Quip HTML), turned back into Markdown, so that
// edits made in a canvas can be read as the Markdown it was written from.
//
// API
// canvasMarkdown(html, { title? }) → Markdown. Headings, paragraphs, bold, italics, strike, inline code, links,
//   bullet, numbered and checklist lists (nested), tables, code blocks, quotes and dividers come back as Markdown; any other
//   tag keeps its text. A first heading equal to title, which Slack adds from the canvas title, is dropped.
//
// Shapes read (observed 2026-10-17 on a canvas made from Markdown): <h1>..<h6>; <p class="line">; <b>, <i>, <s>,
// <code>, <lnk href>; <hr> (a divider); lists as <div data-section-style='5'> (bullets), '6' (numbers), '7' (checklist, a done item
// <li class='checked'>), with a nested <ul> for a nested level; <table><tr><td><p>; a code block as
// <p class="prettyprint"> with <br> between lines; <blockquote><p>.

const ENTITIES = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };
const VOID = new Set(['br', 'img', 'hr', 'meta', 'input']);
const LIST_STYLE = { 5: 'bullet', 6: 'number', 7: 'check' };

// Slack keeps a run of spaces as no-break spaces (U+00A0); Markdown needs them back as spaces.
function decode(text) {
  return text.replace(/\u00a0/g, ' ').replace(/&(#x[0-9a-f]+|#\d+|\w+);/gi, (whole, name) => {
    if (name[0] === '#') return String.fromCodePoint(name[1].toLowerCase() === 'x' ? parseInt(name.slice(2), 16) : Number(name.slice(1)));
    return ENTITIES[name.toLowerCase()] ?? whole;
  });
}

function attributes(source) {
  const attrs = {};
  for (const [, name, , double, single, bare] of source.matchAll(/([\w:-]+)(\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g)) {
    attrs[name.toLowerCase()] = decode(double ?? single ?? bare ?? '');
  }
  return attrs;
}

// The HTML as a tree of { tag, attrs, children } and text strings.
function parse(html) {
  const root = { tag: 'root', attrs: {}, children: [] };
  const stack = [root];
  for (const [, text, close, open, rest] of html.matchAll(/([^<]+)|<\/(\w+)[^>]*>|<(\w+)([^>]*)>/g)) {
    const top = stack[stack.length - 1];
    if (text != null) top.children.push(decode(text));
    else if (close) {
      const at = stack.map((node) => node.tag).lastIndexOf(close.toLowerCase());
      if (at > 0) stack.length = at;
    } else {
      const node = { tag: open.toLowerCase(), attrs: attributes(rest.replace(/\/$/, '')), children: [] };
      top.children.push(node);
      if (!VOID.has(node.tag) && !rest.trim().endsWith('/')) stack.push(node);
    }
  }
  return root;
}

const kids = (node, tag) => node.children.filter((child) => typeof child !== 'string' && child.tag === tag);

// Inline content as one line of Markdown.
function inline(node) {
  if (typeof node === 'string') return node;
  const inner = () => node.children.map(inline).join('');
  switch (node.tag) {
    case 'b': case 'strong': return wrap(inner(), '**');
    case 'i': case 'em': return wrap(inner(), '_');
    case 's': case 'del': return wrap(inner(), '~~');
    case 'code': return `\`${inner()}\``;
    case 'lnk': case 'a': return node.attrs.href ? `[${inner()}](${node.attrs.href})` : inner();
    case 'br': return '\n';
    case 'ul': case 'ol': return '';
    default: return inner();
  }
}

// Emphasis markers go around the words, never around their surrounding spaces.
function wrap(text, mark) {
  const [, lead, body, trail] = text.match(/^(\s*)([\s\S]*?)(\s*)$/);
  return body ? `${lead}${mark}${body}${mark}${trail}` : text;
}

function listLines(ul, style, depth) {
  const lines = [];
  let n = 0;
  for (const child of ul.children) {
    if (typeof child === 'string') continue;
    if (child.tag === 'ul' || child.tag === 'ol') {
      lines.push(...listLines(child, style, depth + 1));
      continue;
    }
    if (child.tag !== 'li') continue;
    n += 1;
    const marker = style === 'number' ? `${n}.` : style === 'check' ? `- [${/\bchecked\b/.test(child.attrs.class || '') ? 'x' : ' '}]` : '-';
    lines.push(`${'  '.repeat(depth)}${marker} ${inline(child).trim()}`);
    for (const nested of [...kids(child, 'ul'), ...kids(child, 'ol')]) lines.push(...listLines(nested, style, depth + 1));
  }
  return lines;
}

function table(node) {
  const rows = kids(node, 'tr').length ? kids(node, 'tr') : kids(node, 'tbody').flatMap((body) => kids(body, 'tr'));
  const cells = rows.map((row) => row.children.filter((cell) => typeof cell !== 'string')
    .map((cell) => inline(cell).trim().replace(/\n/g, ' ').replace(/\|/g, '\\|')));
  if (!cells.length) return '';
  const line = (row) => `| ${row.join(' | ')} |`;
  return [line(cells[0]), `|${cells[0].map(() => '---').join('|')}|`, ...cells.slice(1).map(line)].join('\n');
}

// Each block-level piece of a container as Markdown, in order.
function blocks(node) {
  const out = [];
  for (const child of node.children) {
    if (typeof child === 'string') {
      if (child.trim()) out.push(child.trim());
      continue;
    }
    const level = /^h([1-6])$/.exec(child.tag);
    if (level) out.push(`${'#'.repeat(Number(level[1]))} ${inline(child).trim()}`);
    else if (child.tag === 'hr') out.push('---');
    else if (child.tag === 'p' && /\bprettyprint\b/.test(child.attrs.class || '')) out.push(`\`\`\`\n${inline(child)}\n\`\`\``);
    else if (child.tag === 'p') {
      const text = inline(child).trim();
      if (text) out.push(text);
    } else if (child.tag === 'blockquote') out.push(blocks(child).join('\n\n').split('\n').map((line) => `> ${line}`.trimEnd()).join('\n'));
    else if (child.tag === 'table') out.push(table(child));
    else if (child.tag === 'ul' || child.tag === 'ol') out.push(listLines(child, child.tag === 'ol' ? 'number' : 'bullet', 0).join('\n'));
    else if (child.tag === 'div' && child.attrs['data-section-style'] in LIST_STYLE) {
      const style = LIST_STYLE[child.attrs['data-section-style']];
      out.push(child.children.filter((c) => typeof c !== 'string' && (c.tag === 'ul' || c.tag === 'ol'))
        .flatMap((list) => listLines(list, style, 0)).join('\n'));
    } else out.push(...blocks(child));
  }
  return out.filter(Boolean);
}

function canvasMarkdown(html, { title = null } = {}) {
  const parts = blocks(parse(String(html)));
  if (title != null && parts[0] === `# ${title.trim()}`) parts.shift();
  return `${parts.join('\n\n')}\n`;
}

module.exports = { canvasMarkdown };
