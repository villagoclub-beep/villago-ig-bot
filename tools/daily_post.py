#!/usr/bin/env python3
"""
VillaGO Daily Instagram Post
Runs on GitHub Actions (Ubuntu) — no local dependencies needed.
Env vars required: BUFFER_TOKEN
"""

import json, math, os, sys, tempfile, urllib.request
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── Config ────────────────────────────────────────────────────────────
BUFFER_TOKEN = os.environ["BUFFER_TOKEN"]
CHANNEL_ID   = "6a3a74335ab6d2f10661bfa6"   # VillaGO Instagram

BASE_API  = "https://warmplus.club"
HEADERS   = {"User-Agent": "Mozilla/5.0", "Referer": "https://warmphuket.com/"}

SZ  = 1080
GAP = 2
LW  = int(SZ * 0.38)
RW  = SZ - LW
PH  = (SZ - GAP) // 2

# ── Palette ───────────────────────────────────────────────────────────
LINEN = (240, 234, 222)
SAND  = (188, 172, 150)
STONE = (128, 114,  96)
CHAR  = ( 24,  18,  12)
INK   = ( 42,  34,  22)
GOLD  = (166, 128,  60)
WHITE = (255, 255, 255)

# ── Photo index per villa ─────────────────────────────────────────────
VILLAS = {
    "V4": {
        "name": "Villa Serenity",
        "specs": [
            ("bed",    "6",        "Bedrooms"),
            ("area",   "1,000 m²", "Villa Area"),
            ("person", "12",       "Guests"),
            ("pool",   "30 m",     "Lap Pool"),
        ],
        "cards": [
            # (left_title, section_label, body_lines, top_idx, bot_idx, top_lbl, bot_lbl)
            (["Villa","Sere-","nity"], None,
             ["Naithon · Phuket"],
             27, 1, "Night Exterior", "Infinity Pool"),
            (["Private","Pool"], "Pool & Garden",
             ["30 m infinity pool","Terrace loungers","Garden & sea breeze","Sunrise to sunset"],
             1, 41, "Infinity Pool · Open Ocean", "Aerial View"),
            (["Open","to the","Ocean"], "Living & Dining",
             ["Cathedral ceilings","Floor-to-ceiling glass","Treehouse dining sala","Al fresco terrace","Private dining room"],
             42, 45, "Living Room · Ocean Wall", "Treehouse Dining"),
            (["The","Suites"], "Bedrooms",
             ["Every room faces sea or pool"],
             37, 3, "Master Suite · Palm Ocean", "Ocean Suite"),
            (["Looked","After"], "Signature Experiences",
             ["Private chef · daily menu","Floating pool breakfast","Dedicated full-time maid","Cinema · Mahjong room","Airport transfer incl.","EN · 中文 · RU"],
             24, 38, "Floating Breakfast", "Pool Kayaking"),
        ],
        "caption": """\
Villa Serenity — Naithon, Phuket 🌊

A private 1,000 m² estate perched above the Andaman Sea.

✦  30 m infinity pool · open ocean horizon
✦  6 en-suite bedrooms · up to 12 guests
✦  Floating breakfast served in-pool daily
✦  Private on-site chef · custom menus
✦  Dedicated full-time maid
✦  Treehouse dining · cinema · mahjong room
✦  Airport transfer included
✦  Trilingual concierge EN · 中文 · RU

Every room faces the sea or the pool.
Enquire via DM or villago.net

—

#VillaSerenity #VillaGO #PhuketVilla
#LuxuryVilla #PrivateVilla #InfinityPool
#FloatingBreakfast #PhuketLuxury #Naithon
#ThailandTravel #TropicalEscape #VillaRental"""
    },
    "V5": {
        "name": "Villa Elegance",
        "specs": [
            ("bed",    "5",        "Bedrooms"),
            ("area",   "1,500 m²", "Villa Area"),
            ("person", "10",       "Guests"),
            ("pool",   "Private",  "Pool"),
        ],
        "cards": [
            (["Villa","Eleg-","ance"], None,
             ["Naithon · Phuket"],
             20, 23, "Villa Exterior · Pool", "Pool Side · Ocean"),
            (["Private","Pool"], "Pool & Garden",
             ["Ocean-front terrace","Tropical garden","Sun loungers"],
             4, 27, "Infinity Pool · Open Ocean", "Garden · Sea View"),
            (["Open","Living"], "Living & Dining",
             ["Grand double-height hall","Floor-to-ceiling glass","Poolside terrace dining","Indoor-outdoor flow","Panoramic ocean view"],
             13, 14, "Grand Living Hall", "Terrace Dining · Pool · Ocean"),
            (["The","Suites"], "Bedrooms",
             ["Every suite faces sea or pool"],
             6, 15, "Master Suite · Sea View", "Bedroom · Pool · Ocean"),
            (["Looked","After"], "Signature Experiences",
             ["Private chef · daily menu","Floating pool breakfast","Dedicated full-time maid","Pool activities","Airport transfer incl.","EN · 中文 · RU"],
             1, 3, "Floating Breakfast", "Service Team"),
        ],
        "caption": """\
Villa Elegance — Naithon, Phuket 🌊

A private 1,500 m² oceanfront estate for up to 10 guests.

✦  Private infinity pool · open ocean panorama
✦  5 en-suite bedrooms · sea & pool views
✦  Grand double-height living hall
✦  Floating breakfast served in-pool daily
✦  Private on-site chef · custom menus
✦  Dedicated full-time maid
✦  Poolside terrace dining · ocean breeze
✦  Airport transfer included
✦  Trilingual concierge EN · 中文 · RU

Enquire via DM or villago.net

—

#VillaElegance #VillaGO #PhuketVilla
#LuxuryVilla #PrivateVilla #InfinityPool
#FloatingBreakfast #PhuketLuxury #Naithon
#ThailandTravel #TropicalEscape #VillaRental"""
    },
}

VILLA_ROTATION = ["V4", "V5"]

# ── Fonts (macOS + Linux fallbacks) ───────────────────────────────────
def serif(sz):
    for p in [
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/Library/Fonts/Georgia.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    ]:
        try: return ImageFont.truetype(p, sz)
        except: pass
    return ImageFont.load_default()

def sans(sz, bold=False):
    for p, i in [
        ("/System/Library/Fonts/Helvetica.ttc",  1 if bold else 0),
        ("/System/Library/Fonts/PingFang.ttc",   1 if bold else 0),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",    0) if bold else
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 0),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0) if bold else
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",      0),
    ]:
        try: return ImageFont.truetype(p, sz)
        except: pass
    return ImageFont.load_default()

def sans_cjk(sz, bold=False):
    for p, i in [
        ("/Library/Fonts/Arial Unicode.ttf", 0),
        ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0),
        ("/System/Library/Fonts/STHeiti Light.ttc", 0),
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
        ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 0),
    ]:
        try: return ImageFont.truetype(p, sz, index=i)
        except: pass
    return ImageFont.load_default()

def has_cjk(text):
    return any('一' <= c <= '鿿' for c in text)

# ── Icons ─────────────────────────────────────────────────────────────
def icon_bed(d, x, y, s, c):
    d.rectangle([x, y+s//2, x+s, y+s], outline=(*c,210), width=2)
    for ox in [3, s//2+2]:
        d.rectangle([x+ox, y+s//2-7, x+ox+s//2-6, y+s//2], outline=(*c,190), width=2)

def icon_pool(d, x, y, s, c):
    for row in range(3):
        ry = y + row*(s//3)
        pts = [(x+i*s//8, ry+int(math.sin(i*math.pi/4)*4)) for i in range(9)]
        for i in range(len(pts)-1):
            d.line([pts[i],pts[i+1]], fill=(*c,200), width=2)

def icon_person(d, x, y, s, c):
    r=s//5; cx=x+s//2
    d.ellipse([cx-r,y,cx+r,y+r*2], outline=(*c,210), width=2)
    d.line([(cx,y+r*2),(cx,y+s-4)], fill=(*c,190), width=2)
    d.line([(x+4,y+s//2),(x+s-4,y+s//2)], fill=(*c,190), width=2)
    d.line([(cx,y+s-4),(x+4,y+s+6)], fill=(*c,180), width=2)
    d.line([(cx,y+s-4),(x+s-4,y+s+6)], fill=(*c,180), width=2)

def icon_area(d, x, y, s, c):
    m,a=5,7
    d.rectangle([x+m,y+m,x+s-m,y+s-m], outline=(*c,210), width=2)
    for ax,ay,dx,dy in [(x+m,y+m,-1,-1),(x+s-m,y+m,1,-1),(x+m,y+s-m,-1,1),(x+s-m,y+s-m,1,1)]:
        d.line([(ax,ay),(ax+dx*a,ay)], fill=(*c,195), width=2)
        d.line([(ax,ay),(ax,ay+dy*a)], fill=(*c,195), width=2)

ICONS = {"bed":icon_bed,"pool":icon_pool,"person":icon_person,"area":icon_area}

# ── Image helpers ─────────────────────────────────────────────────────
def dl(path):
    req = urllib.request.Request(BASE_API+path, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return Image.open(BytesIO(r.read())).convert("RGB")

def fit(img, w, h):
    r = max(w/img.width, h/img.height)
    nw,nh = int(img.width*r), int(img.height*r)
    img = img.resize((nw,nh), Image.LANCZOS)
    x,y = (nw-w)//2, (nh-h)//2
    return img.crop((x,y,x+w,y+h))

def grad_bottom(img, frac=0.28, strength=140):
    w,h = img.size
    gh = int(h*frac)
    ov = Image.new("RGBA",(w,h),(0,0,0,0))
    dr = ImageDraw.Draw(ov)
    for i in range(gh):
        a = int(strength*(i/gh)**1.8)
        dr.line([(0,h-gh+i),(w,h-gh+i)], fill=(8,6,4,a))
    return Image.alpha_composite(img.convert("RGBA"),ov).convert("RGB")

def photo_caption(photo, label):
    p = grad_bottom(fit(photo, RW, PH))
    d = ImageDraw.Draw(p)
    d.text((18, p.height-36), label.upper(),
           font=sans(15,bold=True), fill=(*WHITE,190))
    return p

# ── Canvas ────────────────────────────────────────────────────────────
def make_canvas(top_img, bot_img, card_num, top_label, bot_label):
    c = Image.new("RGB",(SZ,SZ),LINEN)
    c.paste(photo_caption(top_img, top_label), (LW, 0))
    c.paste(photo_caption(bot_img, bot_label), (LW, PH+GAP))
    d = ImageDraw.Draw(c)
    d.rectangle([LW, PH, SZ, PH+GAP], fill=GOLD)
    d.rectangle([0,0,4,SZ], fill=GOLD)
    d.rectangle([0,0,SZ,3], fill=GOLD)
    d.text((LW+16,18), f"0{card_num} / 05",
           font=sans(16,bold=True), fill=(*WHITE,160))
    return c, d

def draw_panel(d, title_lines, section_label=None, specs=None, body_lines=None):
    M=44; FOOT_H=50; TOP_PAD=36; USABLE=SZ-TOP_PAD-FOOT_H
    BRAND_H=30; LABEL_H=28 if section_label else 0
    TITLE_H=len(title_lines)*96; RULE1_H=12
    SPEC_H=(len(specs)*90) if specs else 0; RULE2_H=12 if specs else 0
    BODY_H=(len(body_lines)*46) if body_lines else 0
    content_h=BRAND_H+LABEL_H+TITLE_H+RULE1_H+SPEC_H+RULE2_H+BODY_H
    slack=max(0,USABLE-content_h)
    n_gaps=sum([1,1 if section_label else 0,1,1,1 if specs else 0,1 if body_lines else 0])
    gap=slack//max(n_gaps,1); cy=TOP_PAD

    d.text((M,cy),"VillaGO",font=sans(22,bold=True),fill=(*STONE,210)); cy+=BRAND_H+gap
    if section_label:
        d.text((M,cy),section_label.upper(),font=sans(18),fill=(*GOLD,220)); cy+=LABEL_H+gap
    for line in title_lines:
        d.text((M,cy),line,font=serif(88),fill=CHAR); cy+=96
    cy+=gap
    d.line([(M,cy),(LW-M,cy)],fill=(*SAND,180),width=1); cy+=RULE1_H+gap
    if specs:
        for icon_key,val,lbl in specs:
            ICONS[icon_key](d,M,cy+6,34,STONE)
            d.text((M+52,cy),val,font=sans(32,bold=True),fill=CHAR)
            d.text((M+52,cy+38),lbl,font=sans(20),fill=STONE)
            cy+=90
        cy+=gap
        d.line([(M,cy),(LW-M,cy)],fill=(*SAND,100),width=1); cy+=RULE2_H+gap
    if body_lines:
        for line in body_lines:
            f=sans_cjk(22) if has_cjk(line) else sans(22)
            d.text((M,cy),line,font=f,fill=INK); cy+=46
    d.text((M,SZ-FOOT_H+10),"VillaGO.net",font=sans(20,bold=True),fill=(*STONE,170))

# ── Generate cards ────────────────────────────────────────────────────
def generate_cards(villa_id, photos, outdir):
    cfg = VILLAS[villa_id]
    paths = []
    for i, (title, section, body, top_idx, bot_idx, top_lbl, bot_lbl) in enumerate(cfg["cards"], 1):
        c, d = make_canvas(dl(photos[top_idx]), dl(photos[bot_idx]),
                           i, top_lbl, bot_lbl)
        # Only card 1 gets specs
        draw_panel(d, title, section,
                   specs=cfg["specs"] if i==1 else None,
                   body_lines=body)
        p = outdir / f"{i:02d}.jpg"
        c.save(p, "JPEG", quality=96)
        print(f"  ✅  {p.name}")
        paths.append(p)
    return paths

# ── Upload image to GitHub Release ───────────────────────────────────
GH_REPO  = os.environ.get("GITHUB_REPOSITORY", "villagoclub-beep/villago-ig-bot")
GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")

def get_or_create_release(tag="media"):
    """Get existing media release or create one."""
    headers = {"Authorization": f"token {GH_TOKEN}",
               "Content-Type": "application/json"}
    # Try get
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GH_REPO}/releases/tags/{tag}",
        headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())["id"]
    except urllib.error.HTTPError:
        pass
    # Create
    body = json.dumps({"tag_name": tag, "name": "Media storage",
                       "body": "Auto-generated image storage.", "prerelease": True}).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GH_REPO}/releases",
        data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())["id"]

def upload(path):
    import datetime, mimetypes
    release_id = get_or_create_release()
    # Unique filename to avoid collisions across days
    stamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    fname = f"{stamp}_{path.name}"
    data  = path.read_bytes()
    req = urllib.request.Request(
        f"https://uploads.github.com/repos/{GH_REPO}/releases/{release_id}/assets?name={fname}",
        data=data,
        headers={
            "Authorization": f"token {GH_TOKEN}",
            "Content-Type": "image/jpeg",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        asset = json.loads(r.read())
    url = asset["browser_download_url"]
    print(f"  📤  {path.name} → {url}")
    return url

# ── Post to Buffer ────────────────────────────────────────────────────
def post_to_buffer(caption, img_urls):
    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess { post { id status dueAt } }
        ... on NotFoundError     { message }
        ... on UnauthorizedError { message }
        ... on UnexpectedError   { message }
        ... on RestProxyError    { message code }
        ... on LimitReachedError { message }
        ... on InvalidInputError { message }
      }
    }
    """
    variables = {
        "input": {
            "channelId": CHANNEL_ID,
            "text": caption,
            "schedulingType": "automatic",
            "mode": "addToQueue",
            "assets": [{"image": {"url": u}} for u in img_urls],
            "metadata": {
                "instagram": {"type": "post", "shouldShareToFeed": True}
            }
        }
    }
    body = json.dumps({"query": mutation, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.buffer.com/graphql", data=body,
        headers={"Authorization": f"Bearer {BUFFER_TOKEN}",
                 "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

# ── Main ──────────────────────────────────────────────────────────────
def main():
    import datetime
    villa_id = os.environ.get("VILLA_ID", "")
    if not villa_id:
        day = datetime.datetime.utcnow().timetuple().tm_yday
        villa_id = VILLA_ROTATION[day % len(VILLA_ROTATION)]
    print(f"\n🏡  Generating {VILLAS[villa_id]['name']} ({villa_id})...")

    # Fetch photos
    print("📡  Fetching photo list...")
    req = urllib.request.Request(
        BASE_API+"/api/properties/villas?page=1&limit=100&lang=en", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    villa  = next(v for v in data["data"] if v["property_number"] == villa_id)
    photos = villa["photos"]
    print(f"   {len(photos)} photos available")

    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)

        # Generate images
        print("\n🎨  Generating cards...")
        paths = generate_cards(villa_id, photos, outdir)

        # Upload
        print("\n📤  Uploading images...")
        urls = [upload(p) for p in paths]

        # Post
        print("\n📮  Posting to Buffer...")
        result = post_to_buffer(VILLAS[villa_id]["caption"], urls)
        print(f"   {json.dumps(result, indent=2)}")

    post = result.get("data",{}).get("createPost",{})
    if "post" in post:
        print(f"\n✅  Queued! ID={post['post']['id']} due={post['post']['dueAt']}")
    else:
        print(f"\n❌  Error: {post}")
        sys.exit(1)

if __name__ == "__main__":
    main()
