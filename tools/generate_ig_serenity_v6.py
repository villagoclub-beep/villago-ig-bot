#!/usr/bin/env python3
"""
Villa Serenity — VillaGO IG Carousel v6
Square 1080x1080 · Left linen panel (38%) + Right 2 stacked landscape photos (62%)
"""

import json, urllib.request, math
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent.parent / "outputs" / "ig_daily" / "serenity_v6"
OUT.mkdir(parents=True, exist_ok=True)

BASE    = "https://warmplus.club"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://warmphuket.com/"}

SZ  = 1080           # square
GAP = 2              # gap between two right photos (thin gold line)
LW  = int(SZ * 0.38) # left panel width
RW  = SZ - LW        # right photos width
PH  = (SZ - GAP) // 2 # each photo height

# ── Palette ───────────────────────────────────────────────────────────
LINEN  = (240, 234, 222)
PARCH  = (220, 212, 198)
SAND   = (188, 172, 150)
STONE  = (128, 114,  96)
CHAR   = (24,  18,  12)
INK    = (42,  34,  22)
GOLD   = (166, 128,  60)
WHITE  = (255, 255, 255)

PHOTOS = {
    # card 1
    "c1_top":  27,   # night exterior
    "c1_bot":   1,   # infinity pool ocean
    # card 2
    "c2_top":   1,   # pool panorama
    "c2_bot":  41,   # aerial pool
    # card 3
    "c3_top":  42,   # living glass + ocean
    "c3_bot":  45,   # treehouse dining
    # card 4
    "c4_top":  37,   # bedroom palm ocean
    "c4_bot":   3,   # bedroom swan ocean
    # card 5
    "c5_top":  24,   # floating breakfast
    "c5_bot":  38,   # kayak in pool
}

# ── Fonts ─────────────────────────────────────────────────────────────
def serif(sz):
    for p in ["/System/Library/Fonts/Supplemental/Georgia.ttf",
              "/Library/Fonts/Georgia.ttf"]:
        try: return ImageFont.truetype(p, sz)
        except: pass
    return ImageFont.load_default()

def sans(sz, bold=False):
    for p, i in [("/System/Library/Fonts/Helvetica.ttc", 1 if bold else 0),
                 ("/System/Library/Fonts/PingFang.ttc",  1 if bold else 0)]:
        try: return ImageFont.truetype(p, sz, index=i)
        except: pass
    return ImageFont.load_default()

def sans_cjk(sz, bold=False):
    for p, i in [("/Library/Fonts/Arial Unicode.ttf", 0),
                 ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0),
                 ("/System/Library/Fonts/STHeiti Light.ttc", 0),
                 ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
                 ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 0)]:
        try: return ImageFont.truetype(p, sz, index=i)
        except: pass
    return ImageFont.load_default()

def has_cjk(text):
    return any('一' <= c <= '鿿' for c in text)

# ── Image ─────────────────────────────────────────────────────────────
def dl(path):
    req = urllib.request.Request(BASE + path, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return Image.open(BytesIO(r.read())).convert("RGB")

def fit(img, w, h):
    r = max(w / img.width, h / img.height)
    nw, nh = int(img.width * r), int(img.height * r)
    img = img.resize((nw, nh), Image.LANCZOS)
    x, y = (nw - w) // 2, (nh - h) // 2
    return img.crop((x, y, x + w, y + h))

# ── Icons (minimal line-draw) ─────────────────────────────────────────
def icon_bed(d, x, y, s, c):
    lw = 2
    d.rectangle([x, y+s//2, x+s, y+s], outline=(*c,210), width=lw)
    for ox in [3, s//2+2]:
        d.rectangle([x+ox, y+s//2-7, x+ox+s//2-6, y+s//2], outline=(*c,190), width=lw)

def icon_pool(d, x, y, s, c):
    for row in range(3):
        ry = y + row * (s // 3)
        pts = [(x + i*s//8, ry + int(math.sin(i*math.pi/4)*4)) for i in range(9)]
        for i in range(len(pts)-1):
            d.line([pts[i], pts[i+1]], fill=(*c,200), width=2)

def icon_person(d, x, y, s, c):
    r = s//5; cx = x+s//2
    d.ellipse([cx-r, y, cx+r, y+r*2], outline=(*c,210), width=2)
    d.line([(cx, y+r*2),(cx, y+s-4)], fill=(*c,190), width=2)
    d.line([(x+4, y+s//2),(x+s-4, y+s//2)], fill=(*c,190), width=2)
    d.line([(cx, y+s-4),(x+4, y+s+6)], fill=(*c,180), width=2)
    d.line([(cx, y+s-4),(x+s-4, y+s+6)], fill=(*c,180), width=2)

def icon_area(d, x, y, s, c):
    m, lw, a = 5, 2, 7
    d.rectangle([x+m, y+m, x+s-m, y+s-m], outline=(*c,210), width=lw)
    for ax, ay, dx, dy in [(x+m,y+m,-1,-1),(x+s-m,y+m,1,-1),
                            (x+m,y+s-m,-1,1),(x+s-m,y+s-m,1,1)]:
        d.line([(ax,ay),(ax+dx*a,ay)], fill=(*c,195), width=lw)
        d.line([(ax,ay),(ax,ay+dy*a)], fill=(*c,195), width=lw)

def icon_chef(d, x, y, s, c):
    cx = x+s//2
    d.rectangle([x+4, y+s*2//3, x+s-4, y+s], outline=(*c,200), width=2)
    d.ellipse([cx-s//3, y+2, cx+s//3, y+s//2+4], outline=(*c,195), width=2)

def icon_star(d, x, y, s, c):
    cx, cy = x+s//2, y+s//2
    r1, r2 = s//2-2, s//4
    pts = [(cx+( r1 if i%2==0 else r2)*math.cos(math.pi*i/5-math.pi/2),
            cy+( r1 if i%2==0 else r2)*math.sin(math.pi*i/5-math.pi/2))
           for i in range(10)]
    for i in range(len(pts)):
        d.line([pts[i], pts[(i+1)%len(pts)]], fill=(*c,200), width=2)

ICONS = {"bed":icon_bed,"pool":icon_pool,"person":icon_person,
         "area":icon_area,"chef":icon_chef,"star":icon_star}

# ── Gradient overlay on photo ─────────────────────────────────────────
def grad_bottom(img, frac=0.35, strength=160):
    w, h = img.size
    gh = int(h * frac)
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    for i in range(gh):
        a = int(strength * (i / gh) ** 1.8)
        dr.line([(0, h - gh + i), (w, h - gh + i)], fill=(8, 6, 4, a))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

# ── Photo caption strip ───────────────────────────────────────────────
def photo_caption(photo, label):
    """Burn a small caption label into bottom-left of photo"""
    p = photo.copy()
    p = grad_bottom(p, frac=0.28, strength=140)
    d = ImageDraw.Draw(p)
    d.text((18, p.height - 36), label.upper(),
           font=sans(15, bold=True), fill=(*WHITE, 190))
    return p

# ── Canvas builder ────────────────────────────────────────────────────
def make_canvas(top_img, bot_img, card_num=1,
                top_label="", bot_label=""):
    top = photo_caption(fit(top_img, RW, PH), top_label)
    bot = photo_caption(fit(bot_img, RW, PH), bot_label)

    c = Image.new("RGB", (SZ, SZ), LINEN)
    c.paste(top, (LW, 0))
    c.paste(bot, (LW, PH + GAP))

    d = ImageDraw.Draw(c)

    # Thin gold divider between photos
    d.rectangle([LW, PH, SZ, PH + GAP], fill=GOLD)

    # 4px gold left-edge accent bar
    d.rectangle([0, 0, 4, SZ], fill=GOLD)

    # Horizontal gold rule at very top
    d.rectangle([0, 0, SZ, 3], fill=GOLD)

    # Card number — top-right corner of photo area
    num_txt = f"0{card_num} / 05"
    d.text((LW + 16, 18), num_txt,
           font=sans(16, bold=True), fill=(*WHITE, 160))

    return c, d

def draw_panel(d, title_lines, section_label=None,
               specs=None, body_lines=None):
    """Draw content in left linen panel — vertically distributed"""
    M        = 44   # +4px gold bar + breathing room
    FOOT_H   = 50   # reserved for VillaGO.net footer
    TOP_PAD  = 36
    USABLE   = SZ - TOP_PAD - FOOT_H

    # ── Measure each block height ──────────────────────────────────────
    BRAND_H   = 30
    LABEL_H   = 28 if section_label else 0
    TITLE_H   = len(title_lines) * 96
    RULE1_H   = 12
    SPEC_H    = (len(specs) * 90) if specs else 0
    RULE2_H   = 12 if specs else 0
    BODY_H    = (len(body_lines) * 46) if body_lines else 0

    content_h = BRAND_H + LABEL_H + TITLE_H + RULE1_H + SPEC_H + RULE2_H + BODY_H
    slack     = max(0, USABLE - content_h)

    # Distribute slack into N gaps between blocks
    n_gaps = sum([1,                        # after brand
                  1 if section_label else 0,# after label
                  1,                        # after title (before rule)
                  1,                        # after rule1
                  1 if specs else 0,        # after specs (before rule2)
                  1 if body_lines else 0,   # after rule2
                  ])
    gap = slack // max(n_gaps, 1)

    cy = TOP_PAD

    # Brand
    d.text((M, cy), "VillaGO", font=sans(22, bold=True), fill=(*STONE, 210))
    cy += BRAND_H + gap

    # Section label
    if section_label:
        d.text((M, cy), section_label.upper(), font=sans(18), fill=(*GOLD, 220))
        cy += LABEL_H + gap

    # Title
    for line in title_lines:
        d.text((M, cy), line, font=serif(88), fill=CHAR)
        cy += 96
    cy += gap

    # Rule 1
    d.line([(M, cy), (LW-M, cy)], fill=(*SAND, 180), width=1)
    cy += RULE1_H + gap

    # Specs
    if specs:
        for icon_key, val, lbl in specs:
            ICONS[icon_key](d, M, cy + 6, 34, STONE)
            d.text((M + 52, cy),      val, font=sans(32, bold=True), fill=CHAR)
            d.text((M + 52, cy + 38), lbl, font=sans(20),            fill=STONE)
            cy += 90
        cy += gap
        d.line([(M, cy), (LW-M, cy)], fill=(*SAND, 100), width=1)
        cy += RULE2_H + gap

    # Body
    if body_lines:
        for line in body_lines:
            f = sans_cjk(22) if has_cjk(line) else sans(22)
            d.text((M, cy), line, font=f, fill=INK)
            cy += 46

    # Footer pinned to bottom
    d.text((M, SZ - FOOT_H + 10), "VillaGO.net",
           font=sans(20, bold=True), fill=(*STONE, 170))

# ══════════════════════════════════════════════════════════════════════
def card1(P):
    c, d = make_canvas(dl(P[PHOTOS["c1_top"]]), dl(P[PHOTOS["c1_bot"]]),
                       card_num=1,
                       top_label="Night Exterior",
                       bot_label="Infinity Pool")
    draw_panel(d,
        title_lines = ["Villa", "Sere-", "nity"],
        specs       = [
            ("bed",    "6",        "Bedrooms"),
            ("area",   "1,000 m²", "Villa Area"),
            ("person", "12",       "Guests"),
            ("pool",   "30 m",     "Lap Pool"),
        ],
        body_lines  = ["Naithon · Phuket"],
    )
    c.save(OUT/"01_hero.jpg", "JPEG", quality=96)
    print("✅  01_hero.jpg")

def card2(P):
    c, d = make_canvas(dl(P[PHOTOS["c2_top"]]), dl(P[PHOTOS["c2_bot"]]),
                       card_num=2,
                       top_label="Infinity Pool · Open Ocean",
                       bot_label="Aerial View")
    draw_panel(d,
        section_label = "Pool & Garden",
        title_lines   = ["Private", "Pool"],
        specs         = [
            ("pool",   "30 m",    "Lap Pool"),
            ("area",   "Ocean",   "Facing"),
            ("person", "12",      "Guests"),
        ],
        body_lines    = [
            "30 m infinity pool",
            "Terrace loungers",
            "Garden & sea breeze",
            "Sunrise to sunset",
        ],
    )
    c.save(OUT/"02_pool.jpg", "JPEG", quality=96)
    print("✅  02_pool.jpg")

def card3(P):
    c, d = make_canvas(dl(P[PHOTOS["c3_top"]]), dl(P[PHOTOS["c3_bot"]]),
                       card_num=3,
                       top_label="Living Room · Ocean Wall",
                       bot_label="Treehouse Dining")
    draw_panel(d,
        section_label = "Living & Dining",
        title_lines   = ["Open", "to the", "Ocean"],
        body_lines    = [
            "Cathedral ceilings",
            "Floor-to-ceiling glass",
            "Treehouse dining sala",
            "Al fresco terrace",
            "Private dining room",
        ],
    )
    c.save(OUT/"03_living.jpg", "JPEG", quality=96)
    print("✅  03_living.jpg")

def card4(P):
    c, d = make_canvas(dl(P[PHOTOS["c4_top"]]), dl(P[PHOTOS["c4_bot"]]),
                       card_num=4,
                       top_label="Master Suite · Palm Ocean",
                       bot_label="Ocean Suite")
    draw_panel(d,
        section_label = "Bedrooms",
        title_lines   = ["The", "Suites"],
        specs         = [
            ("bed",    "6",       "En-suite Rooms"),
            ("pool",   "Pool",    "Direct Access"),
            ("person", "12",      "Guests"),
            ("area",   "Ocean",   "View All Rooms"),
        ],
    )
    c.save(OUT/"04_bedrooms.jpg", "JPEG", quality=96)
    print("✅  04_bedrooms.jpg")

def card5(P):
    c, d = make_canvas(dl(P[PHOTOS["c5_top"]]), dl(P[PHOTOS["c5_bot"]]),
                       card_num=5,
                       top_label="Floating Breakfast",
                       bot_label="Pool Kayaking")
    draw_panel(d,
        section_label = "Signature Experiences",
        title_lines   = ["Looked", "After"],
        body_lines    = [
            "Private chef · daily menu",
            "Floating pool breakfast",
            "Dedicated full-time maid",
            "Cinema · Mahjong room",
            "Airport transfer incl.",
            "EN · 中文 · RU",
        ],
    )
    c.save(OUT/"05_services.jpg", "JPEG", quality=96)
    print("✅  05_services.jpg")

# ══════════════════════════════════════════════════════════════════════
def main():
    print("📡  Fetching photos...")
    req = urllib.request.Request(
        BASE+"/api/properties/villas?page=1&limit=100&lang=en", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    villa  = next(v for v in data["data"] if v["property_number"] == "V4")
    photos = villa["photos"]
    print(f"   {len(photos)} photos\n")

    card1(photos); card2(photos); card3(photos)
    card4(photos); card5(photos)
    print(f"\n📁  → {OUT}")

if __name__ == "__main__":
    main()
