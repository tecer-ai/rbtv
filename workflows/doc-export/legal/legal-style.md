# Legal Document Styling Conventions

Legal documents must use formal, unbranded appearance. Never apply company branding, logos, or colored headers to legal output.

## Visual Standards

| Element | Convention |
|---------|-----------|
| Font (PDF) | Calibri or Segoe UI (sans-serif system font) |
| Font (DOCX) | Calibri (set explicitly via `legal-docx-style.yaml`) |
| Page size | A4 (default); Letter for US jurisdictions |
| Margins | 25mm top/bottom, 20mm right, 30mm left (PDF); 2.5cm top/bottom, 3.0cm left, 2.0cm right (DOCX) |
| Header | None — no logo, no branding, no text |
| Footer | Page number only, centered |
| Table borders | Black (`#000000`), single line |
| Table header bg | Light gray (`#D9D9D9`) — no color |
| Body text color | Black (`#000000`) |
| Line spacing | 1.5 |

## Signature Blocks

Signature blocks must include:
- A horizontal line (50 chars wide in DOCX, underline in PDF)
- Party name in bold below the line
- Date field: `Data: ____/____/________`

## Style Artifacts

- **PDF:** Use `legal-pdf-style.css` in this folder. Pass via `--stylesheet`.
- **DOCX:** Use `legal-docx-style.yaml` in this folder. Pass via `--style`. The `md-to-docx.py` script's signature detection still applies — tables with "assinatura" or "signature" headers render as signature blocks.

## When No Style Is Provided

The `md-to-docx.py` built-in defaults (Outfit font, branded colors) are NOT acceptable for legal output. Always pass `legal-docx-style.yaml` explicitly. Never omit `--style` for legal DOCX generation.
