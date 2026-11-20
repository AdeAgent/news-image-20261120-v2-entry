# The World Today - Friday 20 November 2026. V2 broadsheet rebuild.
#
# A newspaper front page drawn entirely in code: a serif masthead, thirteen
# illustrated lead cards in three rows, a strip of six big numbers, a
# numbered list of the remaining thirty-seven stories, a world map with
# numbered pins, and a date-check footer. The news itself is the same fifty
# verified stories as the first entry for this competition, only the layout,
# the typography and the pictures are new: the first entry's pixel headline
# and four leads are replaced by a broadsheet masthead and thirteen leads,
# the shape the highest-ranked entries on the board use.
#
# Everything is drawn from two small bitmap fonts defined in this file and
# the PNG bytes are encoded by hand, so the program uses only the Python
# standard library, needs no network and no files besides this one. Two runs
# write byte for byte the same file.
#
# Local check:
#   mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
#   python3 -c "import hashlib;print(hashlib.sha256(open('out/entry.png','rb').read()).hexdigest())"

import math
import os
import struct
import zlib
from pathlib import Path

WIDTH = 1024
HEIGHT = 1024

PAPER = (247, 242, 231)
INK = (26, 26, 26)
RED = (164, 30, 34)
DARKRED = (122, 20, 24)
BLUE = (31, 78, 121)
NAVY = (16, 38, 66)
SKY = (207, 224, 232)
SAND = (232, 220, 192)
TAN = (214, 196, 160)
GREY = (120, 116, 108)
LIGHTGREY = (226, 220, 208)
GOLD = (212, 175, 55)
WHITE = (255, 255, 255)
GREEN = (46, 110, 62)
BROWN = (122, 84, 52)
TEAL = (18, 110, 105)


def _chunk(kind, payload):
    out = struct.pack(">I", len(payload)) + kind + payload
    out += struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    return out


def encode_png(width, height, rgb):
    """Encode a raw RGB buffer as a complete PNG file (filter 0 rows)."""
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    blob = b"\x89PNG\r\n\x1a\n"
    blob += _chunk(b"IHDR", ihdr)
    blob += _chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    blob += _chunk(b"IEND", b"")
    return blob


class Canvas:
    """A plain RGB pixel buffer with small drawing helpers."""

    def __init__(self, width, height, bg):
        self.w = width
        self.h = height
        self.buf = bytearray(width * height * 3)
        for i in range(width * height):
            self.buf[i * 3] = bg[0]
            self.buf[i * 3 + 1] = bg[1]
            self.buf[i * 3 + 2] = bg[2]

    def px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i] = color[0]
            self.buf[i + 1] = color[1]
            self.buf[i + 2] = color[2]

    def fill(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.buf[i] = color[0]
                self.buf[i + 1] = color[1]
                self.buf[i + 2] = color[2]

    def hline(self, x, y, w, color, thick=1):
        self.fill(x, y, w, thick, color)

    def vline(self, x, y, h, color, thick=1):
        self.fill(x, y, thick, h, color)

    def frame(self, x, y, w, h, color, thick=1):
        self.hline(x, y, w, color, thick)
        self.hline(x, y + h - thick, w, color, thick)
        self.vline(x, y, h, color, thick)
        self.vline(x + w - thick, y, h, color, thick)

    def line(self, x0, y0, x1, y1, color):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.px(x, y, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def disc(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy) <= r * r:
                    self.px(xx, yy, color)

    def ring(self, cx, cy, r, color, thick=2):
        for yy in range(cy - r - 1, cy + r + 2):
            for xx in range(cx - r - 1, cx + r + 2):
                d = ((xx - cx) * (xx - cx) + (yy - cy) * (yy - cy)) ** 0.5
                if r - thick < d <= r:
                    self.px(xx, yy, color)

    def poly(self, points, color):
        """Fill a polygon with a scanline pass."""
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        for y in range(min(ys), max(ys) + 1):
            nodes = []
            n = len(points)
            for i in range(n):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    nodes.append(int(x0 + (y - y0) * (x1 - x0) / (y1 - y0)))
            nodes.sort()
            for k in range(0, len(nodes) - 1, 2):
                self.hline(nodes[k], y, nodes[k + 1] - nodes[k], color)

# A condensed 5x7 bitmap font for body text: one narrow column per glyph,
# single-pixel strokes, drawn entirely in capitals like a newspaper.
PIXEL = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "*": ("00000", "10101", "01110", "11111", "01110", "10101", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
}


def px_width(text, scale=1):
    return len(text) * 6 * scale


def px_text(cv, x, y, text, color, scale=1):
    cx = x
    for ch in text.upper():
        glyph = PIXEL.get(ch, PIXEL[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    cv.fill(cx + col * scale, y + row * scale, scale, scale, color)
        cx += 6 * scale
    return cx


def px_centered(cv, x, y, width, text, color, scale=1):
    w = px_width(text, scale)
    px_text(cv, x + max(0, (width - w) // 2), y, text, color, scale)


def px_wrap(text, max_width, scale=1):
    words = text.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if px_width(trial, scale) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def px_para(cv, x, y, width, text, color, scale=1, leading=None):
    if leading is None:
        leading = 9 * scale + 2
    for line in px_wrap(text, width, scale):
        px_text(cv, x, y, line, color, scale)
        y += leading
    return y


# A 7x9 serif display font for the masthead, the lead headlines and the big
# numbers. Stems carry a flat foot on the baseline and a flat cap on the
# top row, which is what makes it read as a newspaper serif at small sizes.
SERIF = {
    "A": ("0011000", "0111100", "1100110", "1100110", "1111110", "1100110", "1100110", "1100110", "1110111"),
    "B": ("1111100", "1100110", "1100110", "1100110", "1111100", "1100110", "1100110", "1100110", "1111100"),
    "C": ("0111110", "1100010", "1100000", "1100000", "1100000", "1100000", "1100000", "1100010", "0111100"),
    "D": ("1111000", "1100110", "1100110", "1100110", "1100110", "1100110", "1100110", "1100110", "1111000"),
    "E": ("1111110", "1100000", "1100000", "1100000", "1111100", "1100000", "1100000", "1100000", "1111110"),
    "F": ("1111110", "1100000", "1100000", "1100000", "1111100", "1100000", "1100000", "1100000", "1100000"),
    "G": ("0111110", "1100010", "1100000", "1100000", "1100110", "1100110", "1100110", "1100010", "0111110"),
    "H": ("1100110", "1100110", "1100110", "1100110", "1111110", "1100110", "1100110", "1100110", "1110111"),
    "I": ("0111110", "0011000", "0011000", "0011000", "0011000", "0011000", "0011000", "0011000", "0111110"),
    "J": ("0011110", "0001100", "0001100", "0001100", "0001100", "0001100", "1101100", "1101100", "0111000"),
    "K": ("1100110", "1100110", "1101010", "1111000", "1111000", "1101010", "1100110", "1100110", "1110111"),
    "L": ("1100000", "1100000", "1100000", "1100000", "1100000", "1100000", "1100000", "1100000", "1111110"),
    "M": ("1100110", "1111110", "1111110", "1101010", "1101010", "1100110", "1100110", "1100110", "1110111"),
    "N": ("1100110", "1100110", "1110110", "1111010", "1101110", "1100110", "1100110", "1100110", "1110111"),
    "O": ("0111100", "1100110", "1100110", "1100110", "1100110", "1100110", "1100110", "1100110", "0111100"),
    "P": ("1111100", "1100110", "1100110", "1100110", "1111100", "1100000", "1100000", "1100000", "1100000"),
    "Q": ("0111100", "1100110", "1100110", "1100110", "1100110", "1100110", "1101010", "1100100", "0111010"),
    "R": ("1111100", "1100110", "1100110", "1100110", "1111100", "1101010", "1100110", "1100110", "1110111"),
    "S": ("0111110", "1100010", "1100000", "1100000", "0111100", "0000110", "0000110", "1100010", "0111100"),
    "T": ("1111110", "0011000", "0011000", "0011000", "0011000", "0011000", "0011000", "0011000", "0011000"),
    "U": ("1100110", "1100110", "1100110", "1100110", "1100110", "1100110", "1100110", "1100110", "0111100"),
    "V": ("1100110", "1100110", "1100110", "1100110", "1100110", "1100110", "0111100", "0011000", "0000000"),
    "W": ("1100110", "1100110", "1100110", "1100110", "1101010", "1101010", "1111110", "1111110", "1101010"),
    "X": ("1100110", "1100110", "0111100", "0011000", "0011000", "0111100", "1100110", "1100110", "1110111"),
    "Y": ("1100110", "1100110", "0111100", "0011000", "0011000", "0011000", "0011000", "0011000", "0011000"),
    "Z": ("1111110", "0000110", "0001100", "0011000", "0110000", "1100000", "1100000", "1100000", "1111110"),
    "0": ("0111100", "1100110", "1101110", "1110110", "1101110", "1100110", "1100110", "1100110", "0111100"),
    "1": ("0011000", "0111000", "0011000", "0011000", "0011000", "0011000", "0011000", "0011000", "0111110"),
    "2": ("0111100", "1100110", "0000110", "0001100", "0011000", "0110000", "1100000", "1100000", "1111110"),
    "3": ("1111100", "0000110", "0000110", "0000110", "0111100", "0000110", "0000110", "0000110", "1111100"),
    "4": ("0001100", "0011100", "0110100", "1100100", "1111110", "0001100", "0001100", "0001100", "0001100"),
    "5": ("1111110", "1100000", "1100000", "1111100", "0000110", "0000110", "0000110", "1100110", "0111100"),
    "6": ("0111100", "1100000", "1100000", "1111100", "1100110", "1100110", "1100110", "1100110", "0111100"),
    "7": ("1111110", "0000110", "0001100", "0011000", "0011000", "0100000", "0100000", "0100000", "0100000"),
    "8": ("0111100", "1100110", "1100110", "1100110", "0111100", "1100110", "1100110", "1100110", "0111100"),
    "9": ("0111100", "1100110", "1100110", "1100110", "0111110", "0000110", "0000110", "0001100", "0111000"),
    " ": ("0000000", "0000000", "0000000", "0000000", "0000000", "0000000", "0000000", "0000000", "0000000"),
    ".": ("0000000", "0000000", "0000000", "0000000", "0000000", "0000000", "0000000", "0011000", "0011000"),
    ",": ("0000000", "0000000", "0000000", "0000000", "0000000", "0011000", "0011000", "0001000", "0010000"),
    ":": ("0000000", "0011000", "0011000", "0000000", "0000000", "0011000", "0011000", "0000000", "0000000"),
    ";": ("0000000", "0011000", "0011000", "0000000", "0000000", "0011000", "0011000", "0001000", "0010000"),
    "!": ("0011000", "0011000", "0011000", "0011000", "0011000", "0000000", "0000000", "0011000", "0011000"),
    "?": ("0111100", "1100110", "0000110", "0001100", "0011000", "0000000", "0000000", "0011000", "0011000"),
    "'": ("0011000", "0011000", "0001000", "0000000", "0000000", "0000000", "0000000", "0000000", "0000000"),
    "-": ("0000000", "0000000", "0000000", "0000000", "0111110", "0000000", "0000000", "0000000", "0000000"),
    "/": ("0000010", "0000100", "0000100", "0001000", "0010000", "0010000", "0100000", "0100000", "1000000"),
    "(": ("0001100", "0011000", "0110000", "0100000", "0100000", "0100000", "0110000", "0011000", "0001100"),
    ")": ("0110000", "0011000", "0001100", "0000100", "0000100", "0000100", "0001100", "0011000", "0110000"),
    "&": ("0111000", "1000100", "1010100", "0100000", "1010100", "1001000", "1001000", "1000100", "0111010"),
    "%": ("1100110", "1101110", "0001100", "0011000", "0110000", "1101010", "1100110", "0000000", "0000000"),
    "$": ("0011000", "0111110", "1101000", "0111100", "0001100", "0010110", "1111100", "0011000", "0011000"),
    "+": ("0000000", "0000000", "0011000", "0011000", "1111110", "0011000", "0011000", "0000000", "0000000"),
    "=": ("0000000", "0000000", "0000000", "1111110", "0000000", "1111110", "0000000", "0000000", "0000000"),
    "*": ("0000000", "1010100", "0111000", "1111100", "0111000", "1010100", "0000000", "0000000", "0000000"),
    '"': ("1010100", "1010100", "0000000", "0000000", "0000000", "0000000", "0000000", "0000000", "0000000"),
}


def serif_width(text, scale=1):
    return len(text) * 8 * scale


def serif_text(cv, x, y, text, color, scale=1):
    cx = x
    for ch in text.upper():
        glyph = SERIF.get(ch, SERIF[" "])
        for row in range(9):
            bits = glyph[row]
            for col in range(7):
                if bits[col] == "1":
                    cv.fill(cx + col * scale, y + row * scale, scale, scale, color)
        cx += 8 * scale
    return cx


def serif_centered(cv, x, y, width, text, color, scale=1):
    w = serif_width(text, scale)
    serif_text(cv, x + max(0, (width - w) // 2), y, text, color, scale)


def serif_wrap(text, max_width, scale=1):
    words = text.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if serif_width(trial, scale) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def serif_para(cv, x, y, width, text, color, scale=1, leading=None):
    if leading is None:
        leading = 9 * scale + 2
    for line in serif_wrap(text, width, scale):
        serif_text(cv, x, y, line, color, scale)
        y += leading
    return y

# ---------------------------------------------------------------------------
# The day's news. Every item below happened, or was first reported, on
# Friday 20 November 2026. Figures come from the wires of the day: the
# cyclone's landfall and evacuation count from the India Meteorological
# Department and Odisha officials; the Senate vote and the Iran cost from
# Reuters and the Senate hearing; the Riyadh strike from Reuters and the
# Saudi Press Agency; the Berlin summit from the BBC; the APEC outcome from
# Xinhua and the APEC leaders' declaration. Items marked CLAIM are one
# side's account, not independently confirmed. Headlines are shortened to
# fit their cards; nothing is added and no figure is changed.
# ---------------------------------------------------------------------------

# Thirteen leads: (number, kicker, picture, headline, deck or "").
# Decks only restate their headline; the hero lead keeps its full deck.
LEADS = [
    ("1", "ASIA - WEATHER", "cyclone",
     "CYCLONE AKVAN BEARS DOWN ON ODISHA",
     "300,000 evacuated as the storm crosses near Gopalpur; winds 90-100, gusting 110."),
    ("2", "WASHINGTON - IRAN", "iran",
     "TRUMP WAITS UNTIL 2027 ON IRAN", ""),
    ("3", "EUROPE - DIPLOMACY", "europe",
     "EUROPE OPEN TO RUSSIA TALKS", ""),
    ("4", "MIDDLE EAST - CONFLICT", "kafd",
     "MISSILE HITS RIYADH KAFD", ""),
    ("5", "ASIA - TRADE", "apec",
     "APEC ADOPTS SHENZHEN OUTLOOK", ""),
    ("6", "CLIMATE - COP31", "cop",
     "COP31 CLOSES; GAP $305BN", ""),
    ("7", "SPORT - BASEBALL", "baseball",
     "TRUMP PARDONS PETE ROSE", ""),
    ("8", "ASIA - SECURITY", "nuclear",
     "N. KOREA EXPANDS URANIUM", ""),
    ("9", "AMERICAS - DIPLOMACY", "flags",
     "US, VENEZUELA TIES BACK", ""),
    ("10", "ASIA - LAW", "court",
     "S. KOREA CLEARS EX-PM HAN", ""),
    ("11", "OCEANIA - DISASTER", "drought",
     "FIJI DROUGHT DISASTER", ""),
    ("12", "SPORT - CRICKET", "cricket",
     "NICHOLLS 113* AS NZ REACH 243-5", ""),
    ("13", "MARKETS - ASIA", "chart",
     "SENSEX +989; GOLD AT $3,756", ""),
]

# Stories 14 to 50, numbered, in three columns of 13, 12 and 12.
ALSO = (
    "GOOGLE SHIPS GEMINI 4 NEON, 1M-TOKEN WINDOW|ANTHROPIC OFFER CLOSES; VALUED AT $1.5 TRILLION|NASA VOYAGER 1 NOW ONE LIGHT-DAY FROM EARTH|"
    "MIGRANT BOAT CAPSIZES OFF SENEGAL|HAITI APPROVES SALVADORAN TROOP DEAL|"
    "ADNOC VESSEL ATTACKED IN STRAIT OF HORMUZ|EU-UK SUMMIT OPENS IN BRUSSELS|"
    "WORLD CHILDREN'S DAY MARKED AROUND THE GLOBE|SYRIA HAILS UN VOTE ON POST-WAR PROGRESS|"
    "SOMALIA EXPELS UAE ENVOY|COLOMBIA MARCHES AGAIN AGAINST THE PRESIDENT|"
    "CHINA HOLDS RATES FOR AN 18TH MONTH|MODI MEETS WILLIAM AND KATE IN NEW DELHI|"
    "QUAD HOLDS FIRST SUMMIT IN TWO YEARS|NATO ASSEMBLY OPENS ITS 72ND SESSION|"
    "FIRE AT YUNUS HOME IN DHAKA; ARSON SUSPECTED|ASEAN SUMMIT CLOSES WITH NEW PACTS|"
    "WITKOFF AND KUSHNER BRIEF ZELENSKYY|COALITION OF THE WILLING MEETS IN BERLIN|"
    "AUSTRALIA SANCTIONS SETTLERS|PAKISTAN MINISTER TO DELHI FOR SCO|"
    "PHILIPPINES-CHILE TRADE DEAL SIGNED|MUSK PLANS PHILIPPINES PROJECTS|"
    "COP31: INDIA PUSHES RESILIENCE|ASIAN HOCKEY TROPHY BEGINS|HARIMAU SHAKTI EXERCISE IN IPOH|"
    "INDIA ELECTRONICS EXPORTS JUMP 44 PERCENT|CRUDE OIL FUTURES FALL OVER 3 PERCENT|"
    "INDIA'S FIRST BIRD-FLU VACCINE|YOUTH ANTI-WAR PROTESTS IN EUROPE|"
    "EU DELAYS METHANE RULES 24 MONTHS|BAYERN MUNICH BEAT KOLN 3-0|ARGENTINA 0-2 AUSTRALIA, U17 CUP|"
    "MERZ HOSTS QATAR'S EMIR IN BERLIN|AZERBAIJAN'S ALIYEV VISITS VIETNAM|US JOBLESS CLAIMS 203,000|"
    "NIFTY GAINS 286 TO 25,514"
).split("|")

NUMBERS = [
    ("300,000", "EVACUATED FROM AKVAN"),
    ("51-48", "SENATE VOTE ON IRAN"),
    ("$48BN", "COST OF THE IRAN WAR"),
    ("113*", "NICHOLLS, UNBEATEN IN NZ"),
    ("$3,756", "GOLD PER OUNCE, DOWN 2.8%"),
    ("+989", "SENSEX JUMPS IN MUMBAI"),
]

MINI_NUMBERS = [
    ("300,000", "EVACUATED"),
    ("51-48", "SENATE VOTE"),
    ("$3,756", "GOLD / OZ"),
]

# World map pins: (story number, longitude, latitude). A few plotted
# positions are nudged a few degrees from the true spot so neighbouring
# pins do not cover each other's numbers; the map is schematic.
PINS = [
    ("1", 88, 20), ("2", -74, 36), ("3", 13, 52), ("4", 47, 25),
    ("5", 114, 22), ("6", 30, 37), ("7", -92, 42), ("8", 122, 44),
    ("9", -72, 7), ("10", 131, 33), ("11", 174, -18), ("12", 170, -43),
    ("13", 72, 19), ("17", -17, 15), ("18", -60, 16), ("19", 60, 23),
]

# Rough continent outlines in (longitude, latitude), equirectangular.
CONTINENTS = [
    [(-168, 66), (-140, 70), (-120, 72), (-95, 80), (-80, 73), (-60, 60), (-55, 47), (-70, 42), (-75, 35), (-80, 26), (-90, 21), (-97, 16), (-105, 20), (-115, 28), (-125, 40), (-125, 49), (-150, 60)],
    [(-80, 10), (-60, 8), (-50, 0), (-35, -8), (-40, -20), (-48, -28), (-58, -35), (-65, -41), (-70, -52), (-73, -37), (-70, -20), (-80, -5)],
    [(-18, 35), (-10, 31), (0, 36), (10, 37), (20, 32), (32, 31), (35, 28), (43, 12), (51, 11), (48, 0), (40, -10), (35, -20), (32, -29), (26, -34), (18, -35), (12, -18), (8, 4), (-8, 5), (-18, 15)],
    [(-10, 36), (-9, 43), (-2, 48), (0, 51), (5, 53), (8, 57), (10, 59), (18, 56), (21, 55), (24, 58), (28, 60), (30, 62), (32, 70), (40, 68), (44, 66), (40, 60), (35, 55), (30, 50), (28, 45), (23, 40), (19, 42), (12, 44), (8, 44), (3, 42), (-1, 37)],
    [(32, 70), (40, 68), (50, 69), (60, 70), (70, 72), (80, 73), (90, 75), (100, 77), (110, 74), (120, 73), (130, 72), (140, 72), (150, 70), (160, 66), (162, 60), (158, 52), (142, 50), (140, 40), (135, 35), (130, 33), (127, 35), (122, 38), (120, 32), (115, 23), (110, 20), (105, 10), (100, 8), (98, 12), (95, 16), (92, 21), (88, 22), (85, 20), (80, 15), (76, 10), (72, 20), (66, 25), (60, 25), (57, 27), (52, 28), (48, 30), (44, 29), (40, 32), (36, 36)],
    [(113, -22), (114, -30), (115, -35), (120, -34), (125, -32), (130, -32), (135, -35), (140, -38), (145, -38), (150, -37), (153, -32), (153, -27), (150, -22), (146, -19), (142, -15), (142, -11), (136, -12), (132, -12), (130, -13), (126, -14), (122, -17), (118, -20)],
]

DATE_CHECK = (
    "LEFT OUT - THEY BROKE BEFORE FRIDAY: ICJ GENOCIDE RULING ON MYANMAR "
    "(19 NOV). TRILATERAL TRUMP-XI-PUTIN MEETING (19 NOV). ANTHROPIC "
    "$81.34BN IPO PRICED (19 NOV). CRIMEA BRIDGE SPAN FALLS (17-18 NOV). "
    "DENMARK-GREENLAND PACT (19 NOV). GERMANY ELECTRICITY-TAX CUT (18 NOV)."
)

REGIONS_LINE = "ASIA 21 - EUROPE 9 - AMERICAS 8 - WORLD 4 - OCEANIA 3 - MIDDLE EAST 3 - AFRICA 2"
HOW_TO_READ = "1-13 ARE THE LEADS, EACH WITH ITS OWN PICTURE. 14-50 ARE THE REST OF FRIDAY, NUMBERED. PINS ON THE MAP MATCH THE NUMBERS."

# ---------------------------------------------------------------------------
# Illustrations. Each lead carries a small drawn picture, kept abstract on
# purpose: a cyclone is rings and rain, a capitol is a dome and columns, a
# skyline is towers and smoke, a chart is candlesticks. No picture pretends
# to be a photograph, and no picture carries words that could come out
# garbled, except the year on the capitol and the numbers on the chart.
# ---------------------------------------------------------------------------

def draw_cyclone(cv, x, y, w, h):
    cv.fill(x, y, w, h, SKY)
    cx, cy = x + w // 2, y + h // 2 - 4
    cv.ring(cx, cy, 8, NAVY, 2)
    cv.ring(cx, cy, 16, BLUE, 2)
    cv.ring(cx, cy, 24, BLUE, 2)
    cv.disc(cx, cy, 4, RED)
    for k in range(8):
        rx = x + 8 + k * 12
        cv.line(rx, y + 6, rx - 5, y + 20, BLUE)
    base = y + h - 12
    for k in range(6):
        tx = x + 10 + k * (w - 20) // 5
        cv.poly([(tx - 8, base), (tx + 8, base), (tx, base - 10)], SAND)
    cv.fill(x, base, w, h - (base - y), TAN)


def draw_iran(cv, x, y, w, h):
    cv.fill(x, y, w, h, NAVY)
    serif_text(cv, x + 10, y + 6, "2027", GOLD, 3)
    dx = x + w - 52
    dy = y + h - 6
    cv.disc(dx, dy - 18, 20, WHITE)
    cv.fill(dx - 20, dy - 18, 40, 18, WHITE)
    for k in range(4):
        cx = dx - 15 + k * 10
        cv.fill(cx, dy - 16, 3, 16, NAVY)
    cv.fill(dx - 24, dy - 2, 48, 3, WHITE)
    cv.fill(x, y + h - 3, w, 3, GOLD)
    cv.fill(x + 8, y + h - 26, 34, 3, GOLD)


def draw_europe(cv, x, y, w, h):
    cv.fill(x, y, w, h, PAPER)
    fx, fy = x + 8, y + 8
    fw, fh = (w - 24) // 2, h - 16
    cv.fill(fx, fy, fw, fh, BLUE)
    for k in range(12):
        ang = 2 * math.pi * k / 12 - math.pi / 2
        px = fx + fw // 2 + int(14 * math.cos(ang))
        py = fy + fh // 2 + int(14 * math.sin(ang))
        cv.disc(px, py, 2, GOLD)
    rx = fx + fw + 8
    rw = w - 24 - fw
    cv.fill(rx, fy, rw, fh // 3, WHITE)
    cv.fill(rx, fy + fh // 3, rw, fh // 3, BLUE)
    cv.fill(rx, fy + 2 * fh // 3, rw, fh - 2 * fh // 3, RED)
    cv.frame(fx, fy, fw, fh, INK, 1)
    cv.frame(rx, fy, rw, fh, INK, 1)


def draw_kafd(cv, x, y, w, h):
    cv.fill(x, y, w, h, (233, 226, 205))
    cv.disc(x + w - 40, y + 14, 10, GOLD)
    heights = [44, 66, 38, 56, 30]
    bw = 22
    gap = 7
    total = len(heights) * bw + (len(heights) - 1) * gap
    sx = x + (w - total) // 2
    base = y + h - 8
    for i, hh in enumerate(heights):
        tx = sx + i * (bw + gap)
        cv.fill(tx, base - hh, bw, hh, NAVY if i == 1 else BLUE)
        for wy in range(base - hh + 6, base - 4, 10):
            cv.fill(tx + 4, wy, bw - 8, 3, SKY)
    cv.fill(sx + bw + gap + 3, base - 66 - 10, 16, 5, RED)
    cv.disc(sx + bw + gap + 11, base - 66 - 22, 6, GREY)
    cv.disc(sx + bw + gap + 19, base - 66 - 29, 4, GREY)
    cv.fill(x, base, w, 8, TAN)


def draw_apec(cv, x, y, w, h):
    cv.fill(x, y, w, h, SKY)
    cv.fill(x, y + h - 18, w, 18, BLUE)
    for k in range(5):
        cv.line(x + 12 + k * 16, y + h - 18, x + 12 + k * 16, y + h - 4, WHITE)
    heights = [34, 48, 28, 42]
    bw = 26
    gap = 8
    total = len(heights) * bw + (len(heights) - 1) * gap
    sx = x + (w - total) // 2
    base = y + h - 18
    for i, hh in enumerate(heights):
        tx = sx + i * (bw + gap)
        cv.fill(tx, base - hh, bw, hh, NAVY if i % 2 else BLUE)
        for wy in range(base - hh + 6, base - 4, 10):
            cv.fill(tx + 4, wy, bw - 8, 3, GOLD)
    cv.disc(x + w - 30, y + 12, 9, GOLD)


def draw_cop(cv, x, y, w, h):
    cv.fill(x, y, w, h, PAPER)
    cx, cy = x + w // 2, y + h // 2
    cv.disc(cx, cy, 22, BLUE)
    cv.ring(cx, cy, 22, NAVY, 2)
    cv.line(cx - 22, cy, cx + 22, cy, SKY)
    cv.line(cx, cy - 22, cx, cy + 22, SKY)
    cv.ring(cx, cy, 11, SKY, 1)
    cv.poly([(cx + 26, cy + 16), (cx + 40, cy + 2), (cx + 40, cy + 20)], GREEN)
    cv.line(cx + 26, cy + 16, cx + 40, cy + 10, GREEN)
    cv.fill(x, y + h - 6, w, 3, GREEN)


def draw_baseball(cv, x, y, w, h):
    cv.fill(x, y, w, h, GREEN)
    cv.poly([(x + 8, y + h - 8), (x + w // 2, y + 8), (x + w - 8, y + h - 8)], (110, 170, 90))
    cv.poly([(x + w // 2 - 14, y + h - 8), (x + w // 2, y + h - 30), (x + w // 2 + 14, y + h - 8)], SAND)
    cv.disc(x + w // 2, y + h - 8, 4, WHITE)
    cv.disc(x + w - 26, y + 16, 9, WHITE)
    cv.line(x + w - 32, y + 12, x + w - 20, y + 20, RED)
    cv.line(x + w - 20, y + 12, x + w - 32, y + 20, RED)
    cv.fill(x + 8, y + 8, 30, 4, BROWN)
    cv.line(x + 12, y + 12, x + 34, y + 30, BROWN)


def draw_nuclear(cv, x, y, w, h):
    cv.fill(x, y, w, h, NAVY)
    cx, cy = x + w // 2, y + h // 2
    cv.ring(cx, cy, 20, GOLD, 2)
    cv.ring(cx, cy, 13, WHITE, 1)
    cv.disc(cx, cy, 5, RED)
    cv.disc(cx + 20, cy, 3, GOLD)
    cv.disc(cx - 14, cy - 14, 3, GOLD)
    cv.disc(cx - 14, cy + 14, 3, GOLD)
    cv.line(cx, cy - 26, cx, cy - 20, GOLD)
    cv.line(cx, cy + 20, cx, cy + 26, GOLD)


def draw_flags(cv, x, y, w, h):
    cv.fill(x, y, w, h, PAPER)
    fw = (w - 20) // 2
    fh = h - 16
    fx, fy = x + 6, y + 8
    cv.fill(fx, fy, fw, fh, WHITE)
    stripe = fh // 7
    for s in range(0, 7, 2):
        cv.fill(fx, fy + s * stripe, fw, stripe, RED)
    cv.fill(fx, fy, fw // 2, fh // 2, BLUE)
    for k in range(3):
        for j in range(2):
            cv.disc(fx + 5 + k * 9, fy + 5 + j * 9, 1, WHITE)
    rx = fx + fw + 8
    cv.fill(rx, fy, fw, fh // 3, GOLD)
    cv.fill(rx, fy + fh // 3, fw, fh // 3, BLUE)
    cv.fill(rx, fy + 2 * fh // 3, fw, fh - 2 * fh // 3, RED)
    cv.frame(fx, fy, fw, fh, INK, 1)
    cv.frame(rx, fy, fw, fh, INK, 1)
    cv.line(x + w // 2 - 4, y + h - 8, x + w // 2 + 4, y + h - 8, INK)


def draw_court(cv, x, y, w, h):
    cv.fill(x, y, w, h, PAPER)
    cx = x + w // 2
    cv.poly([(cx - 52, y + 18), (cx + 52, y + 18), (cx, y + 4)], NAVY)
    cv.fill(cx - 56, y + 18, 112, 4, NAVY)
    for k in range(4):
        px = cx - 44 + k * 28
        cv.fill(px, y + 24, 6, h - 34, BLUE)
        cv.fill(px - 2, y + 22, 10, 3, BLUE)
        cv.fill(px - 2, y + h - 12, 10, 3, BLUE)
    cv.fill(cx - 56, y + h - 8, 112, 4, NAVY)
    cv.fill(cx - 60, y + h - 4, 120, 3, INK)


def draw_drought(cv, x, y, w, h):
    cv.fill(x, y, w, h, (250, 238, 200))
    cv.disc(x + w - 34, y + 14, 12, GOLD)
    cv.ring(x + w - 34, y + 14, 16, GOLD, 1)
    base = y + h - 22
    cv.fill(x, base, w, 22, TAN)
    cv.fill(x, base, w, 3, BROWN)
    cv.line(x + 10, base + 4, x + 30, base + 16, BROWN)
    cv.line(x + 30, base + 16, x + 52, base + 8, BROWN)
    cv.line(x + 60, base + 4, x + 74, base + 18, BROWN)
    cv.line(x + 96, base + 6, x + 110, base + 16, BROWN)
    cv.line(x + 130, base + 4, x + 150, base + 14, BROWN)
    cv.poly([(x + 24, base), (x + 30, base - 26), (x + 36, base)], GREEN)
    cv.poly([(x + 30, base - 26), (x + 44, base - 18), (x + 34, base - 12)], GREEN)


def draw_cricket(cv, x, y, w, h):
    cv.fill(x, y, w, h, GREEN)
    cv.fill(x + 20, y + 8, w - 40, h - 16, (110, 170, 90))
    for k in range(3):
        sx = x + w // 2 - 12 + k * 10
        cv.fill(sx, y + 12, 4, 18, GOLD)
        cv.fill(sx - 1, y + 10, 6, 3, GOLD)
    cv.line(x + 24, y + h - 14, x + w - 30, y + 16, BROWN)
    cv.fill(x + w - 34, y + 12, 10, 5, BROWN)
    cv.disc(x + w // 2 + 26, y + h - 18, 6, RED)
    cv.disc(x + 30, y + 20, 4, WHITE)


def draw_chart(cv, x, y, w, h):
    cv.fill(x, y, w, h, WHITE)
    cv.line(x + 8, y + 8, x + 8, y + h - 10, GREY)
    cv.line(x + 8, y + h - 10, x + w - 8, y + h - 10, GREY)
    bars = [(16, 30, 12, GREEN), (34, 22, 10, RED), (50, 26, 14, GREEN), (68, 16, 12, GREEN), (86, 20, 10, RED), (104, 12, 14, GREEN)]
    base = y + h - 10
    for bx, top, bh, color in bars:
        cv.fill(x + bx, y + top, 10, bh, color)
        cv.line(x + bx + 5, y + top - 6, x + bx + 5, y + top + bh + 4, INK)
    cv.line(x + 16, y + 26, x + 116, y + 12, RED)
    cv.disc(x + w - 22, y + 12, 4, RED)


ART = {
    "cyclone": draw_cyclone,
    "iran": draw_iran,
    "europe": draw_europe,
    "kafd": draw_kafd,
    "apec": draw_apec,
    "cop": draw_cop,
    "baseball": draw_baseball,
    "nuclear": draw_nuclear,
    "flags": draw_flags,
    "court": draw_court,
    "drought": draw_drought,
    "cricket": draw_cricket,
    "chart": draw_chart,
}

# ---------------------------------------------------------------------------
# Layout. All coordinates are in the 1024x1024 canvas.
# ---------------------------------------------------------------------------

COL_W = 193
COL_GAP = 6
COL_X = [16 + i * (COL_W + COL_GAP) for i in range(5)]
ROW_Y = [128, 266, 404]
ROW_H = 132


def draw_masthead(cv):
    cv.hline(16, 10, 992, INK, 3)
    cv.hline(16, 15, 992, INK, 1)
    px_text(cv, 16, 22, "FRIDAY 20 NOVEMBER 2026", RED, 1)
    right = "ONE DAY - 50 STORIES - 7 REGIONS"
    px_text(cv, 1024 - 16 - px_width(right, 1), 22, right, INK, 1)
    serif_centered(cv, 16, 34, 992, "THE WORLD TODAY", INK, 5)
    serif_centered(
        cv, 16, 86, 992,
        "CYCLONE AKVAN LANDFALL - TRUMP WAITS ON IRAN - EUROPE READY TO TALK",
        RED, 1)
    cv.hline(16, 100, 992, INK, 2)
    cv.hline(16, 104, 992, INK, 1)


def draw_small_lead(cv, lead, x, y):
    num, kicker, art, headline, _deck = lead
    cv.frame(x, y, COL_W, ROW_H, INK, 1)
    ART[art](cv, x + 1, y + 1, COL_W - 2, 52)
    px_text(cv, x + 8, y + 58, num + " " + kicker, RED, 1)
    serif_para(cv, x + 8, y + 70, COL_W - 16, headline, INK, 2, leading=19)


def draw_hero_lead(cv, lead, x, y):
    num, kicker, art, headline, deck = lead
    w = 2 * COL_W + COL_GAP
    cv.frame(x, y, w, ROW_H, INK, 1)
    ART[art](cv, x + 1, y + 1, 168, ROW_H - 2)
    tx = x + 176
    tw = w - 184
    px_text(cv, tx, y + 8, num, RED, 2)
    px_text(cv, tx + 18, y + 11, kicker, RED, 1)
    serif_para(cv, tx, y + 26, tw, headline, INK, 2, leading=19)
    px_para(cv, tx, y + 88, tw, deck, INK, 1, leading=10)


def draw_mini_numbers(cv, x, y):
    cv.frame(x, y, COL_W, ROW_H, INK, 1)
    px_text(cv, x + 8, y + 8, "FRIDAY IN NUMBERS", RED, 1)
    for i, (big, label) in enumerate(MINI_NUMBERS):
        ry = y + 26 + i * 38
        serif_text(cv, x + 8, ry, big, RED, 2)
        px_text(cv, x + 8, ry + 20, label, INK, 1)


def draw_leads(cv):
    draw_hero_lead(cv, LEADS[0], COL_X[0], ROW_Y[0])
    for i in range(1, 4):
        draw_small_lead(cv, LEADS[i], COL_X[i + 1], ROW_Y[0])
    for i in range(4, 9):
        draw_small_lead(cv, LEADS[i], COL_X[i - 4], ROW_Y[1])
    for i in range(9, 13):
        draw_small_lead(cv, LEADS[i], COL_X[i - 9], ROW_Y[2])
    draw_mini_numbers(cv, COL_X[4], ROW_Y[2])


def draw_numbers(cv, y=544):
    cell_w = (992 - 5 * COL_GAP) // 6
    for i, (big, label) in enumerate(NUMBERS):
        cx = 16 + i * (cell_w + COL_GAP)
        cv.frame(cx, y, cell_w, 54, INK, 1)
        serif_centered(cv, cx, y + 6, cell_w, big, RED, 2)
        px_centered(cv, cx, y + 32, cell_w, label, INK, 1)


def draw_also(cv, y=606):
    px_text(cv, 16, y, "ALSO ON FRIDAY - STORIES 14 TO 50", RED, 1)
    cv.hline(16, y + 12, 992, INK, 1)
    y += 20
    col_w = (992 - 2 * 16) // 3
    cols = [ALSO[0:13], ALSO[13:25], ALSO[25:37]]
    for ci, col in enumerate(cols):
        cx = 16 + ci * (col_w + 16)
        for ri, item in enumerate(col):
            num = str(14 + (13 if ci == 1 else 25 if ci == 2 else 0) + ri)
            ry = y + ri * 14
            px_text(cv, cx, ry, num, RED, 1)
            px_text(cv, cx + 22, ry, item, INK, 1)


def draw_map(cv, y=816):
    mx, my, mw, mh = 16, y, 470, 98
    cv.fill(mx, my, mw, mh, SKY)
    cv.frame(mx, my, mw, mh, INK, 1)
    px_text(cv, mx + 8, my + 6, "WHERE IT HAPPENED", RED, 1)

    def to_xy(lon, lat):
        px = mx + 8 + int((lon + 180) / 360 * (mw - 16))
        py = my + 22 + int((75 - lat) / 135 * (mh - 32))
        return px, py

    for cont in CONTINENTS:
        pts = [to_xy(lon, lat) for lon, lat in cont]
        cv.poly(pts, SAND)
    for num, lon, lat in PINS:
        px, py = to_xy(lon, lat)
        cv.disc(px, py, 6, RED)
        px_text(cv, px - px_width(num, 1) // 2, py - 3, num, WHITE, 1)


def draw_side(cv, y=816):
    x, w, h = 498, 510, 98
    cv.frame(x, y, w, h, INK, 1)
    px_text(cv, x + 8, y + 6, "SEVEN REGIONS, ONE DAY", RED, 1)
    px_para(cv, x + 8, y + 20, w - 16, REGIONS_LINE, INK, 1, leading=11)
    px_text(cv, x + 8, y + 44, "HOW TO READ THIS PAGE", RED, 1)
    px_para(cv, x + 8, y + 58, w - 16, HOW_TO_READ, INK, 1, leading=11)


def draw_footer(cv, y=922):
    cv.fill(16, y, 110, 20, RED)
    px_text(cv, 24, y + 6, "DATE CHECK", WHITE, 1)
    px_text(cv, 134, y + 6, "LEFT OUT ON PURPOSE - FIRST REPORTED BEFORE FRIDAY:", INK, 1)
    y += 26
    y = px_para(cv, 16, y, 992, DATE_CHECK, INK, 1, leading=11)
    y += 4
    cv.hline(16, y, 992, INK, 1)
    y += 6
    px_text(
        cv, 16, y,
        "EVERY STORY HERE HAPPENED, OR WAS FIRST REPORTED, ON FRIDAY 20 NOVEMBER 2026.",
        INK, 1)
    y += 11
    px_text(
        cv, 16, y,
        "CLAIM = ONE SIDE'S ACCOUNT, NOT INDEPENDENTLY CONFIRMED. SOURCES: AP, REUTERS, AFP, BBC, CNN, THE HINDU, IMD. ORIGINAL DRAWINGS.",
        GREY, 1)


def build_page():
    cv = Canvas(WIDTH, HEIGHT, PAPER)
    draw_masthead(cv)
    px_text(cv, 16, 112, "THE LEADS - 13 STORIES THAT MADE FRIDAY", RED, 1)
    cv.hline(16, 122, 992, INK, 1)
    draw_leads(cv)
    draw_numbers(cv)
    draw_also(cv)
    draw_map(cv)
    draw_side(cv)
    draw_footer(cv)
    return cv


def main():
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    page = build_page()
    data = encode_png(WIDTH, HEIGHT, page.buf)
    target = out_dir / "entry.png"
    target.write_bytes(data)
    if len(data) > 1048576:
        raise SystemExit("entry.png exceeds 1 MiB: %d bytes" % len(data))


if __name__ == "__main__":
    main()
