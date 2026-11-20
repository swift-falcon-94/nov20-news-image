#!/usr/bin/env python3
"""The World Today - 20 November 2026: one dense 1024x1024 news image.

Stdlib-only Python, no network, deterministic: two runs write identical
bytes. Everything is drawn at 2048x2048 and averaged down to 1024x1024,
so small text stays crisp. A 5x7 bitmap font carries the small print, a
12x16 stroke font carries the masthead. The picture sums up Friday
20 November 2026 in 54 verified stories across 6 continents, with a
world map drawn from real coastline coordinates, a UTC timeline strip,
a date-check box and a source list.

Run: mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
Writes entry.png into MAKEFUN_OUTPUT_DIR (or /output, or ./out).
"""
import math
import os
import struct
import sys
import zlib

SCALE = 2
W, H = 1024, 1024
PW, PH = W * SCALE, H * SCALE

BG = (13, 27, 46)
BG2 = (18, 38, 62)
PANEL = (24, 48, 76)
PANEL2 = (30, 58, 90)
FG = (235, 240, 246)
DIM = (168, 186, 205)
GOLD = (255, 196, 66)
SKY = (86, 199, 255)
RED = (255, 107, 97)
GREEN = (96, 214, 149)
EDGE = (58, 92, 128)
LANDC = (46, 98, 88)
SEAC = (16, 42, 68)

# ---------------------------------------------------------------- 5x7 font
# One glyph = 35 bits, 7 rows of 5, row-major, '1' = ink.
F5 = {}


def _g(ch, bits):
    F5[ch] = [bits[i * 5:(i + 1) * 5] for i in range(7)]


_g('A', "01110100011000111111100011000110001")
_g('B', "11110100011000111110100011000111110")
_g('C', "01110100011000010000100001000101110")
_g('D', "11110100011000110001100011000111110")
_g('E', "11111100001000011110100001000011111")
_g('F', "11111100001000011110100001000010000")
_g('G', "01110100011000010111100011000101111")
_g('H', "10001100011000111111100011000110001")
_g('I', "01110001000010000100001000010001110")
_g('J', "00111000100001000010000101001001100")
_g('K', "10001100101010011000101001001010001")
_g('L', "10000100001000010000100001000011111")
_g('M', "10001110111010110101100011000110001")
_g('N', "10001110011010110011100011000110001")
_g('O', "01110100011000110001100011000101110")
_g('P', "11110100011000111110100001000010000")
_g('Q', "01110100011000110001101011001001101")
_g('R', "11110100011000111110101001001010001")
_g('S', "01111100001000001110000010000111110")
_g('T', "11111001000010000100001000010000100")
_g('U', "10001100011000110001100011000101110")
_g('V', "10001100011000110001100010101000100")
_g('W', "10001100011000110101101011101110001")
_g('X', "10001100010101000100010101000110001")
_g('Y', "10001100010101000100001000010000100")
_g('Z', "11111000010001000100010001000011111")
_g('0', "01110100011001110101110011000101110")
_g('1', "00100011000010000100001000010001110")
_g('2', "01110100010000100110010001000011111")
_g('3', "11111000100010000010000011000101110")
_g('4', "00010001100101010010111110001000010")
_g('5', "11111100001111000001000011000101110")
_g('6', "00110010001000011110100011000101110")
_g('7', "11111000010001000100010000100001000")
_g('8', "01110100011000101110100011000101110")
_g('9', "01110100011000101111000010001001100")
_g(' ', "00000000000000000000000000000000000")
_g('.', "00000000000000000000000000110001100")
_g(',', "00000000000000000000011000010001000")
_g(':', "00000011000110000000011000110000000")
_g(';', "00000011000110000000011000010001000")
_g('-', "00000000000000001110000000000000000")
_g("'", "00100001000100000000000000000000000")
_g('/', "00001000100001000100010000100010000")
_g('(', "00010001000100001000010000010000010")
_g(')', "01000001000001000010000100010001000")
_g('%', "10001100100010001000010011000110001")
_g('+', "00000001000010011111001000010000000")
_g('=', "00000000001111100000111110000000000")
_g('?', "01110100010000100110001000000000100")
_g('!', "00100001000010000100001000000000100")
_g('&', "01100100101010001000101011001001101")
_g('$', "00100011111010001110001011111000100")
_g('#', "01010010101111101010111110101001010")
_g('*', "00000001001010101110101010010000000")
_g('_', "00000000000000000000000000000011111")
_g('>', "10000010000010000010001000100010000")
_g('<', "00001000100010001000001000001000001")
_g('•', "00000000000110001100011000000000000")
_g('"', "01010010100000000000000000000000000")
_g('[', "01110010000100001000010000100001110")
_g(']', "01110000100001000010000100001001110")


def txt_w(s, adv=6):
    return max(0, len(s) * adv - 1)


def wrap(s, n):
    words = s.split(' ')
    lines, cur = [], ''
    for w in words:
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= n:
            cur += ' ' + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

# ------------------------------------------------------- 12x16 stroke font
# Strokes in a 12 wide x 16 tall grid. _p appends one polyline to a glyph.
S16 = {}


def _p(ch, pts):
    S16.setdefault(ch, []).append(pts)


_p('A', [(1, 15), (6, 1), (11, 15)])
_p('A', [(4, 10), (8, 10)])
_p('B', [(1, 1), (1, 15)])
_p('B', [(1, 1), (8, 1), (10, 3), (10, 6), (8, 8), (1, 8)])
_p('B', [(1, 8), (8, 8), (10, 10), (10, 13), (8, 15), (1, 15)])
_p('C', [(10, 3), (8, 1), (4, 1), (2, 3), (1, 8), (2, 13), (4, 15), (8, 15), (10, 13)])
_p('D', [(1, 1), (1, 15)])
_p('D', [(1, 1), (8, 1), (11, 4), (11, 12), (8, 15), (1, 15)])
_p('E', [(1, 1), (1, 15)])
_p('E', [(1, 1), (10, 1)])
_p('E', [(1, 8), (8, 8)])
_p('E', [(1, 15), (10, 15)])
_p('F', [(1, 1), (1, 15)])
_p('F', [(1, 1), (10, 1)])
_p('F', [(1, 8), (8, 8)])
_p('G', [(10, 3), (8, 1), (4, 1), (2, 3), (1, 8), (2, 13), (4, 15), (8, 15), (10, 13), (10, 9), (6, 9)])
_p('H', [(1, 1), (1, 15)])
_p('H', [(11, 1), (11, 15)])
_p('H', [(1, 8), (11, 8)])
_p('I', [(4, 1), (8, 1)])
_p('I', [(6, 1), (6, 15)])
_p('I', [(4, 15), (8, 15)])
_p('J', [(11, 1), (11, 12), (9, 15), (5, 15), (3, 13)])
_p('K', [(1, 1), (1, 15)])
_p('K', [(10, 1), (1, 8)])
_p('K', [(3, 7), (11, 15)])
_p('L', [(1, 1), (1, 15)])
_p('L', [(1, 15), (10, 15)])
_p('M', [(1, 15), (1, 1), (6, 9), (11, 1), (11, 15)])
_p('N', [(1, 15), (1, 1), (11, 15), (11, 1)])
_p('O', [(4, 1), (8, 1), (11, 4), (11, 12), (8, 15), (4, 15), (1, 12), (1, 4), (4, 1)])
_p('P', [(1, 1), (1, 15)])
_p('P', [(1, 1), (8, 1), (11, 4), (11, 6), (8, 9), (1, 9)])
_p('Q', [(4, 1), (8, 1), (11, 4), (11, 12), (8, 15), (4, 15), (1, 12), (1, 4), (4, 1)])
_p('Q', [(7, 11), (11, 15)])
_p('R', [(1, 1), (1, 15)])
_p('R', [(1, 1), (8, 1), (11, 4), (11, 6), (8, 9), (1, 9)])
_p('R', [(4, 9), (11, 15)])
_p('S', [(10, 3), (8, 1), (4, 1), (2, 3), (1, 5), (3, 8), (9, 8), (11, 10), (10, 13), (8, 15), (4, 15), (2, 13)])
_p('T', [(1, 1), (11, 1)])
_p('T', [(6, 1), (6, 15)])
_p('U', [(1, 1), (1, 12), (3, 15), (8, 15), (11, 12), (11, 1)])
_p('V', [(1, 1), (6, 15), (11, 1)])
_p('W', [(1, 1), (3, 15), (6, 8), (9, 15), (11, 1)])
_p('X', [(1, 1), (11, 15)])
_p('X', [(11, 1), (1, 15)])
_p('Y', [(1, 1), (6, 8)])
_p('Y', [(11, 1), (6, 8)])
_p('Y', [(6, 8), (6, 15)])
_p('Z', [(1, 1), (11, 1), (1, 15), (11, 15)])
_p('0', [(4, 1), (8, 1), (11, 4), (11, 12), (8, 15), (4, 15), (1, 12), (1, 4), (4, 1)])
_p('0', [(3, 4), (9, 12)])
_p('1', [(6, 1), (6, 15)])
_p('1', [(4, 3), (6, 1)])
_p('1', [(3, 15), (9, 15)])
_p('2', [(2, 3), (4, 1), (8, 1), (10, 3), (10, 6), (1, 15), (11, 15)])
_p('3', [(1, 1), (10, 1), (10, 5), (6, 8), (10, 11), (10, 13), (8, 15), (1, 15)])
_p('4', [(9, 1), (9, 15)])
_p('4', [(1, 10), (9, 10)])
_p('4', [(9, 1), (1, 10)])
_p('5', [(10, 1), (1, 1), (1, 8), (8, 8), (10, 10), (10, 13), (8, 15), (1, 15)])
_p('6', [(10, 3), (8, 1), (4, 1), (2, 3), (1, 8), (1, 12), (3, 15), (8, 15), (10, 13), (10, 10), (8, 8), (1, 8)])
_p('7', [(1, 1), (11, 1), (5, 15)])
_p('8', [(4, 1), (8, 1), (11, 4), (11, 6), (8, 8), (4, 8), (1, 6), (1, 4), (4, 1)])
_p('8', [(4, 8), (8, 8), (11, 11), (11, 13), (8, 15), (4, 15), (1, 13), (1, 11), (4, 8)])
_p('9', [(1, 13), (1, 10), (3, 8), (8, 8), (11, 10), (11, 12), (9, 15), (4, 15), (2, 13)])
_p(' ', [])
_p('-', [(2, 8), (10, 8)])
_p('.', [(5, 14), (7, 14), (7, 15), (5, 15)])
_p(':', [(5, 5), (7, 5), (7, 7), (5, 7)])
_p(':', [(5, 11), (7, 11), (7, 13), (5, 13)])
_p('/', [(10, 15), (2, 1)])
_p('•', [(5, 7), (7, 7), (7, 9), (5, 9)])
_p("'", [(5, 1), (7, 4)])


def stroke_w(s, adv=14):
    return max(0, len(s) * adv - 2)


# ------------------------------------------------------------------ canvas
class Img:
    """RGB buffer at device resolution (2048x2048).

    All drawing calls take LOGICAL 1024x1024 coordinates; every primitive
    is scaled to device pixels before it is rasterised, and the buffer is
    averaged 2x2 down to 1024x1024 on export.
    """

    def __init__(self):
        self.px = bytearray(PW * PH * 3)
        self.rect(0, 0, W, H, BG)

    def _put(self, dx, dy, c):
        if 0 <= dx < PW and 0 <= dy < PH:
            o = (dy * PW + dx) * 3
            self.px[o] = c[0]
            self.px[o + 1] = c[1]
            self.px[o + 2] = c[2]

    def rect(self, x, y, w, h, c):
        x0 = max(0, int(x * SCALE))
        y0 = max(0, int(y * SCALE))
        x1 = min(PW, int((x + w) * SCALE))
        y1 = min(PH, int((y + h) * SCALE))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            o = (yy * PW + x0) * 3
            self.px[o:o + len(row)] = row

    def hline(self, x, y, w, c, thick=1):
        self.rect(x, y, w, thick, c)

    def seg(self, x0, y0, x1, y1, c, t=1):
        # Bresenham at device resolution; t = thickness in device px.
        ax0, ay0 = int(round(x0 * SCALE)), int(round(y0 * SCALE))
        ax1, ay1 = int(round(x1 * SCALE)), int(round(y1 * SCALE))
        dx, dy = abs(ax1 - ax0), abs(ay1 - ay0)
        sx = 1 if ax0 < ax1 else -1
        sy = 1 if ay0 < ay1 else -1
        err = dx - dy
        r = max(0, t // 2)
        while True:
            for oy in range(-r, r + 1):
                for ox in range(-r, r + 1):
                    self._put(ax0 + ox, ay0 + oy, c)
            if ax0 == ax1 and ay0 == ay1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                ax0 += sx
            if e2 < dx:
                err += dx
                ay0 += sy

    def disc(self, cx, cy, r, c, fill=True):
        cr = int(round(r * SCALE))
        ccx, ccy = int(round(cx * SCALE)), int(round(cy * SCALE))
        for dy in range(-cr, cr + 1):
            dx = int((cr * cr - dy * dy) ** 0.5) if abs(dy) <= cr else 0
            if fill:
                for xx in range(ccx - dx, ccx + dx + 1):
                    self._put(xx, ccy + dy, c)
            else:
                self._put(ccx - dx, ccy + dy, c)
                self._put(ccx + dx, ccy + dy, c)
                self._put(ccx, ccy + dy, c)

    def arc(self, cx, cy, r, a0, a1, c, t=2, steps=40):
        prev = None
        for i in range(steps + 1):
            a = a0 + (a1 - a0) * i / steps
            p = (cx + r * math.cos(a), cy + r * math.sin(a))
            if prev is not None:
                self.seg(prev[0], prev[1], p[0], p[1], c, t)
            prev = p

    def gon(self, pts, c, fill=True):
        dpts = [(int(round(x * SCALE)), int(round(y * SCALE))) for x, y in pts]
        if fill:
            ys = [p[1] for p in dpts]
            for yy in range(max(0, min(ys)), min(PH, max(ys) + 1)):
                xs = []
                for i in range(len(dpts)):
                    x0, y0 = dpts[i]
                    x1, y1 = dpts[(i + 1) % len(dpts)]
                    if (y0 <= yy < y1) or (y1 <= yy < y0):
                        xs.append(x0 + (yy - y0) * (x1 - x0) / (y1 - y0))
                xs.sort()
                for k in range(0, len(xs) - 1, 2):
                    for xx in range(max(0, int(xs[k])), min(PW, int(xs[k + 1]) + 1)):
                        self._put(xx, yy, c)
        else:
            for i in range(len(dpts)):
                x0, y0 = dpts[i]
                x1, y1 = dpts[(i + 1) % len(dpts)]
                self.seg(x0 / SCALE, y0 / SCALE, x1 / SCALE, y1 / SCALE, c, 2)

    # -- text: 5x7 bitmap -----------------------------------------------
    def txt(self, x, y, s, c, adv=6, sc=1):
        cx = x
        for ch in s.upper():
            rows = F5.get(ch, F5[' '])
            for ry in range(7):
                row = rows[ry]
                for rx in range(5):
                    if row[rx] == '1':
                        self.rect(cx + rx * sc, y + ry * sc, sc, sc, c)
            cx += adv * sc

    def txtc(self, x, y, w, s, c, adv=6, sc=1):
        self.txt(x + (w - txt_w(s, adv) * sc) / 2, y, s, c, adv, sc)

    # -- text: 12x16 stroke ---------------------------------------------
    def stxt(self, x, y, s, c, adv=14, h=30, t=3):
        cx = x
        sx = adv / 12.0
        sy = h / 16.0
        for ch in s.upper():
            for poly in S16.get(ch, []):
                for i in range(len(poly) - 1):
                    self.seg(cx + poly[i][0] * sx, y + poly[i][1] * sy,
                             cx + poly[i + 1][0] * sx, y + poly[i + 1][1] * sy,
                             c, t)
            cx += adv

    def stxtc(self, x, y, w, s, c, adv=14, h=30, t=3):
        self.stxt(x + (w - stroke_w(s, adv)) / 2, y, s, c, adv, h, t)

    # -- export ----------------------------------------------------------
    def png(self):
        out = bytearray(W * H * 3)
        for yy in range(H):
            for xx in range(W):
                r = g = b = 0
                for dy in range(SCALE):
                    base = ((yy * SCALE + dy) * PW + xx * SCALE) * 3
                    for dx in range(SCALE):
                        o = base + dx * 3
                        r += self.px[o]
                        g += self.px[o + 1]
                        b += self.px[o + 2]
                o2 = (yy * W + xx) * 3
                out[o2] = (r + 2) // 4
                out[o2 + 1] = (g + 2) // 4
                out[o2 + 2] = (b + 2) // 4
        rows = b''.join(b'\x00' + bytes(out[y * W * 3:(y + 1) * W * 3]) for y in range(H))
        ihdr = struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)

        def chunk(kind, data):
            b = struct.pack('>I', len(data)) + kind + data
            return b + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)

        return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
                + chunk(b'IDAT', zlib.compress(bytes(rows), 9)) + chunk(b'IEND', b''))

# ----------------------------------------------------------------- stories
# (n, region, headline, body, lon, lat, illustration). 14 main cards.
STORIES = [
    (1, "ASIA",
     "AKVAN LANDFALL: GOPALPUR, NO DEATHS",
     "Crossed coast 07:30-08:30 IST, winds 70-80 km/h, gust 90, weaker than forecast. 370,000 evacuated, 423 teams out. Rain: Patrapur 209 mm. 3rd cyclone in 24 days.",
     85, 19, "cyclone"),
    (2, "UKRAINE",
     "KYIV BARRAGE: 110+ MISSILES OVERNIGHT",
     "Russia fired 110+ missiles, 400 drones into Fri. 8 killed, 28 hurt. 3 Dnipro bridges damaged. Poland scrambled jets as airspace was violated.",
     30, 50, "barrage"),
    (3, "JUSTICE",
     "MYANMAR: ICJ RULING UNFAIR (19 NOV)",
     "Thu: court ruled 9-6 Myanmar committed genocide vs Rohingya, a first for a state. Fri: Naypyitaw calls it unfair, not unanimous. Refugees celebrate, reparations next.",
     96, 21, "court"),
    (4, "SUMMIT",
     "SHENZHEN SUMMIT: 4-POINT PEACE PACT (19 NOV)",
     "Trump, Xi, Putin met 90 min, signed declaration: no nuclear war, oil supply, UN reform, ICC limits. No Ukraine or Iran deal. Trade truce extended.",
     114, 22, "summit"),
    (5, "GAMES",
     "GTA VI: $2.36BN ON DAY ONE (19 NOV)",
     "Sensor Tower estimate, NOT official: 24.6m copies by end of launch day, 75% PS5. Up from $1.84bn on Thu morning. Take-Two silent on figures.",
     -80, 26, "gta"),
    (6, "TECH",
     "ANTHROPIC +17% ON DEBUT, MARKETS FALL",
     "Opened $111.50, closed $97.17 on $83 offer. Record $81.3bn IPO. But S&P -2%, Nasdaq -2.3%; Fri Asia: Nikkei -4.8%, Kospi -5.2%.",
     -122, 38, "ipo"),
    (7, "EUROPE",
     "BERLIN: EUROPE READY TO TALK (19 NOV)",
     "Coalition of the Willing: Europe ready to negotiate with Russia, only with Kyiv at the table. Kushner: Trump open to NATO-style guarantee. No date set.",
     13, 52, "eu"),
    (8, "GULF",
     "RIYADH TOWER HIT BY MISSILE (19 NOV)",
     "Houthi missile struck the 80-storey PIF Tower, windows out on 7-8 floors, facade bent. No injuries. 2nd strike on a Riyadh landmark in 2 weeks.",
     47, 25, "tower"),
    (9, "SPACE",
     "VOYAGER 1 PASSES ONE LIGHT-DAY (19 NOV)",
     "First human object past one light-day, 26bn km, at 05:16 EST Thu. But no science data since 14 Nov, carrier signal only. Voyager 2 due 2035.",
     -118, 34, "voyager"),
    (10, "EUROPE",
     "YOUTH STRIKE SWEEPS EUROPE, 25 NATIONS",
     "Tens of thousands walk out Fri over living costs, housing, tuition and militarisation. Italy general strike, 100+ demos. Slogan: fight for our future.",
     2, 49, "crowd"),
    (11, "AFRICA",
     "SENEGAL BOAT SINKS, 4 DEAD, DOZENS LOST",
     "Pirogue capsized Wed 02:00 off Yenne, 50-100 aboard, hit a rock in transfer. 4 bodies found Thu, dozens missing. Canary arrivals up two-thirds in 2026.",
     -17, 15, "boat"),
    (12, "ASIA",
     "MONGOLIA PRESIDENT OUT, 96-104 VOTE",
     "Parliament accepts Khurelsukh resignation Fri. Announced 17 Nov over $25m bribery claims, denied. Speaker Byambatsogt acting head; vote within 4 months.",
     107, 48, "vote"),
    (13, "PACIFIC",
     "FIJI DROUGHT DISASTER, TONGA TOO",
     "Fiji declares national disaster, Tonga emergency as El Nino drought bites. Cook Islands emergency ahead of Cyclone Xavier. LA faces El Nino flood threat.",
     178, -18, "drought"),
    (14, "SPORT",
     "CRICKET: NICHOLLS 175*, INDIA FIGHT BACK",
     "NZ 368 in Wellington, Nicholls 175 not out, Phillips 118. India 159/1 at stumps Day 2: Jaiswal 85, Rahul 52 not out. Trail by 209.",
     175, -41, "cricket"),
]

ALSO = [
    "TRUMP-IRAN: DECISION PUSHED TO 2027; SENATE REJECTS WAR POWERS 51-48; IRAN OPS COST $48.3BN.",
    "HORMUZ: TANKER CATCHES FIRE AFTER HITTING A MINE; IEA CALLS IT THE TOP THREAT TO ENERGY SECURITY.",
    "GAZA: TANKS CROSSED YELLOW LINE 18 NOV, FIRST SINCE CEASEFIRE; 3 KILLED; 4 NATIONS URGE AID ACCESS.",
    "BANGLADESH: VIOLENCE AHEAD OF HASINA RETURN; ARSON IN GOPALGANJ; GOVT REJECTS PASSPORT REQUEST.",
    "US-VENEZUELA: HEGSETH SIGNS MILITARY DEAL IN CARACAS, UNDER A YEAR AFTER MADURO WAS CAPTURED.",
    "COP31: DRAFT DROPS FOSSIL-FUEL PHASE-OUT AND NET-ZERO DATES; PACIFIC NATIONS DEMAND PHASE-OUT.",
    "NVIDIA PROBE (19 NOV): CALIFORNIA AG SUBPOENAS NVIDIA OVER CHIPS TO CHINA; HUANG QUIT 12 NOV.",
    "BEPICOLOMBO REACHES MERCURY AFTER 8 YEARS; ORBIT INSERTION SET FOR SAT 21 NOV; SCIENCE FROM 2027.",
    "HAYABUSA2: JAXA DROPS 1998KY26 FLYBY AFTER ION ENGINES FAIL; NEW TARGET 2015BM510, FISCAL 2028.",
    "HAN DUCK-SOO: COURT ORDERS RETRIAL IN MARTIAL-LAW CASE; TOP COURT HAD OVERTURNED A CONVICTION.",
    "SOMALIA EXPELS UAE AMBASSADOR, ACCUSING ABU DHABI OF UNDERMINING ITS SOVEREIGNTY.",
    "DENMARK RATIFIES GREENLAND SECURITY DEAL WITH US UNANIMOUSLY, AFTER TAKEOVER TALK.",
    "SUDAN: DRONE STRIKE KILLS 10 AT GOLD MINE IN SOUTH KORDOFAN; AMNESTY URGES A PROBE.",
    "HAITI: FORCES KILL 34 SUSPECTED GANG MEMBERS IN MARTISSANT RAID TO RETAKE A KEY CORRIDOR.",
    "ETHIOPIA-ERITREA: DRONE AND ARTILLERY STRIKES NEAR BADME AMID A BUILDUP; WAR FEARS GROW.",
    "IRAQ ORDERS KATAIB HEZBOLLAH OUT OF JURF AL-NASR BY FRI, AMID SMUGGLING CLAIMS AND US PRESSURE.",
    "ISRAEL: MOSQUE SET ON FIRE IN AL-DAHI; 8 HURT AS DRIVER RAMS PALESTINIANS IN KAFR QASIM.",
    "UK-EU SUMMIT (FRI): YOUTH MOBILITY SCHEME EXPECTED; BURNHAM REOPENS THE BREXIT DEBATE.",
    "POLAND: RZESZOW FLIGHTS HALTED, WARNING LIFTED 07:30; EU TO SUMMON RUSSIAN ENVOY OVER EMBASSY.",
    "ESTONIA TO SHUT ALL 3 RUSSIA CROSSINGS FROM 1 DEC AFTER ALLEGED GRU BOMB AND ARSON ATTEMPT.",
    "EU PROPOSES 45BN EURO UKRAINE LOAN, TO BE REPAID AFTER RUSSIA PAYS REPARATIONS.",
    "PRAGUE: HUGE PROTEST OVER MEDIA LAW; FRANCE: 4TH WEEKEND OF PROTESTS, 146,000 OUT SAT.",
    "US SENATE PASSES ENERGY PERMITTING OVERHAUL 62-33; MUST STILL CLEAR THE HOUSE.",
    "WHITE HOUSE FIRES CYBER DIRECTOR CAIRNCROSS AFTER OUTAGES; KIRSTEN DAVIES TO FILL ROLE.",
    "UN SECRETARY-GENERAL RACE STALLS AFTER 8 VOTES; P5 NOT AGREED; COSTA RICA CANDIDATE LEADS.",
    "JAPAN: CORE INFLATION HIGHEST THIS YEAR; BANK OF JAPAN SEEN ON TRACK TO RAISE RATES.",
    "BRAZIL: CENTRAL BANK SELLS $1BN TO CURB DOLLAR; REAL DOWN 18% IN A MONTH.",
    "KENYA: LAST EBOLA PATIENT OUT 11 NOV; 42-DAY COUNTDOWN TO EBOLA-FREE 23 DEC.",
    "ZIMBABWE: HALO TRUST DESTROYS ITS 250,000TH LANDMINE; FUNDS THREATEN 2030 GOAL.",
    "PAKISTAN: 22 MILITANTS KILLED IN NW RAIDS; 10 DIE AS BUS HITS A GAS TANKER.",
    "COLOMBIA: THOUSANDS PROTEST TAX PLANS IN BOGOTA; NATIONAL STRIKE CALLED.",
    "BUKELE REGISTERS FOR A THIRD TERM IN EL SALVADOR; 2025 CHANGE REMOVED TERM LIMITS.",
    "MODI MEETS PRINCE AND PRINCESS OF WALES IN NEW DELHI; INDIA-UK TIES DISCUSSED.",
    "PEW: ISLAM ON COURSE TO ECLIPSE CHRISTIANITY AS THE LARGEST RELIGION WITHIN A DECADE.",
    "GOLD -4.2%, DOWN 11% IN A MONTH; IMF WARNS GLOBAL DEBT NEARS 100% OF GDP.",
]

SPORT = [
    "SHELTON BEATS JODAR 7-6(8), 7-5 AT ATP FINALS IN TURIN; SEMI HOPES ALIVE.",
    "JEPCHIRCHIR BANNED 3 YEARS FOR DOPING, STRIPPED OF SYDNEY MARATHON TITLE.",
    "PETE ROSE PARDONED POSTHUMOUSLY BY TRUMP (19 NOV); 4,256 CAREER HITS.",
    "AIFF WINS GOLD IN AFC MEMBER ASSOCIATION OF THE YEAR IN BANGKOK (19 NOV).",
    "FIFA PRESIDENT ELECTION SET FOR 2027; THREE CANDIDATES CONFIRMED.",
]

SOURCES = "SOURCES: BBC, REUTERS, CNN, AP, AFP, THE HINDU, IMD, ONETURN, NASA, ESA/JAXA, UNHCR, SENSOR TOWER, WSJ, AL JAZEERA."
TOTAL = len(STORIES) + len(ALSO) + len(SPORT)

# ------------------------------------------------------------- world map
# Coastline polygons as "lon,lat lon,lat ..." strings, parsed at draw time.
def _pts(s):
    out = []
    for tok in s.split():
        lo, la = tok.split(',')
        out.append((float(lo), float(la)))
    return out


LAND = [
    _pts("-168,66 -158,58 -140,60 -130,54 -125,49 -124,42 -120,34 -114,29 -110,24 -105,20 -97,16 -92,15 -86,12 -83,9 -79,9 -80,13 -84,16 -87,21 -90,21 -91,19 -97,26 -93,30 -89,30 -84,30 -81,25 -80,32 -76,35 -74,40 -70,42 -66,45 -60,47 -65,50 -60,52 -55,52 -60,55 -65,58 -68,58 -78,62 -85,66 -92,66 -95,69 -110,68 -125,70 -140,70 -155,71 -165,68 -168,66"),
    _pts("-45,60 -40,64 -32,68 -25,70 -20,74 -30,76 -45,76 -55,74 -58,70 -53,64 -45,60"),
    _pts("-79,9 -75,11 -72,12 -64,11 -60,8 -55,6 -52,5 -50,0 -44,-3 -38,-5 -35,-8 -40,-20 -48,-27 -52,-33 -57,-38 -65,-41 -68,-50 -69,-52 -74,-54 -73,-45 -73,-35 -71,-30 -70,-20 -75,-15 -79,-8 -81,-4 -80,1 -79,9"),
    _pts("-6,35 -10,31 -15,27 -17,21 -17,15 -15,11 -12,8 -8,5 -4,5 0,6 6,4 9,4 13,0 12,-5 13,-10 12,-17 16,-28 20,-35 28,-33 32,-29 36,-22 40,-15 40,-10 42,-5 46,-1 51,2 51,11 48,11 44,11 40,15 38,18 37,22 35,28 32,31 25,32 19,33 11,34 10,37 0,36 -6,35"),
    _pts("-10,36 -9,43 -2,44 -1,46 -4,48 -1,50 2,51 5,53 8,57 10,59 5,60 5,62 10,64 12,66 18,69 25,71 32,70 40,68 50,69 60,69 70,72 80,73 90,75 100,77 110,74 120,73 130,72 140,72 150,70 158,69 162,66 170,66 178,65 178,62 170,60 162,60 158,58 156,52 150,59 142,55 140,50 135,45 130,42 127,40 126,38 122,38 120,32 121,28 118,25 112,22 108,18 105,10 103,8 100,7 98,10 95,16 92,21 90,22 86,20 82,17 80,15 77,8 75,12 72,20 68,23 66,25 62,25 58,25 56,26 54,27 51,28 50,30 48,30 44,29 40,28 38,25 35,28 34,31 36,36 30,36 27,37 23,36 22,39 19,42 15,44 12,45 8,44 3,43 0,40 -2,37 -6,36 -10,36"),
    _pts("-5,50 -3,53 -5,56 -3,58 -1,57 0,53 -1,51 -5,50"),
    _pts("113,-22 114,-30 115,-33 118,-35 124,-33 129,-32 132,-32 135,-35 138,-35 140,-38 145,-38 150,-37 153,-32 153,-27 150,-23 146,-19 142,-15 142,-11 137,-12 135,-15 132,-12 130,-13 126,-14 122,-17 118,-20 113,-22"),
    _pts("167,-45 170,-42 174,-39 177,-38 175,-37 172,-41 168,-44 167,-45"),
    _pts("130,31 132,33 135,34 138,35 140,38 141,41 143,43 145,44 142,44 140,40 138,37 135,35 132,33 130,31"),
    _pts("44,-16 47,-15 50,-16 49,-20 47,-24 44,-25 43,-21 44,-16"),
    _pts("95,5 98,3 100,0 103,-2 106,-6 110,-7 114,-8 118,-9 120,-10 124,-10 128,-8 130,-4 132,-2 131,1 128,1 124,0 120,0 116,1 112,2 108,3 104,2 100,5 95,5"),
]

PIN_OFF = {2: (14, -14), 5: (-16, -12), 6: (12, 8), 7: (-16, -12),
           9: (-16, -12), 10: (-18, 4), 13: (10, -12)}

# ---------------------------------------------------------- illustrations
def pic(img, kind, x, y, w, h):
    """One small original drawing inside (x, y, w, h), logical coords."""
    cx, cy = x + w // 2, y + h // 2
    if kind == "cyclone":
        for r in (22, 16, 10):
            img.arc(cx, cy, r, 0.3, 4.6, SKY, 2, 26)
        img.disc(cx, cy, 4, GOLD)
        img.seg(cx - 26, cy + 18, cx + 26, cy + 18, DIM, 1)
        img.txt(x + 2, y + h - 9, "70-80 KM/H", DIM)
    elif kind == "barrage":
        for i, (dx, dy) in enumerate([(-30, -14), (-8, -18), (14, -12), (30, -16)]):
            img.seg(cx + dx, cy + dy, cx + dx - 8, cy + dy + 22, RED if i % 2 else GOLD, 2)
            img.disc(cx + dx - 8, cy + dy + 22, 3, RED if i % 2 else GOLD)
        img.rect(x + 4, y + h - 8, w - 8, 3, EDGE)
    elif kind == "court":
        img.seg(cx, y + 4, cx, y + h - 8, GOLD, 2)
        img.seg(cx - 26, y + 10, cx + 26, y + 10, GOLD, 2)
        img.arc(cx - 18, y + 12, 9, 0, 3.15, SKY, 2, 16)
        img.arc(cx + 18, y + 12, 9, 0, 3.15, SKY, 2, 16)
        img.rect(cx - 3, y + h - 8, 6, 5, GOLD)
    elif kind == "summit":
        for i, c in enumerate((RED, GOLD, SKY)):
            px = x + 14 + i * (w - 28) // 2
            img.seg(px, y + 6, px, y + h - 6, DIM, 2)
            img.gon([(px, y + 6), (px + 20, y + 12), (px, y + 18)], c)
    elif kind == "gta":
        img.stxt(x + w // 2 - 20, y + 2, "VI", GOLD, adv=20, h=34, t=3)
        img.rect(x + 6, y + h - 12, w - 12, 2, SKY)
        img.txt(x + 6, y + h - 9, "$2.36BN", SKY)
    elif kind == "ipo":
        bars = [10, 18, 14, 26, 34]
        for i, bh in enumerate(bars):
            bx = x + 8 + i * 20
            img.rect(bx, y + h - 8 - bh, 13, bh, GREEN if i == 4 else SKY)
        img.seg(x + 6, y + h - 10 - 34, x + w - 8, y + 4, GOLD, 2)
        img.gon([(x + w - 8, y + 4), (x + w - 18, y + 2), (x + w - 14, y + 12)], GOLD)
    elif kind == "eu":
        img.disc(cx, cy, 20, (0, 51, 153))
        for i in range(12):
            a = 2 * math.pi * i / 12 - math.pi / 2
            img.disc(int(cx + 13 * math.cos(a)), int(cy + 13 * math.sin(a)), 2, GOLD)
    elif kind == "tower":
        img.rect(cx - 9, y + 12, 18, h - 16, PANEL2)
        img.seg(cx, y + 2, cx, y + 12, DIM, 2)
        for fy in range(y + 16, y + h - 8, 7):
            img.seg(cx - 9, fy, cx + 9, fy, GOLD, 1)
        img.arc(cx + 16, y + 16, 8, 0.5, 2.6, RED, 2, 12)
        img.disc(cx + 20, y + 14, 2, RED)
    elif kind == "voyager":
        img.arc(cx - 6, cy - 4, 18, 3.4, 6.0, SKY, 2, 20)
        img.seg(cx - 6, cy - 4, cx - 6, cy + 20, DIM, 2)
        img.seg(cx - 16, cy + 20, cx + 4, cy + 20, DIM, 2)
        for sx, sy in ((x + 8, y + 6), (x + w - 10, y + 10), (x + 14, y + h - 8)):
            img.disc(sx, sy, 1, FG)
        img.txt(x + 2, y + h - 9, "26BN KM", DIM)
    elif kind == "crowd":
        for i in range(5):
            px = x + 12 + i * (w - 24) // 4
            img.disc(px, cy - 6, 6, GOLD if i % 2 == 0 else SKY)
            img.rect(px - 8, cy + 2, 16, h - cy - 4, PANEL2)
        img.seg(x + 4, y + h - 4, x + w - 4, y + h - 4, EDGE, 1)
    elif kind == "boat":
        img.gon([(x + 14, cy + 2), (x + w - 14, cy + 2), (x + w - 24, cy + 16), (x + 24, cy + 16)], SKY)
        img.seg(cx, cy + 2, cx, y + 6, DIM, 2)
        img.gon([(cx, y + 6), (cx + 16, cy), (cx, cy)], RED)
        img.seg(x + 6, cy + 22, x + w - 6, cy + 22, SKY, 1)
        img.seg(x + 12, cy + 26, x + w - 12, cy + 26, DIM, 1)
    elif kind == "vote":
        img.rect(cx - 20, cy - 2, 40, 26, PANEL2)
        img.seg(cx - 12, cy - 2, cx + 12, cy - 2, GOLD, 2)
        img.rect(cx - 8, cy - 14, 16, 12, FG)
        img.seg(cx - 4, cy - 8, cx - 1, cy - 4, RED, 2)
        img.seg(cx - 1, cy - 4, cx + 6, cy - 12, RED, 2)
    elif kind == "drought":
        img.disc(cx, y + 12, 8, GOLD)
        for i in range(8):
            a = math.pi * i / 4
            img.seg(int(cx + 11 * math.cos(a)), int(y + 12 + 11 * math.sin(a)),
                    int(cx + 16 * math.cos(a)), int(y + 12 + 16 * math.sin(a)), GOLD, 1)
        img.seg(x + 6, y + h - 12, cx - 8, y + h - 6, DIM, 1)
        img.seg(cx - 8, y + h - 6, cx + 6, y + h - 12, DIM, 1)
        img.seg(cx + 6, y + h - 12, x + w - 6, y + h - 6, DIM, 1)
    elif kind == "cricket":
        img.seg(cx - 18, cy - 16, cx + 8, cy + 14, GOLD, 3)
        img.disc(cx + 18, cy - 14, 5, RED)
        for i in range(3):
            img.seg(x + 14 + i * 7, y + h - 16, x + 14 + i * 7, y + h - 4, DIM, 2)
        img.seg(x + 12, y + h - 16, x + 30, y + h - 16, DIM, 1)

# ------------------------------------------------------------------- layout
def build():
    img = Img()
    # Masthead
    img.rect(0, 0, W, 66, BG2)
    img.stxtc(0, 6, W, "THE WORLD TODAY", FG, adv=27, h=36, t=3)
    img.txtc(0, 48, W, "FRIDAY 20 NOVEMBER 2026  -  %d STORIES  -  6 CONTINENTS" % TOTAL, GOLD)
    img.hline(0, 66, W, GOLD, thick=2)
    # Timeline strip
    img.rect(0, 68, W, 28, PANEL)
    img.txt(10, 77, "THE DAY IN ORDER  >  AKVAN LANDFALL 02:00 UTC  >  KYIV BARRAGE OVERNIGHT  >  MYANMAR CALLS ICJ UNFAIR  >  YOUTH STRIKE 25 NATIONS  >  MONGOLIA VOTE", DIM)
    img.hline(0, 96, W, EDGE, thick=1)

    # Main cards: 7 x 2
    cw, ch, gap = 138, 208, 6
    for idx, st in enumerate(STORIES):
        n, region, head, body, lon, lat, kind = st
        col, row = idx % 7, idx // 7
        x = 8 + col * (cw + gap)
        y = 102 + row * (ch + gap)
        img.rect(x, y, cw, ch, PANEL)
        img.rect(x, y, cw, 2, GOLD if idx % 2 == 0 else SKY)
        img.txt(x + 6, y + 7, region, SKY)
        img.disc(x + cw - 12, y + 12, 8, GOLD)
        img.txt(x + cw - 15, y + 9, str(n), BG)
        pic(img, kind, x + 6, y + 24, cw - 12, 52)
        img.hline(x + 6, y + 80, cw - 12, EDGE, thick=1)
        yy = y + 86
        for ln in wrap(head, 21)[:3]:
            img.txt(x + 6, yy, ln, FG)
            yy += 9
        yy = y + 86 + 3 * 9 + 4
        for ln in wrap(body, 21)[:9]:
            img.txt(x + 6, yy, ln, DIM)
            yy += 9

    # World map
    my0, my1 = 530, 672
    img.rect(0, my0, W, my1 - my0, SEAC)
    img.txt(10, my0 + 4, "WORLD MAP - WHERE IT HAPPENED  (NUMBERS = MAIN CARDS 1-14)", FG)
    mx0, mx1 = 8, 1016
    mtop, mbot = my0 + 18, my1 - 4

    def proj(lon, lat):
        px = mx0 + (lon + 180) / 360.0 * (mx1 - mx0)
        py = mtop + (84 - lat) / 142.0 * (mbot - mtop)
        return px, py

    _, eqy = proj(0, 0)
    img.seg(mx0, eqy, mx1, eqy, EDGE, 1)
    img.txt(mx1 - 62, eqy + 2, "EQUATOR", DIM)
    for poly in LAND:
        img.gon([proj(lon, lat) for lon, lat in poly], LANDC)
    for st in STORIES:
        n, region, head, body, lon, lat, kind = st
        px, py = proj(lon, lat)
        ox, oy = PIN_OFF.get(n, (0, -14))
        img.disc(px + ox, py + oy, 7, GOLD)
        img.seg(px, py, px + ox, py + oy, GOLD, 2)
        img.disc(px, py, 2, RED)
        lab = str(n)
        img.txt(px + ox - (3 if len(lab) == 1 else 6), py + oy - 3, lab, BG)

    # Also today
    ay = 678
    img.txt(10, ay, "ALSO TODAY - %d MORE STORIES" % (len(ALSO) + len(SPORT)), GOLD)
    img.hline(0, ay + 12, W, EDGE, thick=1)
    items = ["\u2022 " + s for s in ALSO + SPORT]
    cols = [[], [], []]
    for i, it in enumerate(items):
        cols[i % 3].append(it)
    for ci, colitems in enumerate(cols):
        cx = 8 + ci * 336
        yy = ay + 18
        for it in colitems:
            for ln in wrap(it, 52)[:2]:
                img.txt(cx, yy, ln, FG)
                yy += 8
            yy += 2

    # Footer
    fy = 950
    img.hline(0, fy, W, GOLD, thick=2)
    yy = fy + 6
    for ln in wrap(SOURCES, 165):
        img.txt(8, yy, ln, DIM)
        yy += 9
    img.txt(8, yy + 2, "DATE CHECK - 20 NOV 2026: AKVAN LANDFALL; KYIV BARRAGE; MYANMAR REACTION; MONGOLIA VOTE; YOUTH STRIKE; COP31 DRAFT. 19 NOV ITEMS ARE DATED ON THEIR CARDS.", FG)
    img.txt(8, yy + 12, "ORIGINAL DRAWINGS  -  STDLIB PYTHON, DETERMINISTIC, NO NETWORK  -  2X SUPER-SAMPLED", DIM)
    return img


def main():
    img = build()
    data = img.png()
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if not outdir:
        outdir = "/output" if os.path.isdir("/output") else "out"
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, "entry.png")
    with open(out, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes, %d stories)" % (out, len(data), TOTAL))


if __name__ == "__main__":
    main()
