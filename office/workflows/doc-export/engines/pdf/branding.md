# md-to-pdf Branding -- Headers, Footers, and Logos

## Headers and Footers

Headers/footers render in an **isolated context** -- your stylesheet CSS does NOT apply. Only inline styles and `<style>` tags inside the template work.

**Injectable class names** (Chromium auto-fills content):

| Class | Injected Content |
|-------|-----------------|
| `pageNumber` | Current page number |
| `totalPages` | Total page count |
| `date` | Formatted print date |
| `title` | Document title (from `document_title` or `--document-title`) |

**Critical rules:**
- Font size defaults to **1pt** -- always set explicitly
- Margin must accommodate header/footer height (e.g., top margin 35mm for a 20px header)
- External image URLs are unreliable -- use base64 data URLs
- A `<style>` tag in either template applies to both header and footer

## Including Logos

The **only reliable method** is base64 encoding via a `config.js` file. JSON config cannot use `fs.readFileSync()`.

```javascript
// config.js -- run: md-to-pdf --config-file config.js document.md
const fs = require('fs');
const path = require('path');

const logo = fs.readFileSync(path.resolve(__dirname, 'logo.png')).toString('base64');

module.exports = {
  stylesheet: [path.resolve(__dirname, 'style.css')],
  pdf_options: {
    format: 'A4',
    margin: '35mm 20mm 25mm 20mm',
    printBackground: true,
    headerTemplate: `
      <style>
        section {
          font-size: 10px;
          font-family: system-ui;
          width: 100%;
          padding: 0 20mm;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        img { height: 28px; }
      </style>
      <section>
        <span class="title" style="font-weight: 600;"></span>
        <img src="data:image/png;base64,${logo}" />
      </section>
    `,
    footerTemplate: `
      <div style="font-size: 9px; font-family: system-ui; color: #888; width: 100%; text-align: center;">
        Page <span class="pageNumber"></span> of <span class="totalPages"></span>
      </div>
    `,
  },
};
```

## Page Number Footer (no logo)

If you only need page numbers without a logo, use frontmatter instead of config.js:

```yaml
---
pdf_options:
  format: A4
  margin: 30mm 20mm 25mm 20mm
  footerTemplate: |-
    <div style="font-size: 9px; font-family: system-ui; color: #888; width: 100%; text-align: center;">
      Page <span class="pageNumber"></span> of <span class="totalPages"></span>
    </div>
---
```
