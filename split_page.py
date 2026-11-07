import pymupdf
from pathlib import Path

src = Path("Gardiner.pdf")
outdir = Path("split_pages")
outdir.mkdir(parents=True, exist_ok=True)

with pymupdf.open(src) as pdf:
    for i in range(len(pdf)):
        with pymupdf.open() as page_pdf:
            page_pdf.insert_pdf(pdf, from_page=i, to_page=i)
            page_pdf.save(outdir / f"page_{(i+1):03d}.pdf")