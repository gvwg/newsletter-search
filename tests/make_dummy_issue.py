"""Build tests/dummy-2026-12.pdf: a fake December 2026 issue for rehearsing
the publish-newsletter skill. GVWG never publishes in December, so the issue
cannot be mistaken for a real one, and every page says TEST.

It copies what publish_prep.py relies on in the current InDesign template:
running headers with the month on pages 2 onward, and a CONTENTS box on
page 2 with titles in one column and page numbers level with them.

Usage (from the repo root):
    .venv\\Scripts\\python tests\\make_dummy_issue.py
"""

from pathlib import Path

import pymupdf

OUT = Path(__file__).resolve().parent / "dummy-2026-12.pdf"
W, H = 612, 792
RED = (0.75, 0.1, 0.1)
GREY = (0.55, 0.55, 0.55)
HEADER = "T H E  C I R C U L A R   |   T E S T  I S S U E   |   D E C E M B E R  2 0 2 6"

# (title, byline, page) - clearly placeholders, but shaped like real entries
CONTENTS = [
    ("[TEST] Presidential Ramblings", None, 3),
    ("[TEST] Editor's Notes", None, 3),
    ("[TEST] This Month's Cover", None, 4),
    ("[TEST] Member Article ~ Placeholder Title", "by Test Author", 5),
    ("[TEST] Instant Gallery", None, 6),
    ("[TEST] Events Calendar", None, 7),
    ("[TEST] Officers and Volunteers", None, 8),
]


def watermark(page):
    """Diagonal, semi-transparent, drawn last so nothing covers it."""
    text, size = "TEST - NOT A REAL ISSUE", 44
    x = (W - pymupdf.get_text_length(text, fontname="hebo", fontsize=size)) / 2
    page.insert_text((x, H / 2 + size / 3), text, fontsize=size, fontname="hebo",
                     color=RED, fill_opacity=0.18,
                     morph=(pymupdf.Point(W / 2, H / 2), pymupdf.Matrix(50)))


def cover(page):
    page.insert_text((232, 30), "D E C E M B E R  2 0 2 6", fontsize=11, color=RED)
    page.insert_text((150, 110), "TEST ISSUE", fontsize=64, fontname="hebo")
    page.insert_text((128, 150), "MOCKUP - NOT A REAL NEWSLETTER", fontsize=22,
                     fontname="hebo", color=RED)
    box = pymupdf.Rect(56, 180, W - 56, 700)
    page.draw_rect(box, color=GREY, fill=(0.9, 0.9, 0.9), width=2)
    page.draw_line(box.tl, box.br, color=GREY, width=1.5)
    page.draw_line(box.tr, box.bl, color=GREY, width=1.5)
    page.insert_text((175, 430), "COVER PHOTO PLACEHOLDER", fontsize=20,
                     fontname="hebo", color=(0.35, 0.35, 0.35))
    page.insert_text((96, 470), "For rehearsing the publish-newsletter workflow only.",
                     fontsize=13, color=(0.35, 0.35, 0.35))
    page.insert_text((150, 740), "GVWG does not publish a December issue.",
                     fontsize=14, color=RED)


def contents(page):
    page.insert_text((306, 52), "CO N T E N TS", fontsize=20, fontname="hebo")
    page.insert_text((40, 100), "TEST ISSUE", fontsize=28, fontname="hebo", color=RED)
    page.insert_text((40, 125), "Placeholder contents for", fontsize=12)
    page.insert_text((40, 140), "rehearsing the publishing steps.", fontsize=12)
    rows, y = [], 95
    for entry in CONTENTS:
        rows.append((y, entry))
        y += 44 if entry[1] else 30
    # Like the InDesign file: all page numbers first (right-aligned just left
    # of the title column), then all titles. Drawn interleaved, MuPDF merges
    # each number into its title's text block.
    for y, (_, _, pno) in rows:
        num = str(pno)
        page.insert_text((320 - pymupdf.get_text_length(num, fontsize=12), y), num,
                         fontsize=12, color=RED)
    for y, (title, byline, _) in rows:
        page.insert_text((340, y), title + (f"\n{byline}" if byline else ""), fontsize=12)


def inner(page, pno):
    page.insert_text((60, 70), next((t for t, _, p in CONTENTS if p == pno), "[TEST] Page"),
                     fontsize=18, fontname="hebo")
    page.insert_text((60, 100), f"Placeholder text for page {pno} of the test issue.", fontsize=12)


def main():
    doc = pymupdf.open()
    for pno in range(1, 9):
        page = doc.new_page(width=W, height=H)
        if pno == 1:
            cover(page)
        else:
            page.insert_text((70, 20), HEADER, fontsize=8, color=GREY)
            contents(page) if pno == 2 else inner(page, pno)
        page.insert_text((40, H - 20), f"Page {pno}", fontsize=9, color=GREY)
        watermark(page)
    doc.set_metadata({"title": "TEST ISSUE - December 2026 (not a real newsletter)"})
    doc.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
