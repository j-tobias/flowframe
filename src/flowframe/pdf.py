"""Render a PDF (from a URL or local path) into a scrollable HTML page.

Headless Chromium has no built-in PDF viewer, so a PDF URL cannot simply be
navigated to and scrolled. Instead we rasterise every page to a PNG and stack
the images vertically in a plain HTML document, which the recorder then opens
and scrolls exactly like any other page.
"""

from __future__ import annotations

import html
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlparse

_HEADERS = {"User-Agent": "flowframe"}
_PDF_MAGIC = b"%PDF-"


def try_load_pdf(url: str, *, timeout: float = 60.0) -> bytes | None:
    """Return PDF bytes if *url* points at a PDF, otherwise ``None``.

    Handles ``http(s)`` URLs, ``file://`` URLs and bare local paths. Detection
    uses the ``.pdf`` suffix, the HTTP ``Content-Type`` header and the ``%PDF-``
    magic bytes, so a PDF served without a ``.pdf`` suffix is still caught while
    an HTML page is never mistaken for one. Returning ``None`` lets the caller
    fall back to ordinary page navigation.
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme in ("http", "https"):
        return _load_remote_pdf(url, parsed.path.lower().endswith(".pdf"), timeout)

    if scheme in ("file", ""):
        path = Path(unquote(parsed.path) if scheme == "file" else url)
        return _load_local_pdf(path)

    return None


def _load_remote_pdf(url: str, suffix_pdf: bool, timeout: float) -> bytes | None:
    # For non-.pdf URLs, probe Content-Type with a cheap HEAD before downloading
    # the body — avoids pulling down whole HTML pages just to discard them.
    if not suffix_pdf:
        try:
            head = urllib.request.Request(url, method="HEAD", headers=_HEADERS)
            with urllib.request.urlopen(head, timeout=timeout) as resp:
                ctype = resp.headers.get("Content-Type", "").lower()
        except OSError:
            return None
        if "application/pdf" not in ctype:
            return None

    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
    except OSError:
        return None

    return data if (suffix_pdf or data[:5] == _PDF_MAGIC) else None


def _load_local_pdf(path: Path) -> bytes | None:
    if not path.is_file():
        return None
    try:
        with path.open("rb") as fh:
            head = fh.read(5)
    except OSError:
        return None
    if head == _PDF_MAGIC or path.suffix.lower() == ".pdf":
        return path.read_bytes()
    return None


def render_pdf_to_html(pdf_bytes: bytes, dest_dir: Path, width: int) -> str:
    """Rasterise *pdf_bytes* into *dest_dir* and return a ``file://`` URL.

    Each page is rendered to a PNG roughly *width* pixels wide (for crispness at
    the recording viewport) and stacked vertically in an ``index.html`` styled
    to resemble a PDF viewer. Returns the URL to navigate the recorder to.

    Raises:
        ValueError: If the PDF contains no pages.
    """
    import pypdfium2 as pdfium

    dest_dir.mkdir(parents=True, exist_ok=True)

    document = pdfium.PdfDocument(pdf_bytes)
    try:
        page_count = len(document)
        if page_count == 0:
            raise ValueError("PDF contains no pages.")

        img_tags: list[str] = []
        for index in range(page_count):
            page = document[index]
            # Width in PDF points (1/72 inch). Render so the bitmap is ~`width`
            # px wide; clamp the scale so tiny/huge pages stay sensible.
            page_width_pt = page.get_size()[0] or 612.0
            scale = max(1.0, min(width / page_width_pt, 4.0))

            image = page.render(scale=scale).to_pil()
            filename = f"page-{index:04d}.png"
            image.save(dest_dir / filename)
            img_tags.append(
                f'<img class="page" src="{html.escape(filename)}" alt="page {index + 1}">'
            )
    finally:
        document.close()

    index_html = _PAGE_TEMPLATE.format(pages="\n".join(img_tags))
    index_path = dest_dir / "index.html"
    index_path.write_text(index_html, encoding="utf-8")

    return index_path.as_uri()


_PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  html, body {{ margin: 0; padding: 0; background: #525659; }}
  .doc {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 16px 0;
    box-sizing: border-box;
  }}
  .page {{
    display: block;
    width: 100%;
    height: auto;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.45);
  }}
</style>
</head>
<body>
  <div class="doc">
{pages}
  </div>
</body>
</html>
"""
