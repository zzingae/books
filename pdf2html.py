import base64
import time
from pathlib import Path

import fitz
from openai import OpenAI
from tqdm import tqdm

client = OpenAI(api_key='')

PDF_DIR = Path("split_pages")      # page_001.pdf, page_002.pdf ...
OUT_DIR = Path("html_output")
IMG_DIR = OUT_DIR / "images"
PAGE_HTML_DIR = OUT_DIR / "pages"

MODEL = "gpt-4.1"
DPI = 200

OUT_DIR.mkdir(exist_ok=True)
IMG_DIR.mkdir(parents=True, exist_ok=True)
PAGE_HTML_DIR.mkdir(parents=True, exist_ok=True)


PROMPT = """
This image contains one scanned page from a mathematics textbook.

Convert it into a clean HTML fragment.

Rules:
- Output HTML fragment only.
- Do not include <html>, <head>, or <body>.
- Do not summarize or omit content.
- Preserve reading order, paragraphs, headings, captions, equation numbers, and footnotes.
- Use LaTeX for all mathematics.
- Inline math must use \\( ... \\).
- Every displayed equation must be written as a separate block like this:

<div class="math-line">
\\[
...
\\]
</div>

- Do not merge several equation lines into one long equation.
- Preserve displayed equations line by line as they appear in the image.
- Do not use aligned, split, gather, multline, or eqnarray unless the source explicitly uses them.
- Preserve subscripts, superscripts, primes, Greek letters, brackets, and equation numbers accurately.
- Convert tables to HTML tables when possible.
- For figures, use <figure><figcaption>caption or short description</figcaption></figure>.
- If something is unreadable, write [UNCLEAR].
"""


def render_pdf_to_png(pdf_path: Path, dpi: int = DPI) -> Path:
    doc = fitz.open(pdf_path)
    page = doc[0]

    zoom = dpi / 72
    pix = page.get_pixmap(
        matrix=fitz.Matrix(zoom, zoom),
        alpha=False,
        colorspace=fitz.csGRAY,
    )

    img_path = IMG_DIR / f"{pdf_path.stem}.png"
    pix.save(img_path)
    doc.close()

    return img_path


def image_to_base64(img_path: Path) -> str:
    return base64.b64encode(img_path.read_bytes()).decode("utf-8")


def ocr_image_to_html(img_path: Path) -> str:
    b64 = image_to_base64(img_path)

    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": PROMPT},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{b64}",
                    },
                ],
            }
        ],
    )

    return response.output_text.strip()


def process_pdf_page(pdf_path: Path) -> str:
    page_name = pdf_path.stem
    out_html_path = PAGE_HTML_DIR / f"{page_name}.html"

    if out_html_path.exists():
        return out_html_path.read_text(encoding="utf-8")

    img_path = render_pdf_to_png(pdf_path)
    html = ocr_image_to_html(img_path)

    wrapped = f"""
<section class="pdf-page" data-page="{page_name}">
{html}
</section>
"""

    out_html_path.write_text(wrapped, encoding="utf-8")
    time.sleep(0.2)

    return wrapped


def merge_html(page_htmls):
    merged = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<script>
window.MathJax = {
  tex: {
    inlineMath: [['\\\\(', '\\\\)']],
    displayMath: [['\\\\[', '\\\\]']],
    processEscapes: true
  }
};
</script>

<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>

<style>
body {
  max-width: 820px;
  margin: 32px auto;
  padding: 0 18px;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 18px;
  line-height: 1.65;
}

.pdf-page {
  border-bottom: 1px solid #ddd;
  margin-bottom: 48px;
  padding-bottom: 48px;
}

.math-line {
  width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  text-align: left;
  margin: 0.8em 0;
  padding: 0.2em 0;
  -webkit-overflow-scrolling: touch;
}

.math-line mjx-container {
  text-align: left !important;
  margin: 0 !important;
  min-width: max-content;
}

table {
  border-collapse: collapse;
  width: 100%;
  overflow-x: auto;
}

th, td {
  border: 1px solid #ccc;
  padding: 6px 10px;
}

figure {
  border: 1px solid #ddd;
  padding: 12px;
  margin: 24px 0;
  background: #fafafa;
}

figcaption {
  font-size: 0.9em;
}

pre {
  overflow-x: auto;
}
</style>
</head>
<body>
"""

    merged += "\n".join(page_htmls)

    merged += """
</body>
</html>
"""

    out_path = OUT_DIR / "index.html"
    out_path.write_text(merged, encoding="utf-8")
    return out_path


def main():
    pdf_paths = sorted(PDF_DIR.rglob("*.pdf"))

    pdf_paths = pdf_paths[:100]

    if not pdf_paths:
        raise FileNotFoundError(f"No PDF files found under: {PDF_DIR.resolve()}")

    page_htmls = []

    for pdf_path in tqdm(pdf_paths, desc="OCR pages"):
        page_htmls.append(process_pdf_page(pdf_path))

    out_path = merge_html(page_htmls)
    print(f"Done: {out_path}")


if __name__ == "__main__":
    main()