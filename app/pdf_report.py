"""Turns the business-case Markdown into a PDF, with no third-party library.

The CML package has no internet, so there is no PDF library to install. This writes the
file directly: A4 pages, the built-in Helvetica fonts (every PDF viewer has them), word
wrapping from the fonts' real character widths, headings, bullets, two-column tables,
a footer with page numbers.

It understands only the Markdown that reports.build_markdown produces:
    # title      ## heading      - bullet      | table | rows |      ---      **bold**
"""
from __future__ import annotations

import re
import zlib
from datetime import datetime, timezone

PAGE_W, PAGE_H = 595.0, 842.0           # A4 in points
MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 56.0, 60.0, 62.0
BODY = 10.0
LEADING = 14.0
NAVY = (0.12, 0.15, 0.38)
INK = (0.10, 0.11, 0.14)
GREY = (0.42, 0.44, 0.50)
HAIRLINE = (0.82, 0.84, 0.88)

# Helvetica and Helvetica-Bold advance widths per 1000 units, for printable ASCII (32-126).
_REG = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
        556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
        1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
        667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
        333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
        556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584]
_BOLD = [278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278,
         556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611,
         975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778,
         667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556,
         333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611,
         611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584]
# A few characters from Windows-1252 beyond ASCII (regular, bold).
_EXTRA = {"—": (1000, 1000), "–": (556, 556), "•": (350, 350), "·": (278, 278), "×": (584, 584),
          "…": (1000, 1000), "‘": (222, 278), "’": (222, 278), "“": (333, 500), "”": (333, 500),
          "°": (400, 400), "±": (584, 584), "§": (556, 556), "©": (737, 737), "®": (737, 737),
          "™": (1000, 1000), " ": (278, 278)}
# Characters Windows-1252 lacks, with a plain stand-in.
_FALLBACK = {"≥": ">=", "≤": "<=", "→": "->", "←": "<-", "−": "-", "≈": "~", "✓": "v", "✕": "x",
             "▲": "^", "▼": "v", " ": " ", " ": " ", " ": " ", " ": " "}


def _clean(text: str) -> str:
    out = []
    for ch in text:
        if ch in _FALLBACK:
            out.append(_FALLBACK[ch])
            continue
        try:
            ch.encode("cp1252")
        except UnicodeEncodeError:
            ch = "?"
        out.append(ch)
    return "".join(out)


def _char_w(ch: str, bold: bool) -> int:
    o = ord(ch)
    if 32 <= o <= 126:
        return (_BOLD if bold else _REG)[o - 32]
    pair = _EXTRA.get(ch)
    return pair[1 if bold else 0] if pair else 556


def text_width(text: str, size: float, bold: bool = False) -> float:
    return sum(_char_w(c, bold) for c in text) * size / 1000.0


def _esc(text: str) -> bytes:
    raw = _clean(text).encode("cp1252", errors="replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _inline(text: str) -> list[tuple[str, bool]]:
    """'a **b** c' -> [('a ', False), ('b', True), (' c', False)]"""
    parts = text.split("**")
    return [(t, i % 2 == 1) for i, t in enumerate(parts) if t]


def _words(segments: list[tuple[str, bool]]) -> list[tuple[str, bool]]:
    """Split into words, keeping each word's weight. A space stays attached before a word."""
    words: list[tuple[str, bool]] = []
    for text, bold in segments:
        for piece in re.findall(r"\s*\S+|\s+", text):
            words.append((piece, bold))
    return words


class _Pages:
    """Collects drawing operations per page and hands out vertical space."""

    def __init__(self) -> None:
        self.pages: list[list[bytes]] = [[]]
        self.y = PAGE_H - MARGIN_TOP

    def _emit(self, op: bytes) -> None:
        self.pages[-1].append(op)

    def need(self, height: float) -> None:
        if self.y - height < MARGIN_BOTTOM:
            self.pages.append([])
            self.y = PAGE_H - MARGIN_TOP

    def text(self, x: float, y: float, s: str, size: float, bold: bool, color) -> None:
        font = b"/F2" if bold else b"/F1"
        self._emit(b"BT " + b"%.3f %.3f %.3f rg " % color + font + b" %.2f Tf %.2f %.2f Td (" % (size, x, y)
                   + _esc(s) + b") Tj ET")

    def line(self, x1: float, y1: float, x2: float, y2: float, color, width: float = 0.5) -> None:
        self._emit(b"%.3f %.3f %.3f RG %.2f w %.2f %.2f m %.2f %.2f l S" % (*color, width, x1, y1, x2, y2))

    def draw_words(self, x0: float, words: list[tuple[str, bool]], y: float, size: float, color) -> None:
        x = x0
        for piece, bold in words:
            self.text(x, y, piece, size, bold, color)
            x += text_width(piece, size, bold)


def _wrap(words: list[tuple[str, bool]], width: float, size: float) -> list[list[tuple[str, bool]]]:
    """Greedy word wrap; a word longer than the line is broken by characters."""
    lines: list[list[tuple[str, bool]]] = []
    cur: list[tuple[str, bool]] = []
    cur_w = 0.0
    for piece, bold in words:
        w = text_width(piece, size, bold)
        if cur and cur_w + w > width and piece.strip():
            while cur and not cur[-1][0].strip():
                cur.pop()
            lines.append(cur)
            cur, cur_w = [], 0.0
            piece = piece.lstrip()
            w = text_width(piece, size, bold)
        if not cur and not piece.strip():
            continue
        while w > width and len(piece) > 1:  # a single very long word
            k = len(piece)
            while k > 1 and text_width(piece[:k], size, bold) > width:
                k -= 1
            if cur:
                lines.append(cur)
                cur, cur_w = [], 0.0
            lines.append([(piece[:k], bold)])
            piece = piece[k:]
            w = text_width(piece, size, bold)
        cur.append((piece, bold))
        cur_w += w
    if cur:
        while cur and not cur[-1][0].strip():
            cur.pop()
        if cur:
            lines.append(cur)
    return lines


def _paragraph(doc: _Pages, text: str, size: float = BODY, color=INK, indent: float = 0.0,
               first_prefix: str = "", leading: float = LEADING, space_after: float = 6.0,
               bold_all: bool = False) -> None:
    width = PAGE_W - 2 * MARGIN_X - indent
    segs = [(t, True) for t, _ in _inline(text)] if bold_all else _inline(text)
    for n, line in enumerate(_wrap(_words(segs), width, size)):
        doc.need(leading)
        doc.y -= leading
        if n == 0 and first_prefix:
            doc.text(MARGIN_X + indent - text_width(first_prefix, size) - 4, doc.y, first_prefix, size, False, color)
        doc.draw_words(MARGIN_X + indent, line, doc.y, size, color)
    doc.y -= space_after


def _table(doc: _Pages, rows: list[list[str]], aligns: list[str]) -> None:
    if not rows:
        return
    cols = len(rows[0])
    total = PAGE_W - 2 * MARGIN_X
    widths = [total * 0.58] + [total * 0.42 / max(1, cols - 1)] * (cols - 1) if cols > 1 else [total]
    row_h = 18.0
    for ri, row in enumerate(rows):
        doc.need(row_h)
        top = doc.y
        base = top - row_h + 5.5
        x = MARGIN_X
        for ci in range(cols):
            cell = _clean(row[ci]) if ci < len(row) else ""
            bold = ri == 0
            w = text_width(cell, BODY, bold)
            avail = widths[ci] - 8
            while w > avail and len(cell) > 1:  # keep a cell on its row rather than overflow it
                cell = cell[:-2] + "…" if len(cell) > 2 else cell[:-1]
                w = text_width(cell, BODY, bold)
            tx = x + widths[ci] - 4 - w if aligns[ci] == "right" else x + 4
            doc.text(tx, base, cell, BODY, bold, NAVY if bold else INK)
            x += widths[ci]
        doc.line(MARGIN_X, top - row_h, MARGIN_X + total, top - row_h,
                 NAVY if ri == 0 else HAIRLINE, 0.9 if ri == 0 else 0.5)
        doc.y -= row_h
    doc.y -= 8


def _layout(markdown: str) -> _Pages:
    doc = _Pages()
    lines = markdown.replace("\r\n", "\n").split("\n")
    i, after_title = 0, False
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        if line.startswith("# "):
            _paragraph(doc, line[2:].strip(), size=20, color=NAVY, leading=25, space_after=4, bold_all=True)
            after_title = True
        elif line.startswith("## "):
            doc.y -= 10
            doc.need(40)
            _paragraph(doc, line[3:].strip(), size=13, color=NAVY, leading=17, space_after=5, bold_all=True)
            after_title = False
        elif line.startswith("|"):
            rows, aligns = [], []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    aligns = ["right" if c.endswith(":") else "left" for c in cells]
                else:
                    rows.append([c.replace("**", "") for c in cells])
                i += 1
            _table(doc, rows, aligns or ["left"] * (len(rows[0]) if rows else 1))
            after_title = False
            continue
        elif line.startswith("- "):
            _paragraph(doc, line[2:].strip(), indent=14, first_prefix="•", space_after=3)
            after_title = False
        elif re.fullmatch(r"-{3,}", line.strip()):
            doc.y -= 6
            doc.need(10)
            doc.line(MARGIN_X, doc.y, PAGE_W - MARGIN_X, doc.y, HAIRLINE, 0.7)
            doc.y -= 12
            after_title = False
        elif after_title:
            _paragraph(doc, line.strip(), size=9.5, color=GREY, space_after=10)
            after_title = False
        else:
            _paragraph(doc, line.strip(), space_after=8)
        i += 1
    return doc


def _pdf_string(text: str) -> bytes:
    return b"<FEFF" + text.encode("utf-16-be").hex().upper().encode("ascii") + b">"


def markdown_to_pdf(markdown: str, title: str = "Report", footer: str = "") -> bytes:
    """Returns the bytes of a PDF containing the Markdown, typeset as described above."""
    doc = _layout(markdown)
    total = len(doc.pages)
    contents = []
    for n, ops in enumerate(doc.pages, start=1):
        foot = _Pages()
        foot.pages = [[]]
        label = f"Page {n} of {total}"
        foot.line(MARGIN_X, 44, PAGE_W - MARGIN_X, 44, HAIRLINE, 0.5)
        foot.text(MARGIN_X, 32, footer or title, 8, False, GREY)
        foot.text(PAGE_W - MARGIN_X - text_width(label, 8), 32, label, 8, False, GREY)
        contents.append(zlib.compress(b"\n".join(ops + foot.pages[0])))

    objs: list[bytes] = []

    def add(body: bytes) -> int:
        objs.append(body)
        return len(objs)

    catalog = add(b"")   # 1, filled below
    pages_obj = add(b"")  # 2
    f1 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    f2 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    now = datetime.now(timezone.utc).strftime("D:%Y%m%d%H%M%SZ").encode("ascii")
    info = add(b"<< /Title " + _pdf_string(title) + b" /Creator " + _pdf_string("Data Product Value")
               + b" /Producer " + _pdf_string("Data Product Value") + b" /CreationDate (" + now + b") >>")
    page_ids = []
    for data in contents:
        content = add(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(data) + data + b"\nendstream")
        page_ids.append(add(
            b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.0f %.0f] /Contents %d 0 R "
            b"/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> >>" % (pages_obj, PAGE_W, PAGE_H, content, f1, f2)))
    objs[pages_obj - 1] = (b"<< /Type /Pages /Count %d /Kids [" % len(page_ids)
                           + b" ".join(b"%d 0 R" % p for p in page_ids) + b"] >>")
    objs[catalog - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % pages_obj

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for n, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % n + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += (b"trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, catalog, info, xref))
    return bytes(out)
