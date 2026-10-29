"""看板の提案（1階入口の光る置き看板に差し込むポスター・10案）のイメージ画像を作る。

  python -I -X utf8 tools/make_sign_images.py [01,05,00,stand …]   … 番号を渡すと、その画像だけ作り直す

スタンドは決まっている: モノタロウの LEDパネルA型スタンド 片面（A1）。幅640×奥行490×高さ1185mm、ボード面 640×884mm。
その中に差し込むポスター（A1・594×841mm）を10案描く。
1案につき3枚: 置いたイメージ（夜の入口・拡大つき）、デザイン（ポスターの全体）、一覧用の小さい画像。
ほかに「今のようす」と「スタンドの大きさ」。

文字や値段は signs.json と site.json から読む（値段の計算は build.py の sign_prices と同じもの）。
値段が決まったら site.json を直して、この画像とページを作り直す。
建物はストリートビューの写真を加工せず、イラストで描き起こす（Google の画像は加工して公開できないため）。
SVG で描き、画面なしの Edge で書き出す。ページ用の小さい WebP と、まとめてダウンロードする ZIP も作る。
"""
import base64
import html
import io
import json
import math
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))
import shoot  # noqa: E402
import build  # noqa: E402  値段の計算（sign_prices・sign_charge）をページと同じにするため

IMG = ROOT / 'docs' / 'assets' / 'img'
OUT = ROOT / 'docs' / 'signs' / 'img'
ZIP = ROOT / 'docs' / 'signs' / 'xiii-sign-posters.zip'
DATA = json.loads((ROOT / 'signs.json').read_text(encoding='utf-8'))
SITE = json.loads((ROOT / 'site.json').read_text(encoding='utf-8'))

LOGO = (IMG / 'logo-x-iii.png').as_uri()
LOGO_W = (IMG / 'logo-x-iii-white.png').as_uri()
BARLOW = (ROOT / 'tools' / 'fonts' / 'Barlow-Regular.ttf').as_uri()

JP = "'Yu Gothic','Meiryo',sans-serif"
JPB = "'Noto Sans JP','Yu Gothic',sans-serif"
MIN = "'Noto Serif JP','Yu Mincho',serif"
SERIF = "'Palatino Linotype','Book Antiqua',Georgia,serif"
NUM = "'Bahnschrift','Barlow',sans-serif"
SCRIPT = "'Segoe Script','Segoe Print',cursive"
HAND = "'Segoe Print','Yu Gothic',cursive"

GOLD, GOLD_L, INK, WHITE = '#d9b66f', '#f4dfa8', '#0c0c0f', '#f6f2ea'

# ---- ポスターに載せる中身（site.json から） ------------------------------------------------
HOURS = f"{SITE['open']}–{int(SITE['close'][:2])}:{SITE['close'][3:]}"   # 19:00–7:00
CLOSED = SITE['closed']
SMOKE = next(c['value'] for c in DATA['contents'] if c['label'] == 'たばこ')
FOOT = f'OPEN {HOURS} ／ {CLOSED} ／ {SMOKE}'
PRICES = {x['id']: x for x in build.sign_prices()}
CHARGE_PER, CHARGE_AMT, _ = build.sign_charge()
CHARGE = f'テーブルチャージ　{CHARGE_PER} {CHARGE_AMT}'
BUDGET = build.raw('budget')[0]
INSTA = SITE['instagram']

# ---- スタンド（mm）。ボード面 640×884 の中に A1 のポスター（594×841）が入る -------------------
PW, PH = 594, 841
STAND_W, STAND_H, STAND_D, BOARD_H = 640, 1185, 490, 884
LIP = 32                               # 表の枠の幅（ポスターのふちに 9〜10mm かかる）

# ---- 建物の絵の座標 --------------------------------------------------------------------
S = 0.07          # 建物の絵の縮尺（1mm = 0.07。1m = 70）
G = 905           # 地面（入口の段の上）の高さ
CX = 1300         # スタンドを置く位置（入口のガラス扉の右）
VB = (430, 160, 1290, 806.25)    # 「今のようす」で切り取る範囲（1600×1000 に拡大）
K = 1600 / VB[2]
PV = (600, 125, 900 * 870 / 1000, 870)   # 置いたイメージの左側（900×1000）に出す範囲
PK = 1000 / 870


def esc(s):
    return html.escape(str(s), quote=True)


def o(x, y):
    """建物の絵の座標を、「今のようす」の画像（1600×1000）の座標にする。"""
    return ((x - VB[0]) * K, (y - VB[1]) * K)


def po(x, y):
    """建物の絵の座標を、置いたイメージの左側（900×1000）の座標にする。"""
    return ((x - PV[0]) * PK, (y - PV[1]) * PK)


def T(x, y, s, size, fill=WHITE, fam=JP, w=700, anchor='middle', ls=0, extra=''):
    # 字間（letter-spacing）は最後の字の後ろにも付くので、その分ずらして真ん中・右端をそろえる。
    if ls and anchor == 'middle':
        x += ls / 2
    elif ls and anchor == 'end':
        x += ls
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" font-weight="{w}" fill="{fill}" '
            f'text-anchor="{anchor}" letter-spacing="{ls}" {extra}>{esc(s)}</text>')


def tw(s, size):
    """文字の幅のおおよそ（点線の長さを決めるのに使う）。"""
    w = 0.0
    for ch in s:
        if ch == ' ':
            w += .3
        elif ord(ch) < 0x300:
            w += .6 if (ch.isupper() or ch.isdigit() or ch == '¥') else .5
        else:
            w += 1.0
    return w * size


def logo(cx, y, w, white=False, extra=''):
    h = w * 234 / 444
    return f'<image href="{LOGO_W if white else LOGO}" x="{cx - w / 2:.1f}" y="{y}" width="{w}" height="{h:.1f}" {extra}/>'


DEFS = f"""<defs>
<style>@font-face{{font-family:'Barlow';src:url('{BARLOW}')}}</style>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#050816"/><stop offset=".55" stop-color="#101839"/><stop offset="1" stop-color="#28214a"/></linearGradient>
<linearGradient id="corner" x1="0" x2="1"><stop offset="0" stop-color="#15326f"/><stop offset=".35" stop-color="#22499f"/><stop offset=".55" stop-color="#2853ad"/><stop offset=".8" stop-color="#1f4494"/><stop offset="1" stop-color="#18367a"/></linearGradient>
<linearGradient id="faceL" x1="0" x2="1"><stop offset="0" stop-color="#10275a"/><stop offset="1" stop-color="#15306c"/></linearGradient>
<linearGradient id="faceR" x1="0" x2="1"><stop offset="0" stop-color="#18367a"/><stop offset=".7" stop-color="#1a3a80"/><stop offset="1" stop-color="#14306c"/></linearGradient>
<linearGradient id="win2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4b3569"/><stop offset="1" stop-color="#271c40"/></linearGradient>
<linearGradient id="win3" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0c2620"/><stop offset=".65" stop-color="#11372d"/><stop offset="1" stop-color="#1e6a4c"/></linearGradient>
<linearGradient id="win4" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0c1222"/><stop offset="1" stop-color="#121a30"/></linearGradient>
<linearGradient id="lobby" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fbfcfd"/><stop offset="1" stop-color="#c3ccd6"/></linearGradient>
<linearGradient id="frost" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f3e6c9" stop-opacity=".55"/><stop offset="1" stop-color="#c9b48d" stop-opacity=".35"/></linearGradient>
<linearGradient id="cyl" x1="0" x2="1"><stop offset="0" stop-color="#2b303d"/><stop offset=".45" stop-color="#4a5163"/><stop offset="1" stop-color="#262a35"/></linearGradient>
<linearGradient id="pole" x1="0" x2="1"><stop offset="0" stop-color="#4c5059"/><stop offset=".5" stop-color="#8d9199"/><stop offset="1" stop-color="#3f434b"/></linearGradient>
<linearGradient id="road" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a2c36"/><stop offset="1" stop-color="#16171e"/></linearGradient>
<linearGradient id="metal" x1="0" x2="1"><stop offset="0" stop-color="#8b929b"/><stop offset=".22" stop-color="#e2e6eb"/><stop offset=".5" stop-color="#c2c7ce"/><stop offset=".8" stop-color="#d9dde2"/><stop offset="1" stop-color="#848a93"/></linearGradient>
<linearGradient id="metalV" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e6e9ed"/><stop offset="1" stop-color="#9aa0a8"/></linearGradient>
<radialGradient id="panelLit" cx=".5" cy=".42" r=".75"><stop offset="0" stop-color="#fff" stop-opacity=".2"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
<radialGradient id="lamp" cx="1" cy=".62" r=".75"><stop offset="0" stop-color="#ffd9a0" stop-opacity=".30"/><stop offset="1" stop-color="#ffd9a0" stop-opacity="0"/></radialGradient>
<radialGradient id="lobbySpill" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#eaf2ff" stop-opacity=".45"/><stop offset="1" stop-color="#eaf2ff" stop-opacity="0"/></radialGradient>
<radialGradient id="spill" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fff0cf" stop-opacity=".75"/><stop offset="1" stop-color="#fff0cf" stop-opacity="0"/></radialGradient>
<radialGradient id="vignette" cx=".5" cy=".5" r=".72"><stop offset=".45" stop-color="#05060c" stop-opacity="0"/><stop offset="1" stop-color="#05060c" stop-opacity=".62"/></radialGradient>
<radialGradient id="bgDesign" cx=".5" cy=".4" r=".8"><stop offset="0" stop-color="#262a33"/><stop offset="1" stop-color="#101217"/></radialGradient>
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#fff" stroke-opacity=".035"/></pattern>
<filter id="halo" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="40"/></filter>
<filter id="neon" x="-60%" y="-60%" width="220%" height="220%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="5" result="a"/><feGaussianBlur stdDeviation="16" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="a"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="5"/></filter>
<filter id="softer" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="14"/></filter>
<filter id="chalk" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="4" result="n"/><feColorMatrix in="n" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 -1.5 1.3" result="m"/><feComposite in="SourceGraphic" in2="m" operator="in"/></filter>
<filter id="dust" x="0" y="0" width="1" height="1"><feTurbulence type="fractalNoise" baseFrequency=".02" numOctaves="3" seed="9"/><feColorMatrix type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .09 0"/></filter>
<filter id="paper" x="0" y="0" width="1" height="1"><feTurbulence type="fractalNoise" baseFrequency=".035" numOctaves="4" seed="3"/><feColorMatrix type="matrix" values="0 0 0 0 .45  0 0 0 0 .33  0 0 0 0 .18  0 0 0 .25 0"/></filter>
<filter id="pop" color-interpolation-filters="sRGB"><feComponentTransfer><feFuncR type="gamma" amplitude="1.04" exponent=".8"/><feFuncG type="gamma" amplitude="1.04" exponent=".8"/><feFuncB type="gamma" amplitude="1.04" exponent=".8"/></feComponentTransfer><feColorMatrix type="saturate" values="1.12"/></filter>
<filter id="gilt" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values=".33 .62 .12 0 .02  .27 .52 .1 0 0  .14 .27 .05 0 0  0 0 0 1 0"/></filter>
<filter id="ink" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="0 0 0 0 .125  0 0 0 0 .25  0 0 0 0 .185  0 0 0 1 0"/></filter>
<filter id="tshadow" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur in="SourceAlpha" stdDeviation="3"/><feOffset dy="1.5"/><feComponentTransfer><feFuncA type="linear" slope=".9"/></feComponentTransfer><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>"""


# ---- ポスターの部品（mm。左上が 0,0、594×841） ----------------------------------------------
def gold_grad(gid):
    return (f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fbeec4"/>'
            f'<stop offset=".45" stop-color="#e2c27e"/><stop offset="1" stop-color="#a9823e"/></linearGradient>')


def shade(gid, a, b, vertical=True):
    """黒のぼかし（a の不透明度から b の不透明度へ）。"""
    xy = 'x1="0" y1="0" x2="0" y2="1"' if vertical else 'x1="0" y1="0" x2="1" y2="0"'
    return (f'<linearGradient id="{gid}" {xy}><stop offset="0" stop-color="#000" stop-opacity="{a}"/>'
            f'<stop offset="1" stop-color="#000" stop-opacity="{b}"/></linearGradient>')


def _photo_info():
    names = {'counter-dark': 'counter-dark-2400', 'backbar': 'backbar-2400', 'counter-wide': 'counter-wide-1108',
             'neon-counter': 'neon-counter-1477', 'tables': 'tables-1108', 'darts': 'darts-1108'}
    out = {}
    for k, f in names.items():
        p = IMG / f'{f}.webp'
        with Image.open(p) as im:
            out[k] = (p.as_uri(), im.size[0], im.size[1])
    return out


PHOTOS = _photo_info()


def ph(name, x, y, w, h, cid, fx=.5, fy=.5, zoom=1.0, rx=0, clip=None, pop=True):
    """写真を枠いっぱいに切り抜いて置く。(fx, fy) は枠の真ん中に来る写真の位置（0〜1）。clip は枠の形（パスの d）。"""
    uri, iw, ih = PHOTOS[name]
    k = max(w / iw, h / ih) * zoom
    dw, dh = iw * k, ih * k
    ix = min(x, max(x + w - dw, x + w / 2 - fx * dw))
    iy = min(y, max(y + h - dh, y + h / 2 - fy * dh))
    shape = f'<path d="{clip}"/>' if clip else f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/>'
    f = ' filter="url(#pop)"' if pop else ''
    return (f'<clipPath id="{cid}">{shape}</clipPath><g clip-path="url(#{cid})">'
            f'<image href="{uri}" x="{ix:.2f}" y="{iy:.2f}" width="{dw:.2f}" height="{dh:.2f}" preserveAspectRatio="none"{f}/></g>')


def rows(*ids):
    return [(PRICES[i]['label'], PRICES[i]['value']) for i in ids]


def plist(x, y, w, items, size, lab, val, lead=None, lh=None, fam=JPB, wl=500, wv=700, extra=''):
    """値段の一覧（名前は左、値段は右。あいだを点線でつなぐ）。"""
    lh = lh or size * 1.55
    s = ''
    for i, (k, v) in enumerate(items):
        yy = y + i * lh
        s += T(x, yy, k, size, lab, fam, wl, 'start', extra=extra)
        s += T(x + w, yy, v, size, val, fam, wv, 'end', extra=extra)
        if lead:
            a, b = x + tw(k, size) + size * .45, x + w - tw(v, size) - size * .45
            if b - a > size:
                s += (f'<line x1="{a:.1f}" x2="{b:.1f}" y1="{yy - size * .32:.1f}" y2="{yy - size * .32:.1f}" stroke="{lead}" '
                      f'stroke-width="{size * .1:.2f}" stroke-dasharray="0 {size * .34:.2f}" stroke-linecap="round"/>')
    return s


def up_arrow(cx, y, h, color, sw, extra=''):
    """上を指す矢印（y が先端、h が長さ）。"""
    return (f'<path d="M{cx} {y + h} V{y + sw / 2} M{cx - h * .4} {y + h * .4} L{cx} {y} L{cx + h * .4} {y + h * .4}" fill="none" '
            f'stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" {extra}/>')


def neon(text, x, y, size, color, fam, sw, anchor='middle', ls=0, w=700):
    """ネオン管のように光る文字（ぼかした光・色の管・白い芯）。"""
    st = 'fill="none" stroke-linejoin="round" stroke-linecap="round"'
    glow = T(x, y, text, size, 'none', fam, w, anchor, ls, st + f' stroke="{color}" stroke-width="{sw * 1.5}"')
    tube = T(x, y, text, size, 'none', fam, w, anchor, ls, st + f' stroke="{color}" stroke-width="{sw}"')
    core = T(x, y, text, size, 'none', fam, w, anchor, ls, st + f' stroke="#fff" stroke-width="{sw * .3}" opacity=".85"')
    return f'<g filter="url(#neon)">{glow}</g>{tube}{core}'


def neon_path(d, color, sw):
    st = 'fill="none" stroke-linejoin="round" stroke-linecap="round"'
    return (f'<g filter="url(#neon)"><path d="{d}" {st} stroke="{color}" stroke-width="{sw * 1.5}"/></g>'
            f'<path d="{d}" {st} stroke="{color}" stroke-width="{sw}"/><path d="{d}" {st} stroke="#fff" stroke-width="{sw * .3}" opacity=".85"/>')


def tag(x, y, text, size=15, bg='#000', fg=WHITE, op=.72):
    """写真の上に置く小さな札（x, y は札の左下）。"""
    w = tw(text, size) + size * 1.2
    return (f'<rect x="{x}" y="{y - size * 1.6:.1f}" width="{w:.1f}" height="{size * 1.6:.1f}" rx="{size * .3:.1f}" fill="{bg}" opacity="{op}"/>'
            + T(x + size * .6, y - size * .48, text, size, fg, JPB, 700, 'start'))


def polaroid(name, x, y, w, h, rot, caption, cid, fx=.5, fy=.5):
    """テープで貼った写真（白いふち付き）。"""
    cx, cy = x + w / 2, y + h / 2
    s = f'<g transform="rotate({rot} {cx} {cy})">'
    s += f'<rect x="{x + 4}" y="{y + 6}" width="{w}" height="{h}" fill="#000" opacity=".45" filter="url(#soft)"/>'
    s += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#f3f0e8"/>'
    s += ph(name, x + 9, y + 9, w - 18, h - 46, cid, fx, fy)
    s += T(cx, y + h - 13, caption, 17, '#33302b', JPB, 700)
    s += f'<rect x="{cx - 34}" y="{y - 12}" width="68" height="24" fill="#efe2b8" opacity=".82" transform="rotate({-rot * 2} {cx} {y})"/>'
    return s + '</g>'


# ---- 10案のポスター ----------------------------------------------------------------------
def poster_classic(p):
    """01 黒と金の王道。"""
    g = f'{p}-g'
    s = (f'<defs>{gold_grad(g)}<radialGradient id="{p}-bg" cx=".5" cy=".38" r=".8"><stop offset="0" stop-color="#241f2a"/>'
         f'<stop offset="1" stop-color="#0a090c"/></radialGradient></defs>')
    s += f'<rect width="{PW}" height="{PH}" fill="url(#{p}-bg)"/>'
    s += f'<rect x="20" y="20" width="{PW - 40}" height="{PH - 40}" fill="none" stroke="{GOLD}" stroke-width="2.2"/>'
    s += f'<rect x="27" y="27" width="{PW - 54}" height="{PH - 54}" fill="none" stroke="{GOLD}" stroke-width=".8" opacity=".8"/>'
    for x, y in ((20, 20), (PW - 20, 20), (20, PH - 20), (PW - 20, PH - 20)):
        s += f'<rect x="{x - 5}" y="{y - 5}" width="10" height="10" transform="rotate(45 {x} {y})" fill="{GOLD}"/>'
    s += T(297, 66, 'DINING BAR  ·  NERIMA', 14, GOLD, NUM, 600, ls=7)
    s += T(297, 158, 'BAR', 104, f'url(#{g})', SERIF, 700, ls=36)
    s += logo(297, 172, 232)
    s += ph('counter-dark', 52, 312, 490, 212, f'{p}-ph', fx=.62, fy=.56)
    s += f'<rect x="52" y="312" width="490" height="212" fill="none" stroke="{GOLD}" stroke-width="1.4"/>'
    s += T(56, 636, '3F', 122, f'url(#{g})', NUM, 700, 'start')
    s += up_arrow(242, 556, 76, GOLD_L, 7)
    s += T(286, 590, 'このビルの3階', 36, WHITE, JPB, 700, 'start')
    s += T(286, 628, 'エレベーターでどうぞ', 24, '#d8d1c4', JPB, 500, 'start')
    s += f'<line x1="60" x2="534" y1="656" y2="656" stroke="{GOLD}" stroke-width="1" opacity=".6"/>'
    s += T(297, 690, CHARGE, 23, GOLD_L, JPB, 700)
    s += plist(64, 724, 212, rows('beer', 'whisky', 'cocktail'), 18, '#ebe5d8', GOLD_L, '#7d6c48', 26)
    s += plist(318, 724, 212, rows('shochu', 'food', 'darts'), 18, '#ebe5d8', GOLD_L, '#7d6c48', 26)
    s += T(297, 801, FOOT, 12.5, '#bdb6a8', JPB, 500)
    return s


def poster_photo(p):
    """02 写真が主役。"""
    g = f'{p}-g'
    s = f'<defs>{gold_grad(g)}{shade(p + "-t", .9, 0)}{shade(p + "-b", 0, .95)}</defs>'
    s += f'<rect width="{PW}" height="{PH}" fill="#000"/>'
    s += ph('counter-dark', 0, 0, PW, PH, f'{p}-ph', fx=.66, fy=.5)
    s += f'<rect x="0" y="0" width="{PW}" height="330" fill="url(#{p}-t)"/>'
    s += f'<rect x="0" y="440" width="{PW}" height="{PH - 440}" fill="url(#{p}-b)"/>'
    s += T(297, 62, 'DINING BAR  ·  NERIMA', 14, GOLD_L, NUM, 600, ls=7)
    s += logo(297, 78, 250)
    s += T(297, 298, 'BAR', 92, WHITE, SERIF, 700, ls=34, extra='filter="url(#tshadow)"')
    s += T(297, 552, 'このビルの3階に、', 32, WHITE, JPB, 700, extra='filter="url(#tshadow)"')
    s += T(297, 594, 'こんなバーがあります。', 32, WHITE, JPB, 700, extra='filter="url(#tshadow)"')
    s += f'<line x1="52" x2="542" y1="622" y2="622" stroke="{GOLD}" stroke-width="1.2" opacity=".75"/>'
    s += T(48, 748, '3F', 132, f'url(#{g})', NUM, 700, 'start')
    s += T(54, 780, 'エレベーターで3階へ', 17, '#e6dfd0', JPB, 500, 'start')
    s += T(240, 660, 'テーブルチャージ', 17, '#e6dfd0', JPB, 700, 'start')
    s += T(542, 660, f'{CHARGE_PER} {CHARGE_AMT}', 20, GOLD_L, JPB, 700, 'end')
    s += plist(240, 692, 302, rows('beer', 'whisky', 'cocktail', 'food', 'darts'), 17, '#efe9dc', GOLD_L, '#8a7a56', 22.5)
    s += T(297, 812, FOOT, 12.5, '#cfc8ba', JPB, 500)
    return s


def poster_neon(p):
    """03 ネオンサイン風。"""
    s = (f'<defs><pattern id="{p}-brick" width="64" height="26" patternUnits="userSpaceOnUse"><rect width="64" height="26" fill="#170f19"/>'
         f'<path d="M0 .8H64 M0 13.8H64 M.8 0V13 M32.8 13V26" stroke="#271b2c" stroke-width="1.6"/></pattern>'
         f'<radialGradient id="{p}-v" cx=".5" cy=".45" r=".75"><stop offset=".35" stop-color="#000" stop-opacity="0"/>'
         f'<stop offset="1" stop-color="#000" stop-opacity=".78"/></radialGradient></defs>')
    s += f'<rect width="{PW}" height="{PH}" fill="url(#{p}-brick)"/><rect width="{PW}" height="{PH}" fill="url(#{p}-v)"/>'
    s += neon('Bar', 297, 226, 200, '#ff4fa3', SCRIPT, 5.5)
    s += neon('X-III', 297, 354, 108, '#ffcf6b', SERIF, 3.6, ls=8)
    s += T(297, 394, 'CROSSLEY', 22, '#ffd98a', NUM, 600, ls=12, extra='filter="url(#neon)"')
    s += neon('3F', 50, 588, 158, '#5fe3ff', NUM, 5, 'start')
    s += neon_path('M276 590 V456 M244 488 L276 456 L308 488', '#5fe3ff', 7)
    s += ph('counter-dark', 318, 436, 228, 160, f'{p}-ph', fx=.62, fy=.55, rx=10)
    s += neon_path('M328 436 H536 A10 10 0 0 1 546 446 V586 A10 10 0 0 1 536 596 H328 A10 10 0 0 1 318 586 V446 A10 10 0 0 1 328 436 Z', '#ff4fa3', 3)
    s += T(297, 642, 'このビルの3階・エレベーターでどうぞ', 22, '#f4eefc', JPB, 700)
    s += neon_path('M81 664 H513 A21 21 0 0 1 513 706 H81 A21 21 0 0 1 81 664 Z', '#ff4fa3', 2.4)
    s += T(297, 693, CHARGE, 20, WHITE, JPB, 700)
    s += plist(66, 738, 212, rows('beer', 'whisky', 'cocktail'), 17, '#bdf0ff', WHITE, '#3f7482', 24)
    s += plist(316, 738, 212, rows('shochu', 'food', 'darts'), 17, '#bdf0ff', WHITE, '#3f7482', 24)
    s += T(297, 812, FOOT, 12.5, '#cdbfd8', JPB, 500)
    return s


def poster_chalk(p):
    """04 黒板のメニュー。"""
    s = f'<rect width="{PW}" height="{PH}" fill="#4a2f1b"/>'
    for i, y in enumerate(range(6, PH, 9)):
        s += f'<line x1="0" x2="{PW}" y1="{y}" y2="{y + (i % 3) - 1}" stroke="#3a2414" stroke-width="{1 + i % 2}" opacity=".7"/>'
    s += '<rect x="26" y="26" width="542" height="789" fill="#1c2a24"/><rect x="26" y="26" width="542" height="789" fill="#fff" filter="url(#dust)"/>'
    c = '<g filter="url(#chalk)">'
    c += T(297, 126, 'BAR', 100, '#f3f0e6', HAND, 700, ls=14)
    c += T(62, 372, '3F', 130, '#f6dc72', HAND, 700, 'start')
    c += up_arrow(262, 258, 112, '#f6dc72', 9)
    c += T(312, 296, 'このビルの', 28, '#f3f0e6', JPB, 700, 'start')
    c += T(312, 340, '3階です！', 40, '#f3f0e6', JPB, 900, 'start')
    c += T(312, 372, 'エレベーターでどうぞ', 18, '#cfe6f5', JPB, 500, 'start')
    c += T(297, 654, '— MENU —', 30, '#f3f0e6', HAND, 700, ls=6)
    c += T(297, 690, CHARGE, 22, '#ffb9c9', JPB, 700)
    c += plist(64, 726, 212, rows('beer', 'whisky', 'cocktail'), 18, '#f3f0e6', '#f3f0e6', '#9fb6aa', 27)
    c += plist(318, 726, 212, rows('shochu', 'tequila', 'food'), 18, '#f3f0e6', '#f3f0e6', '#9fb6aa', 27)
    c += '</g>'
    s += c
    s += logo(297, 138, 190, white=True, extra='opacity=".9"')
    s += polaroid('counter-dark', 58, 404, 232, 200, -4, 'カウンター', f'{p}-p1', fx=.62)
    s += polaroid('darts', 304, 408, 232, 200, 3, 'ダーツ 1ゲーム ¥100', f'{p}-p2', fx=.48, fy=.42)
    s += T(297, 804, FOOT, 12.5, '#cfe6f5', JPB, 500)
    return s


def poster_big3f(p):
    """05 大きな「3F」。"""
    s = (f'<defs><linearGradient id="{p}-y" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffdb57"/>'
         f'<stop offset="1" stop-color="#f3b022"/></linearGradient>{gold_grad(p + "-g")}</defs>')
    s += f'<rect width="{PW}" height="452" fill="url(#{p}-y)"/><rect y="452" width="{PW}" height="{PH - 452}" fill="#121014"/>'
    s += T(297, 80, 'このビルの', 40, '#141008', JPB, 900, ls=6)
    s += T(297, 364, '3F', 330, '#141008', NUM, 700)
    s += T(297, 428, 'に、バーがあります。', 44, '#141008', JPB, 900)
    s += logo(165, 474, 206)
    s += T(408, 532, 'BAR', 64, f'url(#{p}-g)', SERIF, 700, ls=18)
    s += T(408, 568, 'エレベーターで3階へ', 19, '#e8e1d2', JPB, 500)
    s += ph('counter-dark', 40, 592, 252, 100, f'{p}-p1', fx=.62, fy=.55, rx=6)
    s += ph('tables', 302, 592, 252, 100, f'{p}-p2', fx=.5, fy=.62, rx=6)
    s += T(297, 728, CHARGE, 21, '#ffd957', JPB, 700)
    pr = [f'{k} {v}' for k, v in rows('beer', 'whisky', 'cocktail')]
    s += T(297, 756, ' ・ '.join(pr), 15.5, WHITE, JPB, 500)
    pr = [f'{k} {v}' for k, v in rows('shochu', 'food', 'darts')]
    s += T(297, 779, ' ・ '.join(pr), 15.5, WHITE, JPB, 500)
    s += T(297, 806, FOOT, 12, '#c9c2b4', JPB, 500)
    return s


def poster_three(p):
    """06 3枚の写真で見せる。"""
    g = f'{p}-g'
    s = f'<defs>{gold_grad(g)}</defs><rect width="{PW}" height="{PH}" fill="#0c0b0e"/>'
    s += logo(168, 44, 226)
    s += T(548, 112, 'BAR', 86, f'url(#{g})', SERIF, 700, 'end', ls=14)
    s += T(548, 176, '3F', 62, f'url(#{g})', NUM, 700, 'end')
    s += T(462, 170, 'このビルの', 22, WHITE, JPB, 700, 'end')
    s += f'<line x1="40" x2="554" y1="196" y2="196" stroke="{GOLD}" stroke-width="1.2" opacity=".7"/>'
    s += ph('counter-dark', 40, 210, 514, 214, f'{p}-p1', fx=.6, fy=.55)
    s += ph('tables', 40, 432, 253, 162, f'{p}-p2', fx=.5, fy=.62)
    s += ph('darts', 301, 432, 253, 162, f'{p}-p3', fx=.48, fy=.42)
    s += tag(50, 414, 'カウンター') + tag(50, 584, 'テーブル席') + tag(311, 584, 'ダーツ 1ゲーム ¥100')
    s += T(297, 628, 'おひとりでも、仲間とでも。エレベーターで3階へ。', 20, '#e9e3d6', JPB, 500)
    s += f'<line x1="60" x2="534" y1="646" y2="646" stroke="{GOLD}" stroke-width="1" opacity=".55"/>'
    s += T(297, 678, CHARGE, 21, GOLD_L, JPB, 700)
    s += plist(64, 710, 212, rows('beer', 'whisky', 'cocktail'), 17, '#ebe5d8', GOLD_L, '#7d6c48', 24)
    s += plist(318, 710, 212, rows('shochu', 'tequila', 'food'), 17, '#ebe5d8', GOLD_L, '#7d6c48', 24)
    s += T(297, 790, FOOT, 12.5, '#bdb6a8', JPB, 500)
    s += T(297, 810, f'Instagram {INSTA}', 12.5, GOLD, NUM, 600, ls=1)
    return s


def poster_label(p):
    """07 ウイスキーのラベル。"""
    green, red, gold = '#20402f', '#8e2a22', '#b8924a'
    s = f'<defs><path id="{p}-arc" d="M110 160 A230 150 0 0 1 484 160"/></defs>'
    s += f'<rect width="{PW}" height="{PH}" fill="#efe4cb"/><rect width="{PW}" height="{PH}" filter="url(#paper)"/>'
    s += f'<rect x="18" y="18" width="{PW - 36}" height="{PH - 36}" fill="none" stroke="{green}" stroke-width="7"/>'
    s += f'<rect x="28" y="28" width="{PW - 56}" height="{PH - 56}" fill="none" stroke="{gold}" stroke-width="1.6"/>'
    s += f'<rect x="33" y="33" width="{PW - 66}" height="{PH - 66}" fill="none" stroke="{green}" stroke-width=".8"/>'
    for x, y in ((33, 33), (PW - 33, 33), (33, PH - 33), (PW - 33, PH - 33)):
        s += f'<rect x="{x - 6}" y="{y - 6}" width="12" height="12" transform="rotate(45 {x} {y})" fill="{gold}"/>'
    s += (f'<text font-family="{NUM}" font-size="19" font-weight="600" fill="{green}" letter-spacing="5">'
          f'<textPath href="#{p}-arc" startOffset="50%" text-anchor="middle">DINING BAR · NERIMA TOKYO</textPath></text>')
    s += logo(297, 162, 300, extra='filter="url(#ink)"')
    s += T(297, 340, '— EST. 2026 —', 14, gold, SERIF, 700, ls=4)
    s += f'<path d="M50 354 H544 L528 376 L544 398 H50 L66 376 Z" fill="{red}"/>'
    s += f'<path d="M66 358 H528 M66 394 H528" stroke="#e9c98a" stroke-width=".8" opacity=".8"/>'
    s += T(297, 385, 'THIRD FLOOR  ·  3F', 25, '#f6ecd6', NUM, 700, ls=6)
    s += ph('backbar', 129, 412, 336, 210, f'{p}-ph', fx=.72, fy=.6, clip='M297 412 A168 105 0 1 1 296.9 412 Z')
    s += f'<ellipse cx="297" cy="517" rx="168" ry="105" fill="none" stroke="{gold}" stroke-width="3"/>'
    s += f'<ellipse cx="297" cy="517" rx="177" ry="114" fill="none" stroke="{green}" stroke-width="1.4"/>'
    s += T(297, 660, 'このビルの3階・エレベーターでどうぞ', 22, green, JPB, 700)
    s += f'<rect x="68" y="674" width="458" height="112" fill="none" stroke="{green}" stroke-width="1.3"/>'
    s += T(297, 700, CHARGE, 19, red, JPB, 700)
    s += f'<line x1="84" x2="510" y1="711" y2="711" stroke="{gold}" stroke-width=".9"/>'
    s += plist(86, 732, 196, rows('beer', 'whisky', 'cocktail'), 15, green, green, '#b9a77c', 20)
    s += plist(312, 732, 196, rows('shochu', 'food', 'darts'), 15, green, green, '#b9a77c', 20)
    s += T(297, 802, FOOT, 12, green, JPB, 500)
    return s


def poster_deco(p):
    """08 アールデコ。"""
    g = f'{p}-g'
    s = (f'<defs>{gold_grad(g)}<linearGradient id="{p}-bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0f182d"/>'
         f'<stop offset="1" stop-color="#070b15"/></linearGradient></defs>')
    s += f'<rect width="{PW}" height="{PH}" fill="url(#{p}-bg)"/>'
    n = 22
    for inset, sw in ((20, 1.8), (28, .7)):
        a, b, c, d = inset, PW - inset, inset, PH - inset
        s += (f'<path d="M{a + n} {c} H{b - n} L{b} {c + n} V{d - n} L{b - n} {d} H{a + n} L{a} {d - n} V{c + n} Z" '
              f'fill="none" stroke="{GOLD}" stroke-width="{sw}"/>')
    cx, cy = 297, 206
    for deg in range(186, 356, 6):
        r = math.radians(deg)
        s += (f'<line x1="{cx + 108 * math.cos(r):.1f}" y1="{cy + 108 * math.sin(r):.1f}" x2="{cx + 172 * math.cos(r):.1f}" '
              f'y2="{cy + 172 * math.sin(r):.1f}" stroke="{GOLD}" stroke-width="1" opacity=".45"/>')
    s += f'<path d="M{cx - 100} {cy} A100 100 0 0 1 {cx + 100} {cy}" fill="none" stroke="{GOLD}" stroke-width="1.6"/>'
    s += f'<path d="M{cx - 180} {cy} A180 180 0 0 1 {cx + 180} {cy}" fill="none" stroke="{GOLD}" stroke-width=".8" opacity=".6"/>'
    s += logo(297, 128, 236, extra='filter="url(#gilt)"')
    s += T(297, 330, 'BAR', 68, f'url(#{g})', NUM, 600, ls=46, extra='style="font-stretch:75%"')
    s += f'<path d="M150 348 H262 M332 348 H444" stroke="{GOLD}" stroke-width="1.2"/>'
    s += f'<rect x="291" y="342" width="12" height="12" transform="rotate(45 297 348)" fill="{GOLD}"/>'
    arch = 'M152 640 V510 A145 145 0 0 1 442 510 V640 Z'
    s += ph('counter-dark', 152, 365, 290, 275, f'{p}-ph', fx=.6, fy=.55, clip=arch)
    s += f'<path d="{arch}" fill="none" stroke="{GOLD}" stroke-width="2.2"/>'
    s += f'<path d="M142 650 V510 A155 155 0 0 1 452 510 V650 Z" fill="none" stroke="{GOLD}" stroke-width=".8" opacity=".8"/>'
    s += f'<path d="M247 618 H347 L365 640 L347 662 H247 L229 640 Z" fill="#0b1222" stroke="{GOLD}" stroke-width="1.6"/>'
    s += T(297, 657, '3F', 46, GOLD_L, NUM, 700)
    s += T(297, 694, 'このビルの3階・エレベーターでどうぞ', 19, '#e8e2d2', JPB, 500)
    s += T(297, 724, CHARGE, 18, GOLD_L, JPB, 700)
    pr = [f'{k} {v}' for k, v in rows('beer', 'whisky', 'cocktail')]
    s += T(297, 750, '  ◆  '.join(pr), 14, '#e8e2d2', JPB, 500)
    pr = [f'{k} {v}' for k, v in rows('shochu', 'food', 'darts')]
    s += T(297, 772, '  ◆  '.join(pr), 14, '#e8e2d2', JPB, 500)
    s += T(297, 796, FOOT, 11.5, '#a9a497', JPB, 500)
    return s


def poster_first(p):
    """09 はじめての方へ（料金表）。"""
    g = f'{p}-g'
    ink, sub = '#1b160e', '#6b5a3a'
    s = f'<defs>{gold_grad(g)}</defs><rect width="{PW}" height="{PH}" fill="#111016"/>'
    s += logo(297, 30, 196)
    s += T(297, 196, 'BAR · 3F', 60, f'url(#{g})', NUM, 700, ls=8)
    s += T(297, 230, 'このビルの3階・エレベーターでどうぞ', 18, '#e6dfd0', JPB, 500)
    s += f'<rect y="246" width="{PW}" height="416" fill="#fbf7ee"/>'
    s += T(297, 298, 'はじめての方へ', 40, ink, JPB, 900, ls=4)
    s += T(297, 326, '料金の目安です。1杯だけでも、お気軽にどうぞ。', 17, sub, JPB, 500)
    s += '<rect x="46" y="342" width="502" height="76" rx="10" fill="#f2e1b0"/>'
    s += T(68, 374, 'テーブルチャージ', 25, ink, JPB, 900, 'start')
    s += T(68, 402, CHARGE_PER, 17, sub, JPB, 500, 'start')
    s += T(528, 400, CHARGE_AMT, 46, ink, NUM, 700, 'end')
    s += plist(68, 454, 460, rows('beer', 'whisky', 'cocktail', 'shochu', 'food', 'darts'), 23, ink, ink, '#c4b48c', 32)
    s += f'<line x1="68" x2="528" y1="628" y2="628" stroke="#e3d6b4" stroke-width="1"/>'
    s += T(297, 650, f'ご予算の目安：{BUDGET}', 16, sub, JPB, 500)
    for i, (name, fx, fy) in enumerate((('counter-dark', .62, .55), ('tables', .5, .62), ('darts', .48, .42))):
        s += ph(name, 40 + i * 177, 680, 160, 96, f'{p}-p{i}', fx, fy, rx=6)
    s += T(297, 806, FOOT, 12.5, '#c9c2b4', JPB, 500)
    return s


def poster_master(p):
    """10 マスターの一杯。"""
    g = f'{p}-g'
    s = f'<defs>{gold_grad(g)}{shade(p + "-l", .92, 0, False)}{shade(p + "-b", 0, .96)}</defs>'
    s += f'<rect width="{PW}" height="{PH}" fill="#000"/>'
    s += ph('backbar', 0, 0, PW, PH, f'{p}-ph', fx=.72, fy=.5)
    s += f'<rect width="380" height="{PH}" fill="url(#{p}-l)"/>'
    s += f'<rect y="520" width="{PW}" height="{PH - 520}" fill="url(#{p}-b)"/>'
    s += logo(150, 44, 204)
    vt = f'writing-mode="vertical-rl" font-family="{MIN}" font-weight="600" fill="{WHITE}" letter-spacing="2" filter="url(#tshadow)"'
    s += f'<text x="124" y="180" font-size="31" {vt}>銀座・麻布で腕を磨いた</text>'
    s += f'<text x="80" y="180" font-size="31" {vt}>マスターの一杯を、練馬で。</text>'
    s += T(48, 716, '3F', 100, f'url(#{g})', NUM, 700, 'start')
    s += T(178, 674, 'BAR', 44, GOLD_L, SERIF, 700, 'start', ls=12)
    s += T(178, 708, 'このビルの3階・エレベーターでどうぞ', 18, WHITE, JPB, 500, 'start')
    s += T(48, 748, CHARGE, 18, GOLD_L, JPB, 700, 'start')
    pr = [f'{k} {v}' for k, v in rows('cocktail', 'whisky', 'beer', 'food')]
    s += T(48, 774, '　'.join(pr), 14, '#ece6d9', JPB, 500, 'start')
    s += T(48, 800, FOOT, 12, '#bdb6a8', JPB, 500, 'start')
    return s


# 案の id → (ポスターを描く関数, 光ったときのまわりの色)
POSTERS = {
    'classic': (poster_classic, '#ffe2a6'), 'photo': (poster_photo, '#d7f5b4'), 'neon': (poster_neon, '#ff9ad2'),
    'chalk': (poster_chalk, '#f3efe2'), 'big3f': (poster_big3f, '#ffd85a'), 'three': (poster_three, '#ffe2a6'),
    'label': (poster_label, '#fff1d2'), 'deco': (poster_deco, '#ffe2a6'), 'first': (poster_first, '#fffaf0'),
    'master': (poster_master, '#d7f5b4'),
}


def poster(pr):
    func, _ = POSTERS[pr['id']]
    p = 'p' + pr['no']
    return (f'<clipPath id="{p}-all"><rect width="{PW}" height="{PH}"/></clipPath>'
            f'<g clip-path="url(#{p}-all)">{func(p)}</g>')


# ---- スタンド（正面・mm。左上が 0,0。幅 640・高さ 1185。上の 884 がボード面） ----------------------
def stand_svg(art, lit=True, cord=True):
    m = 'url(#metal)'
    s = ''
    s += f'<rect x="12" y="{BOARD_H - 30}" width="26" height="{STAND_H - BOARD_H + 14}" fill="{m}"/>'
    s += f'<rect x="{STAND_W - 38}" y="{BOARD_H - 30}" width="26" height="{STAND_H - BOARD_H + 14}" fill="{m}"/>'
    s += f'<rect x="38" y="{STAND_H - 120}" width="{STAND_W - 76}" height="14" fill="url(#metalV)"/>'
    for x in (4, STAND_W - 46):
        s += f'<rect x="{x}" y="{STAND_H - 18}" width="42" height="18" rx="5" fill="#2a2c31"/>'
    if cord:
        s += (f'<path d="M{STAND_W - 30} {BOARD_H - 6} C{STAND_W - 30} {STAND_H - 60} {STAND_W - 10} {STAND_H - 6} '
              f'{STAND_W + 60} {STAND_H - 5} H{STAND_W + 260}" fill="none" stroke="#141519" stroke-width="7"/>')
    s += f'<rect x="0" y="0" width="{STAND_W}" height="{BOARD_H}" rx="8" fill="{m}"/>'
    px, py = (STAND_W - PW) / 2, (BOARD_H - PH) / 2
    s += f'<g transform="translate({px},{py})">{art}</g>'
    if lit:
        s += f'<rect x="{px}" y="{py}" width="{PW}" height="{PH}" fill="url(#panelLit)" style="mix-blend-mode:screen"/>'
    s += (f'<path d="M0 0H{STAND_W}V{BOARD_H}H0Z M{LIP} {LIP}V{BOARD_H - LIP}H{STAND_W - LIP}V{LIP}Z" fill="{m}" fill-rule="evenodd"/>'
          f'<rect x="{LIP}" y="{LIP}" width="{STAND_W - 2 * LIP}" height="{BOARD_H - 2 * LIP}" fill="none" stroke="#5b6068" stroke-width="2.5"/>'
          f'<rect x="1.5" y="1.5" width="{STAND_W - 3}" height="{BOARD_H - 3}" rx="7" fill="none" stroke="#6c727b" stroke-width="3"/>')
    s += f'<path d="M{LIP} {LIP} H{LIP + 190} L{LIP} {LIP + 300} Z" fill="#fff" opacity=".07"/>'
    return s


def place_stand(pr, cx=CX):
    """スタンドを、入口の横の段の上（ビルの敷地の中）に置く。"""
    _, glow = POSTERS[pr['id']]
    x0, y0 = cx - STAND_W * S / 2, G - STAND_H * S
    s = f'<g opacity=".32" filter="url(#softer)"><rect x="{x0 - 3}" y="{y0 - 2}" width="{STAND_W * S + 6}" height="{BOARD_H * S + 4}" fill="{glow}"/></g>'
    s += f'<ellipse cx="{cx}" cy="{G + 5}" rx="75" ry="11" fill="url(#spill)"/>'
    s += f'<rect x="{x0}" y="{G + 1}" width="{STAND_W * S}" height="5" fill="{glow}" opacity=".18" filter="url(#soft)"/>'
    s += f'<g transform="translate({x0:.2f},{y0:.2f}) scale({S})">{stand_svg(poster(pr))}</g>'
    return s


# ---- 建物（夜） -----------------------------------------------------------------
def building():
    s = ['<rect x="0" y="0" width="1760" height="1100" fill="url(#sky)"/>']
    # 左の隣のビル
    s.append('<rect x="0" y="110" width="345" height="820" fill="#181b2e"/>')
    for r in range(9):
        for c in range(4):
            lit = (r * 7 + c * 3) % 5 == 0
            s.append(f'<rect x="{22 + c * 80}" y="{140 + r * 85}" width="48" height="44" fill="{"#f2d39a" if lit else "#22263c"}" opacity="{.55 if lit else 1}"/>')
    # 右の円柱の建物と、その奥のビル
    s.append('<rect x="1400" y="30" width="150" height="900" fill="url(#cyl)"/>')
    for y in range(50, 640, 46):
        s.append(f'<line x1="1400" x2="1550" y1="{y}" y2="{y}" stroke="#5c6476" stroke-width="2" opacity=".6"/>')
    s.append('<rect x="1400" y="640" width="150" height="270" fill="#363b47"/>')
    s.append('<rect x="1550" y="0" width="230" height="930" fill="#2a2029"/>')
    for y in range(60, 600, 120):
        s.append(f'<rect x="1550" y="{y}" width="230" height="22" fill="#4a3640"/><rect x="1575" y="{y - 70}" width="60" height="50" fill="#f2c98a" opacity=".45"/>')
    s.append('<rect x="1550" y="700" width="230" height="210" fill="#4a2b1d"/><rect x="1570" y="740" width="190" height="120" fill="#ffb867" opacity=".35"/>')
    # 本体（左の面・丸い角・右の面）
    s.append('<rect x="330" y="0" width="270" height="905" fill="url(#faceL)"/>')
    s.append('<rect x="600" y="0" width="410" height="905" fill="url(#corner)"/>')
    s.append('<rect x="1010" y="0" width="390" height="905" fill="url(#faceR)"/>')
    s.append('<line x1="600" x2="600" y1="0" y2="905" stroke="#0d1d47" stroke-width="2" opacity=".5"/><line x1="1010" x2="1010" y1="0" y2="905" stroke="#0d1d47" stroke-width="2" opacity=".5"/>')
    # 階の帯
    for y1, y2 in ((0, 50), (190, 245), (400, 455), (610, 665)):
        s.append(f'<rect x="330" y="{y1}" width="1070" height="{y2 - y1}" fill="#ffffff" opacity=".035"/>')
        s.append(f'<line x1="330" x2="1400" y1="{y2}" y2="{y2}" stroke="#091634" stroke-width="4" opacity=".8"/>')
        s.append(f'<line x1="330" x2="1400" y1="{y1 + 2}" y2="{y1 + 2}" stroke="#6d93ef" stroke-width="1.5" opacity=".22"/>')
    xs = [(345, 465), (478, 590), (612, 702), (708, 800), (806, 898), (904, 996), (1024, 1112), (1122, 1210), (1220, 1300)]
    for (y1, y2, fill) in ((470, 600, 'win2'), (258, 392, 'win3'), (60, 182, 'win4')):
        for i, (x1, x2) in enumerate(xs):
            s.append(f'<rect x="{x1}" y="{y1}" width="{x2 - x1}" height="{y2 - y1}" fill="url(#{fill})"/>')
            if fill == 'win2':
                for bx in range(x1 + 6, x2, 10):
                    s.append(f'<line x1="{bx}" x2="{bx}" y1="{y1}" y2="{y2}" stroke="#d2b9ee" stroke-width="1" opacity=".08"/>')
            if fill == 'win3':
                s.append(f'<circle cx="{(x1 + x2) / 2}" cy="{y1 + 10}" r="3" fill="#ffe2a8" opacity=".8"/>')
                for sy in (y2 - 46, y2 - 18):
                    s.append(f'<line x1="{x1}" x2="{x2}" y1="{sy}" y2="{sy}" stroke="#62f2a6" stroke-width="2" opacity=".5"/>')
                    for bx in range(x1 + 5, x2 - 4, 9):
                        bh = 10 + (bx * 7 % 9)
                        s.append(f'<rect x="{bx}" y="{sy - bh}" width="5" height="{bh}" rx="2" fill="#0a1d17" opacity=".9"/>')
            if fill == 'win4' and i == 6:
                s.append(f'<rect x="{x1}" y="{y1}" width="{x2 - x1}" height="{y2 - y1}" fill="#ffd89a" opacity=".22"/>')
            s.append(f'<rect x="{x1}" y="{y1}" width="{x2 - x1}" height="{y2 - y1}" fill="none" stroke="#0c1a42" stroke-width="5"/>')
            s.append(f'<path d="M{x1 + 8} {y2 - 8} L{x1 + (x2 - x1) * .45} {y1 + 6}" stroke="#fff" stroke-width="8" opacity=".035"/>')
    # 3階の窓の小さな赤いネオン（今あるもの）
    s.append('<g filter="url(#soft)"><rect x="930" y="272" width="44" height="22" rx="6" fill="none" stroke="#ff3d4e" stroke-width="4"/></g><rect x="930" y="272" width="44" height="22" rx="6" fill="none" stroke="#ff8e98" stroke-width="1.5"/>')
    # 1階: 左の面（壁・小窓・室外機）
    s.append('<rect x="360" y="715" width="80" height="70" fill="#0e1830"/><g stroke="#3a4a72" stroke-width="2">' + ''.join(f'<line x1="{x}" x2="{x}" y1="715" y2="785"/>' for x in range(370, 440, 12)) + '</g>')
    s.append('<rect x="470" y="822" width="78" height="60" rx="4" fill="#5c6372"/><circle cx="500" cy="852" r="20" fill="#3b414d"/>')
    # 1階: 丸い角（隣のお店のすりガラス）
    s.append('<rect x="618" y="688" width="374" height="182" fill="#0e1a3a"/><rect x="618" y="688" width="374" height="182" fill="url(#frost)"/>')
    s.append('<g stroke="#0e1d47" stroke-width="5"><line x1="742" x2="742" y1="688" y2="870"/><line x1="866" x2="866" y1="688" y2="870"/></g>')
    s.append('<g stroke="#0b0e17" stroke-width="3">' + ''.join(f'<line x1="{x}" x2="{x}" y1="848" y2="884"/>' for x in range(624, 990, 16)) + '<line x1="618" x2="992" y1="848" y2="848"/></g>')
    # 1階: 右の面（隣のお店の木の扉・柱・入口のガラス扉・案内板）
    s.append('<rect x="1016" y="690" width="76" height="26" fill="#d9c9a8" opacity=".35"/>')
    s.append('<rect x="1018" y="718" width="72" height="187" fill="#2a1c13"/>' + ''.join(f'<line x1="{x}" x2="{x}" y1="722" y2="902" stroke="#3b2a1d" stroke-width="2"/>' for x in range(1026, 1090, 9)))
    s.append('<rect x="1076" y="800" width="5" height="34" rx="2" fill="#c9a45c"/>')
    s.append('<rect x="1098" y="768" width="22" height="26" fill="#111" stroke="#666" stroke-width="1"/>')
    s.append('<rect x="1125" y="668" width="140" height="32" fill="#0d1527"/>')
    s.append('<rect x="1125" y="700" width="140" height="205" fill="url(#lobby)"/>')
    s.append('<rect x="1170" y="758" width="52" height="135" fill="#aeb8c3"/><line x1="1196" x2="1196" y1="758" y2="893" stroke="#7c8692" stroke-width="2"/><rect x="1192" y="744" width="8" height="8" rx="2" fill="#5ad19a"/>')
    s.append('<rect x="1125" y="880" width="140" height="25" fill="#97a1ab" opacity=".9"/>')
    s.append('<g fill="none" stroke="#9aa3ad" stroke-width="5"><rect x="1127" y="700" width="68" height="205"/><rect x="1195" y="700" width="68" height="205"/></g>')
    s.append('<line x1="1185" x2="1185" y1="780" y2="840" stroke="#e1e6eb" stroke-width="3"/><line x1="1205" x2="1205" y1="780" y2="840" stroke="#e1e6eb" stroke-width="3"/>')
    # 案内板（右の柱）
    s.append('<rect x="1358" y="716" width="36" height="134" rx="2" fill="#d9dde3"/><rect x="1361" y="719" width="30" height="128" fill="#f4f5f7"/>')
    for k in range(6):
        y = 724 + k * 20
        fill = '#121214' if k == 2 else '#c9cdd4'
        s.append(f'<rect x="1364" y="{y}" width="24" height="15" fill="{fill}"/>')
    s.append('<rect x="1367" y="767" width="17" height="3" fill="#c9a45c"/>')
    # 入口の段・歩道・車道・横断歩道
    s.append('<rect x="330" y="905" width="1430" height="200" fill="url(#road)"/>')
    s.append('<rect x="330" y="905" width="1070" height="12" fill="#4b4e5a"/><rect x="1092" y="905" width="308" height="12" fill="#5c606c"/>')
    s.append('<rect x="0" y="917" width="1760" height="30" fill="#3a3d48"/><line x1="0" x2="1760" y1="947" y2="947" stroke="#80838c" stroke-width="3"/>')
    for k in range(7):
        x = 520 + k * 150
        s.append(f'<path d="M{x} 975 L{x + 90} 975 L{x + 70} 1010 L{x - 25} 1010 Z" fill="#cfd2d8" opacity=".75"/>')
    s.append('<path d="M0 960 L380 960 L330 1100 L0 1100 Z" fill="#5a2c33" opacity=".8"/>')
    # 街灯と、入口の明かり
    s.append('<rect x="0" y="0" width="1760" height="1100" fill="url(#lamp)"/>')
    s.append('<ellipse cx="1195" cy="915" rx="170" ry="24" fill="url(#lobbySpill)"/>')
    return '\n'.join(s)


def pole_and_wires():
    s = ['<rect x="1446" y="-20" width="24" height="965" fill="url(#pole)"/>']
    s.append('<rect x="1410" y="110" width="40" height="70" rx="12" fill="#5d626d"/><rect x="1418" y="60" width="96" height="8" fill="#5d626d"/>')
    s.append('<rect x="1468" y="560" width="26" height="40" rx="3" fill="#6d727c"/>')
    for y0, sag, w in ((140, 24, 3), (168, 30, 2.5), (205, 36, 2.5), (238, 30, 3), (300, 40, 2)):
        s.append(f'<path d="M0 {y0} Q 730 {y0 + sag} 1458 {y0 - 6} T 1760 {y0 + 8}" fill="none" stroke="#06080f" stroke-width="{w}" opacity=".95"/>')
    return '\n'.join(s)


def people(x=850):
    def one(px, lean=0, look=0):
        return (f'<g transform="translate({px},938) rotate({lean})" fill="#080b14">'
                f'<circle cx="{look}" cy="-110" r="10"/><path d="M-12 -98 Q0 -102 12 -98 L16 -48 L9 -48 L7 0 L1 0 L0 -40 L-1 0 L-7 0 L-9 -48 L-16 -48 Z"/></g>')
    return one(x, 0, 2) + one(x + 34, 2, 3)


# ---- 画像の枠（題名・説明・吹き出し） ------------------------------------------------------
def chrome(no, title, sub, caption, w=1600, h=1000, foot='ダイニングバー XⅢ クロスリー｜入口の置き看板のポスター'):
    badge = (f'<rect x="40" y="36" rx="12" width="{96 if no else 0}" height="46" fill="{GOLD}"/>'
             f'{T(88, 69, "案" + no, 26, "#1a1408", JP, 700) if no else ""}')
    tx = 152 if no else 44
    s = f'<rect x="0" y="0" width="{w}" height="120" fill="#000" opacity=".45"/>{badge}'
    s += T(tx, 70, title, 34, '#fff', JP, 700, 'start')
    s += T(tx, 104, sub, 19, '#cfd0d8', JP, 500, 'start')
    s += f'<rect x="0" y="{h - 48}" width="{w}" height="48" fill="#000" opacity=".6"/>'
    s += T(40, h - 17, caption, 18, '#d9d9e0', JP, 500, 'start')
    s += T(w - 40, h - 17, foot, 18, GOLD, JP, 700, 'end')
    return s


def callout(tx, ty, lx, ly, lines, anchor='start'):
    """吹き出し: (tx,ty) を指す線と、文字の札。anchor が start なら札の左端が lx、end なら右端が lx（出来上がりの座標）。"""
    wmax = max(len(t) for t in lines) * 21 + 34
    hh = 18 + 30 * len(lines)
    bx = lx if anchor == 'start' else lx - wmax
    ex = bx if tx < bx else bx + wmax
    s = f'<line x1="{tx}" y1="{ty}" x2="{ex}" y2="{ly + hh / 2}" stroke="{GOLD}" stroke-width="2.5"/>'
    s += f'<circle cx="{tx}" cy="{ty}" r="6" fill="{GOLD}"/><circle cx="{tx}" cy="{ty}" r="12" fill="none" stroke="{GOLD}" stroke-width="2" opacity=".6"/>'
    s += f'<rect x="{bx}" y="{ly}" width="{wmax}" height="{hh}" rx="10" fill="#0b0d14" opacity=".9" stroke="{GOLD}" stroke-width="1.5"/>'
    for i, t in enumerate(lines):
        s += T(bx + 17, ly + 38 + i * 30, t, 21 if i else 22, '#fff' if i == 0 else '#d3d4db', JP, 700 if i == 0 else 500, 'start')
    return s


def floor_tags(mapper, x=14):
    s = ''
    for label, y1, y2, hl in (('3F', 258, 392, True), ('2F', 470, 600, False), ('1F', 690, 905, False)):
        a, b = mapper(0, y1)[1], mapper(0, y2)[1]
        col = GOLD if hl else '#8a8fa3'
        s += f'<rect x="{x}" y="{a:.1f}" width="6" height="{b - a:.1f}" rx="3" fill="{col}" opacity="{.95 if hl else .6}"/>'
        s += T(x + 16, (a + b) / 2 + 10, label, 30, col, NUM, 700, 'start')
        if hl:
            s += T(x + 16, (a + b) / 2 + 40, 'お店', 20, GOLD, JP, 700, 'start')
    return s


def wrap(text, n):
    """n 文字ほどで折り返す。なるべく「／」「、」「）」の後ろで折り、英数字の途中では折らない。"""
    out, rest = [], text
    while len(rest) > n:
        cut = max((rest.rfind(c, 0, n + 1) + 1 for c in '／、）。'), default=0)
        if cut < n * .5:
            cut = n
            while cut > 1 and rest[cut - 1].isascii() and rest[cut - 1].isalnum() and rest[cut].isascii() and rest[cut].isalnum():
                cut -= 1
        out.append(rest[:cut])
        rest = rest[cut:]
    return out + [rest] if rest else out


# ---- 今のようす（前の提案と同じ絵） ---------------------------------------------------------
def scene_now():
    world = building() + people(820) + pole_and_wires()
    vb = ' '.join(map(str, VB))
    over = floor_tags(o)
    x3, y3 = o(800, 320)
    over += callout(x3, y3, 230, 180, ['3階がお店。でも外からは気づけない', '中は見えず、窓は電線にも隠れる'], 'start')
    xe, ye = o(1195, 800)
    over += callout(xe, ye, 1575, 520, ['入口はこのガラス扉', '隣のお店の扉と並び、わかりにくい'], 'end')
    xb, yb = o(1376, 770)
    over += callout(xb, yb, 1575, 760, ['今の看板は、案内板の', '3階の小さなプレートだけ'], 'end')
    over += chrome('', '今のようす（夜）', '3階にバーがあること、入口がどこかが、ビルの前から伝わっていない',
                   '今のようす（イラスト）　ストリートビュー（2024年11月）の建物をもとに描き起こしたもの')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000">{DEFS}'
            f'<svg x="0" y="0" width="1600" height="1000" viewBox="{vb}" preserveAspectRatio="xMidYMid slice">{world}</svg>{over}</svg>')


# ---- 置いたイメージ（左: 建物と入口、右: スタンドのまわりを拡大） --------------------------------
def place_svg(pr):
    world = building() + people(975) + place_stand(pr) + pole_and_wires()
    vb = ' '.join(f'{v:.2f}' for v in PV)
    body = f'<rect width="1600" height="1000" fill="#0b0d14"/>'
    body += f'<svg x="0" y="0" width="900" height="1000" viewBox="{vb}" preserveAspectRatio="xMidYMid slice">{world}</svg>'
    over = floor_tags(po)
    # 右の拡大
    x, y, w, h = 916, 134, 668, 806
    zx, zy, zw, zh = x + 14, y + 84, w - 28, h - 98
    vh = 112
    vw = vh * zw / zh
    vy = G - STAND_H * S - (vh - STAND_H * S) * .55
    over += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="#0b0d14" stroke="{GOLD}" stroke-width="1.5"/>'
    over += T(x + 20, y + 38, '拡大：入口のガラス扉の横', 23, '#fff', JP, 700, 'start')
    over += T(x + 20, y + 68, '光るスタンド（A1）に、このポスターを入れたところ', 18, '#c9cad3', JP, 500, 'start')
    over += f'<clipPath id="zoomClip"><rect x="{zx}" y="{zy}" width="{zw}" height="{zh}" rx="10"/></clipPath>'
    over += (f'<g clip-path="url(#zoomClip)"><svg x="{zx}" y="{zy}" width="{zw}" height="{zh}" '
             f'viewBox="{CX - 4 - vw / 2:.2f} {vy:.2f} {vw:.2f} {vh:.2f}" preserveAspectRatio="xMidYMid slice">{world}</svg></g>')
    over += f'<rect x="{zx}" y="{zy}" width="{zw}" height="{zh}" rx="10" fill="url(#vignette)"/>'
    over += f'<rect x="{zx + 12}" y="{zy + 12}" width="66" height="32" rx="8" fill="#000" opacity=".6"/>' + T(zx + 45, zy + 34, '拡大', 18, GOLD_L, JP, 700)
    sx, sy = po(CX + STAND_W * S / 2 + 1, G - STAND_H * S * .62)
    over += f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{x}" y2="{y + h / 2}" stroke="{GOLD}" stroke-width="2" opacity=".85"/><circle cx="{sx:.1f}" cy="{sy:.1f}" r="5" fill="{GOLD}"/>'
    over += chrome(pr['no'], pr['name'], pr['catch'], '置いたイメージ（イラスト・夜）　ビルの敷地の中、入口のガラス扉の横に置いたところ')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000">{DEFS}{body}{over}</svg>'


# ---- デザイン（ポスターの全体） ----------------------------------------------------------
SHEET = (1200, 1800)


def sheet_svg(pr):
    W, H = SHEET
    k = 1060 / PW
    x0, y0 = 70, 60
    body = f'<rect width="{W}" height="{H}" fill="url(#bgDesign)"/><rect width="{W}" height="{H}" fill="url(#grid)"/>'
    body += f'<rect x="{x0 + 10}" y="{y0 + 18}" width="{PW * k}" height="{PH * k}" fill="#000" opacity=".55" filter="url(#softer)"/>'
    body += f'<g transform="translate({x0},{y0}) scale({k:.5f})">{poster(pr)}</g>'
    y = y0 + PH * k + 40
    body += f'<rect x="{x0}" y="{y}" rx="12" width="104" height="50" fill="{GOLD}"/>' + T(x0 + 52, y + 35, '案' + pr['no'], 28, '#1a1408', JP, 700)
    body += T(x0 + 124, y + 37, pr['name'], 36, '#fff', JP, 700, 'start')
    body += T(x0, y + 92, f'差し込むポスター（A1・59.4 × 84.1cm）のデザイン案　{pr["style"]}', 22, '#c9cad3', JP, 500, 'start')
    note = '「〇〇〇」の値段は、決まったら入れます。' if any(x['tbd'] for x in PRICES.values()) or CHARGE_AMT.count('〇') else ''
    body += T(x0, y + 128, note + '写真はお店の写真です（印刷の前に撮り直すと、もっときれいになります）。', 20, '#9ea3b2', JP, 500, 'start')
    body += T(W - 70, H - 30, 'ダイニングバー XⅢ クロスリー', 18, GOLD, JP, 700, 'end')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{DEFS}{body}</svg>'


def thumb_svg(pr):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{PW}" height="{PH}" viewBox="0 0 {PW} {PH}">{DEFS}{poster(pr)}</svg>'


# ---- スタンドの大きさ（正面・横・たたんだところ・人） --------------------------------------------
def dim_h(x1, x2, y, label, col='#aeb3c2'):
    return (f'<g stroke="#8d93a3" stroke-width="1.5"><line x1="{x1}" x2="{x2}" y1="{y}" y2="{y}"/><line x1="{x1}" x2="{x1}" y1="{y - 8}" y2="{y + 8}"/>'
            f'<line x1="{x2}" x2="{x2}" y1="{y - 8}" y2="{y + 8}"/></g>' + T((x1 + x2) / 2, y + 28, label, 19, col, JP, 700))


def dim_v(x, y1, y2, label, side='left', col='#aeb3c2'):
    tx = x - 16 if side == 'left' else x + 16
    return (f'<g stroke="#8d93a3" stroke-width="1.5"><line x1="{x}" x2="{x}" y1="{y1}" y2="{y2}"/><line x1="{x - 8}" x2="{x + 8}" y1="{y1}" y2="{y1}"/>'
            f'<line x1="{x - 8}" x2="{x + 8}" y1="{y2}" y2="{y2}"/></g>'
            f'<text x="{tx}" y="{(y1 + y2) / 2}" font-family="{JP}" font-size="19" font-weight="700" fill="{col}" text-anchor="middle" '
            f'transform="rotate(-90 {tx} {(y1 + y2) / 2})">{esc(label)}</text>')


def person(x, base, k):
    h = 1700 * k
    u = h / 17
    s = (f'<g fill="#5f6577"><circle cx="{x}" cy="{base - h + u * 1.1}" r="{u * 1.1}"/>'
         f'<path d="M{x - u * 1.6} {base - h + u * 2.6} Q{x} {base - h + u * 2.2} {x + u * 1.6} {base - h + u * 2.6} '
         f'L{x + u * 2} {base - h + u * 9} L{x + u * 1.2} {base - h + u * 9} L{x + u * 1} {base} L{x + u * .2} {base} '
         f'L{x} {base - h + u * 10} L{x - u * .2} {base} L{x - u * 1} {base} L{x - u * 1.2} {base - h + u * 9} '
         f'L{x - u * 2} {base - h + u * 9} Z"/></g>')
    return s + T(x, base + 36, '人（170cm）', 19, '#aeb3c2', JP, 700)


def stand_figure_svg():
    W, H, base, k = 1600, 1000, 846, .4
    body = f'<rect width="{W}" height="{H}" fill="url(#bgDesign)"/><rect width="{W}" height="{H}" fill="url(#grid)"/>'
    body += f'<line x1="40" x2="{W - 40}" y1="{base}" y2="{base}" stroke="#4a4f5c" stroke-width="3"/>'
    body += person(110, base, k)
    # 正面（ポスターの入る所は斜線で）
    x0 = 250
    blank = (f'<rect width="{PW}" height="{PH}" fill="#2a2f3a"/><rect width="{PW}" height="{PH}" fill="url(#{"hatch"})"/>'
             + T(PW / 2, PH / 2 - 20, 'A1 のポスター', 52, '#f4dfa8', JP, 700) + T(PW / 2, PH / 2 + 50, '59.4 × 84.1cm', 46, '#f4dfa8', NUM, 600))
    body += '<defs><pattern id="hatch" width="24" height="24" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" x2="0" y1="0" y2="24" stroke="#fff" stroke-opacity=".07" stroke-width="10"/></pattern></defs>'
    body += f'<g transform="translate({x0},{base - STAND_H * k}) scale({k})">{stand_svg(blank, lit=False, cord=False)}</g>'
    body += dim_h(x0, x0 + STAND_W * k, base + 34, '幅 64cm')
    body += dim_v(x0 - 26, base - STAND_H * k, base, '高さ 118.5cm')
    body += dim_v(x0 + STAND_W * k + 26, base - STAND_H * k, base - STAND_H * k + BOARD_H * k, 'ボード面 88.4cm', 'right')
    body += T(x0 + STAND_W * k / 2, base - STAND_H * k - 22, '正面', 24, '#fff', JP, 700)
    # 横（A の形）
    x1, top = 690, base - STAND_H * k
    d = STAND_D * k
    body += f'<path d="M{x1} {base} L{x1 + d * .5} {top}" stroke="#d6dade" stroke-width="12" stroke-linecap="round"/>'
    body += f'<path d="M{x1 + d} {base} L{x1 + d * .5} {top}" stroke="#a9afb7" stroke-width="7" stroke-linecap="round"/>'
    body += f'<path d="M{x1 + d * .14} {base - 150} L{x1 + d * .86} {base - 150}" stroke="#7d838c" stroke-width="3" stroke-dasharray="6 5"/>'
    body += f'<circle cx="{x1 + d * .5}" cy="{top}" r="7" fill="#d6dade"/>'
    body += dim_h(x1, x1 + d, base + 34, '奥行 49cm')
    body += T(x1 + d / 2, top - 22, '横から', 24, '#fff', JP, 700)
    # たたんだところ
    x2 = 950
    fh = 1225 * k
    body += f'<rect x="{x2}" y="{base - fh}" width="{60 * k}" height="{fh}" rx="2" fill="url(#metal)"/>'
    body += dim_v(x2 + 60 * k + 24, base - fh, base, 'たたむと 高さ 122.5cm', 'right')
    body += T(x2 + 12, base + 34, '厚さ 6cm', 19, '#aeb3c2', JP, 700)
    body += T(x2 + 12, base - fh - 22, 'たたむと', 24, '#fff', JP, 700)
    # 説明
    px = 1160
    facts = [('光る', ['中の LED パネルが、', 'ポスターを後ろから照らす']), ('電源', ['コンセントにつなぐ', '（AC アダプター）']),
             ('入れ替え', ['表の枠を開けて、', 'A1 のポスターを差し込む']), ('外に置ける', ['ポスターは水に強いもの', '（耐水）にする']),
             ('値段', [f'{DATA["stand"]["price"]}（税込・送料無料）'])]
    body += f'<rect x="{px}" y="200" width="400" height="{70 + 100 * len(facts)}" rx="18" fill="#0b0d13" opacity=".75" stroke="#2c303b"/>'
    for i, (a, lines) in enumerate(facts):
        yy = 252 + i * 100
        body += T(px + 28, yy, a, 19, GOLD, JP, 700, 'start')
        for li, line in enumerate(lines):
            body += T(px + 28, yy + 32 + li * 28, line, 21, '#f2f2f5', JP, 500, 'start')
    over = chrome('', 'スタンドの大きさ', f'{DATA["stand"]["shop"]}の{DATA["stand"]["name"]}（人と同じ縮尺）',
                  '大きさは販売ページの値（幅64 × 奥行49 × 高さ118.5cm、ボード面 64 × 88.4cm）', foot='ダイニングバー XⅢ クロスリー｜入口の置き看板')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{DEFS}{body}{over}</svg>'


# ---- 書き出し ---------------------------------------------------------------------
def render(b, svg, name, tmp, size=(1600, 1000), dsf=1.5, web=(1200, 750), jpg=True):
    """SVG を Edge で画像にする。jpg は保存用（大きい）、webp はページに出す用（小さい）。"""
    w, h = size
    page = tmp / 'render.html'
    page.write_text('<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#000}svg{display:block}</style>'
                    f'</head><body>{svg}</body></html>', encoding='utf-8')
    b.open(page.as_uri(), {'width': w, 'height': h, 'deviceScaleFactor': dsf, 'mobile': False})
    b.wait(1.0)
    r = b.call('Page.captureScreenshot', {'format': 'png', 'clip': {'x': 0, 'y': 0, 'width': w, 'height': h, 'scale': 1}})
    im = Image.open(io.BytesIO(base64.b64decode(r['data']))).convert('RGB')
    if jpg:
        im.save(OUT / f'{name}.jpg', 'JPEG', quality=86, optimize=True, progressive=True)
    im.resize(web, Image.LANCZOS).save(OUT / f'{name}.webp', 'WEBP', quality=82, method=6)
    if b.errors:
        print('  エラー:', b.errors[:3])
    return im.size


def main():
    only = set(sys.argv[1].split(',')) if len(sys.argv) > 1 else None
    OUT.mkdir(parents=True, exist_ok=True)
    if not only:
        for f in OUT.glob('*'):          # 前の画像（前の提案の看板など）を残さない
            f.unlink()
    tmp = Path(tempfile.mkdtemp())
    b = shoot.Browser()
    try:
        if not only or '00' in only:
            print('00 今のようす', render(b, scene_now(), 'sign-00-now', tmp))
        if not only or 'stand' in only:
            print('スタンドの大きさ', render(b, stand_figure_svg(), 'sign-stand', tmp))
        for pr in DATA['proposals']:
            if only and pr['no'] not in only:
                continue
            base = f'sign-{pr["no"]}-{pr["id"]}'
            print(pr['no'], pr['name'],
                  render(b, place_svg(pr), f'{base}-place', tmp),
                  render(b, sheet_svg(pr), f'{base}-poster', tmp, size=SHEET, dsf=1.2, web=(800, 1200)),
                  render(b, thumb_svg(pr), f'{base}-thumb', tmp, size=(PW, PH), dsf=1, web=(480, 680), jpg=False))
    finally:
        b.close()
    # まとめてダウンロードする ZIP（画像はすでに JPEG なので圧縮しない）。古い名前の ZIP は消す。
    for old in ZIP.parent.glob('xiii-sign-*.zip'):
        if old != ZIP:
            old.unlink()
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_STORED) as z:
        for f in sorted(OUT.glob('sign-*.jpg')):
            z.write(f, f'xiii-sign-posters/{f.name}')
    print('ZIP', ZIP.name, f'{ZIP.stat().st_size // 1024} KB')


if __name__ == '__main__':
    main()
