# md-to-pdf Styling -- CSS and Tables

## Custom Stylesheets

`--stylesheet` **replaces** the built-in CSS. To extend instead, use `--css` for inline additions.

GFM tables render as HTML tables. Column alignment (`:---:`, `---:`) is respected.

## Page Break CSS

```css
h1 { page-break-before: always; }
h1:first-child { page-break-before: avoid; }
h2, h3 { page-break-after: avoid; }
table, pre { page-break-inside: avoid; }
p { orphans: 3; widows: 3; }
.page-break { page-break-after: always; }
```

## Professional Stylesheet Template

```css
@page { size: A4; margin: 35mm 20mm 25mm 20mm; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 10pt;
  line-height: 1.7;
  color: #222;
}

h1 {
  font-size: 2em;
  color: #1a3a5c;
  border-bottom: 3px solid #1a3a5c;
  padding-bottom: 0.3em;
  page-break-after: avoid;
}

h2 {
  font-size: 1.4em;
  color: #1a3a5c;
  border-left: 4px solid #1a3a5c;
  padding-left: 0.5em;
  page-break-after: avoid;
}

h3 { font-size: 1.1em; page-break-after: avoid; }

table {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
  font-size: 0.9em;
  page-break-inside: avoid;
}

table th {
  background-color: #1a3a5c;
  color: white;
  padding: 0.6em 1em;
  text-align: left;
}

table td { padding: 0.5em 1em; border: 1px solid #ddd; }
table tr:nth-child(even) { background-color: #f5f7fa; }

pre {
  background-color: #f5f7fa;
  border: 1px solid #e1e4e8;
  border-radius: 4px;
  padding: 1em;
  white-space: pre-wrap;
  font-size: 0.85em;
  page-break-inside: avoid;
}

blockquote {
  border-left: 4px solid #1a3a5c;
  padding-left: 1em;
  color: #555;
  font-style: italic;
}

p { orphans: 3; widows: 3; }
```
