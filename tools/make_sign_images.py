"""看板の提案（1階入口の光る置き看板に差し込むポスター・10案）のイメージ画像を作る。

  python -I -X utf8 tools/make_sign_images.py [final,pdf,fonts,font03,where,00,stand,01 …]   … 名前を渡すと、その画像だけ作り直す
      （final は仕上がりの画像、pdf は印刷用の PDF、fonts は書体の案すべて、font03 は書体の案03だけ、
        where は書体を変える所の目印、00 は今のようす、stand はスタンドの大きさ、01〜10 はそれまでの10案）

スタンドは決まっている: モノタロウの LEDパネルA型スタンド 片面（A1）。幅640×奥行490×高さ1185mm、ボード面 640×884mm。
枠の色はブラック（2026-10-31 にお店が決めた。signs.json の stand.frame）。
その中に差し込むポスター（A1・594×841mm）の仕上がりを描く（2026-11-02 にお店が決めた: 案09をもとに、
タバコは丸いシールで少し控えめに、Instagram の QR コードを足す）。仕上がりは、置いたイメージ・デザイン・一覧用の画像と、
印刷用の PDF（A1 のまわりに塗り足し 3mm）。それまでの10案（案06をもとにした仕上げの10案）は、参考にデザインと一覧用の画像だけ作る。
ほかに「今のようす」と「スタンドの大きさ」。QR コードの中身は tools/qr-instagram.txt（tools/make_qr.py で作る）。

書体の案（2026-11-03 お店の返事: 丸で囲んだ所＝NEW OPEN の札と、値段の一覧の書体の候補がほしい）は、仕上がりのその所の
書体だけを変えたもの（signs.json の fonts）。書体は Google Fonts の無料の書体（SIL Open Font License。看板・印刷に使ってよい）で、
ポスターに使う字だけを Google Fonts から取ってきて（tools/fonts/cache に残す。リポジトリには入れない）、SVG に埋め込んで描く。
仕上がりと印刷用の PDF の書体は signs.json の final の font（書体の案の番号。00 はもとの書体＝パソコンの書体）。
同じ日にお店が 01「上品で細身」に決めた（確定版）。

文字や値段は signs.json と site.json から読む（値段の計算は build.py の sign_prices と同じもの）。
値段が決まったら site.json を直して、この画像とページを作り直す。
建物はストリートビューの写真を加工せず、イラストで描き起こす（Google の画像は加工して公開できないため）。
SVG で描き、画面なしの Edge で書き出す。ページ用の小さい WebP も作る。
"""
import base64
import hashlib
import html
import io
import json
import math
import os
import re
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))
import shoot  # noqa: E402
import build  # noqa: E402  値段の計算（sign_prices・sign_charge）をページと同じにするため

IMG = ROOT / 'docs' / 'assets' / 'img'
OUT = ROOT / 'docs' / 'signs' / 'img'
PDF = ROOT / 'docs' / 'signs' / 'xiii-poster-a1-print.pdf'
QR_FILE = ROOT / 'tools' / 'qr-instagram.txt'
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
INSTA = SITE['instagram']
FOOT = f'OPEN {HOURS} ／ {CLOSED}　Instagram {INSTA}'
SMOKE_T, SMOKE_S, SMOKE_N = (DATA['smoke'][k] for k in ('title', 'sub', 'note'))   # タバコ吸えます／店内喫煙可／20歳未満…
OPEN_EN, OPEN_JP, OPEN_D = (DATA['open'][k] for k in ('en', 'jp', 'date'))         # NEW OPEN／2026年7月オープン／2026年7月
PRICES = {x['id']: x for x in build.sign_prices()}
CHARGE_PER, CHARGE_AMT, _ = build.sign_charge()
CHARGE = f'テーブルチャージ　{CHARGE_PER} {CHARGE_AMT}'


def _qr():
    """Instagram の QR コードのます目（True＝黒）。中身が site.json の instagram_url と違えば止める。"""
    head, *rows = QR_FILE.read_text(encoding='utf-8').split('\n')
    if head.split('\t')[0] != SITE['instagram_url']:
        raise SystemExit('QR コードの中身が site.json の instagram_url と違います（tools/make_qr.py で作り直してください）')
    return [[c == '1' for c in r] for r in rows if r]


QR = _qr()

# ---- スタンド（mm）。ボード面 640×884 の中に A1 のポスター（594×841）が入る -------------------
PW, PH = 594, 841
STAND_W, STAND_H, STAND_D, BOARD_H = 640, 1185, 490, 884
LIP = 32                               # 表の枠の幅（ポスターのふちに 9〜10mm かかる）
# 枠の色。ブラックは夜の暗い背景に溶けないよう、ふちを少し明るくして形を見せる。
FRAME = DATA['stand'].get('frame', 'シルバー')
if FRAME == 'ブラック':
    METAL = ('#0c0d10', '#383b42', '#1b1d22', '#2e3137', '#0a0b0e')   # 横の明暗（左の影・光・真ん中・光・右の影）
    METAL_V = ('#3b3e45', '#141519')                                  # 縦の明暗（上・下）
    RIM_IN, RIM_OUT = '#4b5059', '#5d626d'                             # 窓のふち・外のふち
    SIDE = ('#5d626d', '#202227', '#16171b')                          # 横から見た図: ふちの色・前の脚・後ろの脚
else:
    METAL = ('#8b929b', '#e2e6eb', '#c2c7ce', '#d9dde2', '#848a93')
    METAL_V = ('#e6e9ed', '#9aa0a8')
    RIM_IN, RIM_OUT = '#5b6068', '#6c727b'
    SIDE = ('', '#d6dade', '#a9afb7')

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


_BAHN = Path(r'C:\Windows\Fonts\bahnschrift.ttf')
_BAHN_FONT = ImageFont.truetype(str(_BAHN), 100) if _BAHN.exists() else None


def text_w(s, size, fam=JPB):
    """文字の幅（点線の長さを決めるのに使う）。英語の書体（NUM＝Bahnschrift）は実際の書体で測る。ほかは目安（tw）。"""
    if fam == NUM and _BAHN_FONT:
        return _BAHN_FONT.getlength(s) / 100 * size
    return tw(s, size)


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
<linearGradient id="metal" x1="0" x2="1"><stop offset="0" stop-color="{METAL[0]}"/><stop offset=".22" stop-color="{METAL[1]}"/><stop offset=".5" stop-color="{METAL[2]}"/><stop offset=".8" stop-color="{METAL[3]}"/><stop offset="1" stop-color="{METAL[4]}"/></linearGradient>
<linearGradient id="metalV" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{METAL_V[0]}"/><stop offset="1" stop-color="{METAL_V[1]}"/></linearGradient>
<radialGradient id="panelLit" cx=".5" cy=".42" r=".75"><stop offset="0" stop-color="#fff" stop-opacity=".2"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
<radialGradient id="lamp" cx="1" cy=".62" r=".75"><stop offset="0" stop-color="#ffd9a0" stop-opacity=".30"/><stop offset="1" stop-color="#ffd9a0" stop-opacity="0"/></radialGradient>
<radialGradient id="lobbySpill" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#eaf2ff" stop-opacity=".45"/><stop offset="1" stop-color="#eaf2ff" stop-opacity="0"/></radialGradient>
<radialGradient id="spill" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fff0cf" stop-opacity=".75"/><stop offset="1" stop-color="#fff0cf" stop-opacity="0"/></radialGradient>
<radialGradient id="vignette" cx=".5" cy=".5" r=".72"><stop offset=".45" stop-color="#05060c" stop-opacity="0"/><stop offset="1" stop-color="#05060c" stop-opacity=".62"/></radialGradient>
<radialGradient id="bgDesign" cx=".5" cy=".4" r=".8"><stop offset="0" stop-color="#262a33"/><stop offset="1" stop-color="#101217"/></radialGradient>
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#fff" stroke-opacity=".035"/></pattern>
<filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="5"/></filter>
<filter id="softer" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="14"/></filter>
<filter id="pop" color-interpolation-filters="sRGB"><feComponentTransfer><feFuncR type="gamma" amplitude="1.04" exponent=".8"/><feFuncG type="gamma" amplitude="1.04" exponent=".8"/><feFuncB type="gamma" amplitude="1.04" exponent=".8"/></feComponentTransfer><feColorMatrix type="saturate" values="1.12"/></filter>
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


def rows_en(*ids):
    """値段の一覧（英語の表記。仕上がりのポスター）。"""
    return [(PRICES[i]['en'], PRICES[i]['en_value']) for i in ids]


def plist(x, y, w, items, size, lab, val, lead=None, lh=None, fam=JPB, wl=500, wv=700, extra='', fam_l=None):
    """値段の一覧（名前は左、値段は右。あいだを点線でつなぐ）。fam_l は名前だけ別の書体にするとき。"""
    lh = lh or size * 1.55
    s = ''
    for i, (k, v) in enumerate(items):
        yy = y + i * lh
        s += T(x, yy, k, size, lab, fam_l or fam, wl, 'start', extra=extra)
        s += T(x + w, yy, v, size, val, fam, wv, 'end', extra=extra)
        if lead:
            a, b = x + text_w(k, size, fam_l or fam) + size * .45, x + w - tw(v, size) - size * .45
            if b - a > size:
                s += (f'<line x1="{a:.1f}" x2="{b:.1f}" y1="{yy - size * .32:.1f}" y2="{yy - size * .32:.1f}" stroke="{lead}" '
                      f'stroke-width="{size * .1:.2f}" stroke-dasharray="0 {size * .34:.2f}" stroke-linecap="round"/>')
    return s


# ---- 書体の案（丸で囲んだ所＝NEW OPEN の札と、値段の一覧・営業時間の書体） ------------------------------------
# 2026-11-03 お店の返事: その所の書体の候補がほしい。書体は Google Fonts の無料の書体（SIL Open Font License）。
# ポスターに使う字だけを Google Fonts から取ってきて（tools/fonts/cache に残す）、SVG に埋め込んで描く。
# 00（もとの書体）は、パソコンに入っている書体（Bahnschrift・Noto Sans JP）。
FONT_CACHE = ROOT / 'tools' / 'fonts' / 'cache'
WIN_FONTS = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Fonts'
LOCAL_FONTS = {'Bahnschrift': 'bahnschrift.ttf', 'Noto Sans JP': 'NotoSansJP-VF.ttf'}
BAND_PAD = 2.1     # NEW OPEN の札の右の余白（もとの書体で、札の幅が前と同じ 356 になる値）


def _type_text():
    """Google Fonts から取ってくる字（英数字すべてと、丸で囲んだ所に使う字）。"""
    s = ''.join(chr(c) for c in range(0x20, 0x7f)) + OPEN_EN + OPEN_JP + DATA['charge_en'] + CHARGE_AMT
    s += f'OPEN {HOURS} ／ {CLOSED}' + ''.join(x['en'] + x['en_value'] for x in PRICES.values())
    s += ''.join(t.get('open', {}).get('text', '') for t in DATA['fonts']['list'])
    return ''.join(sorted(set(s)))


TYPE_TEXT = _type_text()


def _get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'make_sign_images.py (crossley)'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


class Face:
    """書体1つ（1つの太さ）。css は SVG で使う名前。字の幅は、書体のファイルを PIL で開いて測る。"""

    def __init__(self, family, weight, italic=False):
        self.family, self.weight, self.italic = family, weight, italic
        self.local = family in LOCAL_FONTS
        slug = re.sub(r'[^a-z0-9]', '', family.lower())
        self.css = family if self.local else f'x-{slug}-{weight}{"i" if italic else ""}'
        self.path = WIN_FONTS / LOCAL_FONTS[family] if self.local else None
        self._pil = self._cmap = None
        self.delta = {}     # 数字を高さのそろった形（lnum）にしたときの、字の幅の差（大きさ 100 のとき）

    @property
    def w(self):
        """SVG に書く太さ。取ってきた書体は1つの太さだけなので 400（太さを足して描かれないように）。"""
        return self.weight if self.local else 400

    def fetch(self):
        """ポスターに使う字だけを Google Fonts から取ってくる（前に取ったものがあれば、それを使う）。"""
        if self.path:
            return self
        key = hashlib.sha1(TYPE_TEXT.encode()).hexdigest()[:10]
        path = FONT_CACHE / f'{self.css}-{key}.ttf'
        if not path.exists():
            axes = f'ital,wght@1,{self.weight}' if self.italic else f'wght@{self.weight}'
            css = _get('https://fonts.googleapis.com/css2?family=' + urllib.parse.quote_plus(self.family) + ':' + axes
                       + '&text=' + urllib.parse.quote(TYPE_TEXT)).decode()
            m = re.search(r"url\((https://[^)]+)\)\s*format\('truetype'\)", css)
            if not m:
                raise SystemExit(f'書体を取ってこられません: {self.family} {self.weight}')
            FONT_CACHE.mkdir(parents=True, exist_ok=True)
            path.write_bytes(_get(m.group(1)))
        self.path = path
        return self

    @property
    def pil(self):
        if self._pil is None:
            f = ImageFont.truetype(str(self.fetch().path), 100)
            if self.local:      # 太さを変えられる書体（パソコンの書体）は、使う太さにして測る
                try:
                    f.set_variation_by_axes([self.weight if a.get('name') in (b'Weight', 'Weight') else a['default']
                                             for a in f.get_variation_axes()])
                except OSError:
                    pass
            self._pil = f
        return self._pil

    def has(self, ch):
        if self._cmap is None:
            with TTFont(str(self.fetch().path), lazy=True) as t:
                self._cmap = set(t.getBestCmap())
        return ord(ch) in self._cmap

    def use_lnum(self):
        """数字を、高さのそろった形（lnum）で描くときの幅を測れるようにする（PIL は書体の切り替えをしないため、差を足す）。"""
        if self.local or self.delta:
            return
        with TTFont(str(self.fetch().path), lazy=True) as t:
            cmap, hmtx, upm = t.getBestCmap(), t['hmtx'], t['head'].unitsPerEm
            subs = {}
            gsub = t['GSUB'].table if 'GSUB' in t else None
            for fr in (gsub.FeatureList.FeatureRecord if gsub else []):
                if fr.FeatureTag == 'lnum':
                    for i in fr.Feature.LookupListIndex:
                        for st in gsub.LookupList.Lookup[i].SubTable:
                            subs.update(getattr(getattr(st, 'ExtSubTable', st), 'mapping', None) or {})
            for ch in '0123456789':
                g = cmap.get(ord(ch))
                if g in subs:
                    self.delta[ch] = (hmtx[subs[g]][0] - hmtx[g][0]) / upm * 100

    def rule(self):
        """SVG に埋め込む @font-face（パソコンの書体は要らない）。"""
        if self.local:
            return ''
        data = base64.b64encode(self.fetch().path.read_bytes()).decode()
        return f"@font-face{{font-family:'{self.css}';src:url(data:font/ttf;base64,{data}) format('truetype')}}"


_FACES = {}


def face(family, weight, italic=False):
    key = (family, int(weight), bool(italic))
    if key not in _FACES:
        _FACES[key] = Face(*key)
    return _FACES[key]


class Stack:
    """字を描く書体の並び（前の書体にない字は、次の書体で描く。ブラウザと同じ）。"""

    def __init__(self, *faces):
        self.faces = faces
        self.css = ','.join(f"'{f.css}'" for f in faces)
        self.w = faces[0].w

    def width(self, s, size, ls=0):
        total, run, cur = 0.0, '', None
        for ch in s:
            f = next((f for f in self.faces if f.has(ch)), self.faces[-1])
            total += f.delta.get(ch, 0)
            if f is not cur and run:
                total += cur.pil.getlength(run)
                run = ''
            cur = f
            run += ch
        if run:
            total += cur.pil.getlength(run)
        return total / 100 * size + ls * len(s)


def plist_s(x, y, w, items, size, lab, val, lead, s_lab, s_val, lh=None):
    """値段の一覧（書体の案の形。名前と値段の幅を実際の書体で測って、あいだを点線でつなぐ）。"""
    lh = lh or size * 1.55
    s = ''
    for i, (k, v) in enumerate(items):
        yy = y + i * lh
        s += T(x, yy, k, size, lab, s_lab.css, s_lab.w, 'start')
        s += T(x + w, yy, v, size, val, s_val.css, s_val.w, 'end')
        a, b = x + s_lab.width(k, size) + size * .45, x + w - s_val.width(v, size) - size * .45
        if b - a > size:
            s += (f'<line x1="{a:.1f}" x2="{b:.1f}" y1="{yy - size * .32:.1f}" y2="{yy - size * .32:.1f}" stroke="{lead}" '
                  f'stroke-width="{size * .1:.2f}" stroke-dasharray="0 {size * .34:.2f}" stroke-linecap="round"/>')
    return s


class Type:
    """書体の案1つ（signs.json の fonts の1つ）。丸で囲んだ所（NEW OPEN の札・値段の一覧・営業時間）に使う書体。
    en は英語と数字、ja は日本語（どちらも [書体, 太い字の太さ, ふつうの字の太さ]）。英語の書体にない字（〜・年など）は日本語の書体で描く。"""

    def __init__(self, t):
        en, ja, op = t['en'], t['ja'], t.get('open', {})
        self.en_b, self.en_r = face(en[0], en[1]), face(en[0], en[2])
        self.ja_b, self.ja_r = face(ja[0], ja[1]), face(ja[0], ja[2])
        lab = t.get('label')                       # 値段の名前だけ別の書体にするとき（[書体, 太さ, 斜体か]）
        self.lab = face(*lab) if lab else self.en_r
        self.open_f = face(op['family'], op.get('weight', 400)) if 'family' in op else self.en_b
        self.open_size, self.open_ls, self.open_text = op.get('size', 25), op.get('ls', 5), op.get('text', OPEN_EN)
        self.ja_size = t.get('ja_size', 18)
        self.k = t.get('scale', 1)                  # 値段の一覧の字の大きさ（書体によって見た目の大きさが違うので合わせる）
        self.kh = t.get('hours_scale', self.k)
        self.upper, self.glow, self.lnum = t.get('upper', False), t.get('glow'), t.get('lnum', False)
        self.s_open, self.s_ja = Stack(self.open_f, self.ja_b), Stack(self.ja_b)
        self.s_charge, self.s_label = Stack(self.en_b, self.ja_b), Stack(self.lab, self.ja_r)
        self.s_price = Stack(self.ja_b) if t.get('price') == 'ja' else Stack(self.en_b, self.ja_b)
        self.s_hours = Stack(self.ja_r) if t.get('hours') == 'ja' else Stack(self.en_r, self.ja_r)

    def tx(self, s):
        return s.upper() if self.upper else s

    def defs(self, p):
        """書体の埋め込みと、光る効果（ネオン。字のまわりに金色の光をぼかして重ねる）。"""
        stacks = (self.s_open, self.s_ja, self.s_charge, self.s_label, self.s_price, self.s_hours)
        faces = {id(f): f for st in stacks for f in st.faces}
        if self.lnum:       # 数字を高さのそろった形に（細身の書体は、数字の高さがそろっていない形が元になっているため）
            for f in (self.en_b, self.en_r, self.lab):
                f.use_lnum()
        css = ''.join(f.rule() for f in faces.values())
        s = f'<style>{css}</style>' if css else ''
        if self.glow:
            s += (f'<filter id="{p}-glow" x="-5%" y="-30%" width="110%" height="160%">'
                  f'<feGaussianBlur in="SourceAlpha" stdDeviation="{self.glow}" result="b"/>'
                  '<feFlood flood-color="#ffb347" flood-opacity=".8"/><feComposite in2="b" operator="in" result="g"/>'
                  '<feMerge><feMergeNode in="g"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
        return s

    def band_width(self):
        t = self.tx(self.open_text)
        return 14 + self.s_open.width(t, self.open_size, self.open_ls) + 14 + self.s_ja.width(OPEN_JP, self.ja_size) + BAND_PAD

    def band(self, x, y, h, fg):
        """NEW OPEN の札（金の地に「NEW OPEN　2026年7月オープン」）。札の幅は字の幅に合わせ、字の上下の真ん中を札の真ん中にそろえる。"""
        t = self.tx(self.open_text)
        _, y0, _, y1 = self.open_f.pil.getbbox(t, anchor='ls')
        base = y + h / 2 - (y0 + y1) / 2 / 100 * self.open_size
        return (f'<rect x="{x}" y="{y}" width="{self.band_width():.1f}" height="{h}" rx="6" fill="{GOLD}"/>'
                f'<text x="{x + 14}" y="{base:.1f}" text-anchor="start" fill="{fg}">'
                f'<tspan font-family="{self.s_open.css}" font-weight="{self.s_open.w}" font-size="{self.open_size}" '
                f'letter-spacing="{self.open_ls}">{esc(t)}</tspan>'
                f'<tspan font-family="{self.s_ja.css}" font-weight="{self.s_ja.w}" font-size="{self.ja_size}" dx="14">{esc(OPEN_JP)}</tspan></text>')

    def prices(self, p, x, w):
        """値段の目安（いちばん上にチャージ）と、その下の営業時間。"""
        k = self.k
        s = plist_s(x, 652, w, [(self.tx(DATA['charge_en']), self.tx(CHARGE_AMT))], 19 * k, GOLD_L, GOLD_L, '#7d6c48',
                    self.s_charge, self.s_price)
        s += plist_s(x, 690, w, [(self.tx(a), self.tx(b)) for a, b in rows_en('beer', 'whisky', 'cocktail', 'food', 'darts')],
                     18 * k, '#ebe5d8', GOLD_L, '#7d6c48', self.s_label, self.s_price, 25.5)
        if self.glow:
            s = f'<g filter="url(#{p}-glow)">{s}</g>'
        s += T(x - 2, 818, self.tx(f'OPEN {HOURS}') + f' ／ {CLOSED}', 13.5 * self.kh, '#bdb6a8', self.s_hours.css, self.s_hours.w, 'start')
        return f'<g style="font-variant-numeric:lining-nums">{s}</g>' if self.lnum else s


TYPES = {t['no']: Type(t) for t in DATA['fonts']['list']}
FINAL_TYPE = TYPES[DATA['final'].get('font', '00')]      # 仕上がりと印刷用の PDF の書体


# ---- 仕上げの10案（案06「3枚の写真で見せる」をもとに） -----------------------------------------
# お店の返事（2026-10-30）: 案06に決定。タバコが吸えることと「2026年7月 NEW OPEN」を目立たせる。
# 焼酎・テキーラは載せない。写真の上の説明（カウンター・テーブル席・ダーツ 1ゲーム ¥100）は入れない。
PHOTO3 = (('counter-dark', .6, .55), ('tables', .5, .62), ('darts', .48, .42))   # 写真3枚と、枠の真ん中に来る位置
RED = '#b3262d'


def line(y, x1=40, x2=554, color=GOLD, w=1.2, op=.7):
    return f'<line x1="{x1}" x2="{x2}" y1="{y}" y2="{y}" stroke="{color}" stroke-width="{w}" opacity="{op}"/>'


def head06(g, y=40):
    """案06の上の段: 左にロゴ、右に BAR と「このビルの 3F」。"""
    s = logo(168, y, 226)
    s += T(548, y + 72, 'BAR', 86, f'url(#{g})', SERIF, 700, 'end', ls=14)
    s += T(548, y + 136, '3F', 62, f'url(#{g})', NUM, 700, 'end')
    s += T(462, y + 130, 'このビルの', 22, WHITE, JPB, 700, 'end')
    return s


def head_small(g, y=34):
    """上の段（小さめ）: 左にロゴ、右に BAR と「このビルの 3F」。"""
    s = logo(150, y, 200)
    s += T(548, y + 62, 'BAR', 76, f'url(#{g})', SERIF, 700, 'end', ls=12)
    s += T(548, y + 116, '3F', 52, f'url(#{g})', NUM, 700, 'end')
    s += T(478, y + 111, 'このビルの', 19, WHITE, JPB, 700, 'end')
    return s


def photos_big2(p, y, hb, hs, x=40, w=514, gap=8):
    """大きい写真1枚と、小さい写真2枚（写真の説明の文字は入れない）。"""
    (n1, fx1, fy1), (n2, fx2, fy2), (n3, fx3, fy3) = PHOTO3
    ws = (w - gap) / 2
    s = ph(n1, x, y, w, hb, f'{p}-p1', fx1, fy1)
    s += ph(n2, x, y + hb + gap, ws, hs, f'{p}-p2', fx2, fy2)
    s += ph(n3, x + ws + gap, y + hb + gap, ws, hs, f'{p}-p3', fx3, fy3)
    return s


def cigarette(x, y, L, rot=-10, ember='#ff6a2b', filt=GOLD, paper='#f3eee4', smoke='#e9e2d4'):
    """火の付いたタバコの絵（火の先が左。x, y は火の先、L は長さ）。禁煙の印と間違えないよう、斜線や丸は付けない。"""
    h = L * .17
    s = f'<g transform="rotate({rot} {x} {y})">'
    s += f'<rect x="{x}" y="{y - h / 2:.2f}" width="{L * .7:.2f}" height="{h:.2f}" fill="{paper}"/>'
    s += f'<rect x="{x + L * .7:.2f}" y="{y - h / 2:.2f}" width="{L * .3:.2f}" height="{h:.2f}" rx="{h * .12:.2f}" fill="{filt}"/>'
    s += f'<g filter="url(#soft)" opacity=".9"><rect x="{x - h * .6:.2f}" y="{y - h * .7:.2f}" width="{h * .9:.2f}" height="{h * 1.4:.2f}" rx="{h * .5:.2f}" fill="{ember}"/></g>'
    s += f'<rect x="{x - h * .5:.2f}" y="{y - h / 2:.2f}" width="{h * .55:.2f}" height="{h:.2f}" rx="{h * .2:.2f}" fill="{ember}"/>'
    s += '</g>'
    sx, sy = x - h * .1, y - h * .9            # 煙（上へゆらゆら）
    s += (f'<path d="M{sx:.2f} {sy:.2f} c{-h * .8:.2f} {-h * .7:.2f} {h * .8:.2f} {-h * 1.1:.2f} 0 {-h * 1.8:.2f} '
          f's{h * .8:.2f} {-h * 1.1:.2f} 0 {-h * 1.8:.2f}" fill="none" stroke="{smoke}" stroke-width="{h * .2:.2f}" stroke-linecap="round" opacity=".8"/>')
    s += (f'<path d="M{sx + h * .7:.2f} {sy - h * .3:.2f} c{-h * .6:.2f} {-h * .6:.2f} {h * .6:.2f} {-h * .9:.2f} 0 {-h * 1.5:.2f}" '
          f'fill="none" stroke="{smoke}" stroke-width="{h * .15:.2f}" stroke-linecap="round" opacity=".55"/>')
    return s


def smoke_band(y, h=60, x=40, w=514, size=36, accent=GOLD, bg='#17151b', ember='#ff6a2b'):
    """「タバコ吸えます」の帯（左にタバコの絵、右に「店内喫煙可」）。"""
    L = h * 1.45
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{bg}" stroke="{accent}" stroke-width="1.6"/>'
    s += cigarette(x + 28, y + h * .66, L, ember=ember)
    s += T(x + 28 + L + 22, y + h / 2 + size * .36, SMOKE_T, size, WHITE, JPB, 900, 'start')
    s += T(x + w - 18, y + h / 2 + 6, SMOKE_S, 17, accent if accent != GOLD else GOLD_L, JPB, 700, 'end')
    return s


def smoke_badge(cx, cy, r, accent=GOLD):
    """丸いシール（「タバコ 吸えます」）。写真の上に貼ったように置く。"""
    s = f'<circle cx="{cx}" cy="{cy + 3}" r="{r + 3}" fill="#000" opacity=".5" filter="url(#soft)"/>'
    s += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#141217" stroke="{accent}" stroke-width="3"/>'
    s += f'<circle cx="{cx}" cy="{cy}" r="{r - 7}" fill="none" stroke="{accent}" stroke-width=".8"/>'
    s += cigarette(cx - r * .4, cy - r * .22, r * .82, rot=-8)
    s += T(cx, cy + r * .22, 'タバコ', r * .3, WHITE, JPB, 900)
    s += T(cx, cy + r * .56, '吸えます', r * .3, WHITE, JPB, 900)
    return s


def open_text(cx, y, en, jp, fg, gap=16, anchor='middle'):
    """「NEW OPEN　2026年7月オープン」（英語は大きく、日本語は小さく）。"""
    return (f'<text x="{cx}" y="{y:.1f}" text-anchor="{anchor}" fill="{fg}">'
            f'<tspan font-family="{NUM}" font-weight="700" font-size="{en}" letter-spacing="5">{OPEN_EN}</tspan>'
            f'<tspan font-family="{JPB}" font-weight="700" font-size="{jp}" dx="{gap}">{OPEN_JP}</tspan></text>')


def open_banner(y, h=40, x=40, w=514, bg=GOLD, fg='#141008'):
    """「NEW OPEN」の帯。"""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{bg}"/>'
            + open_text(x + w / 2, y + h * .71, round(h * .62, 1), round(h * .44, 1), fg))


def open_stamp(cx, cy, r, rot=-12, bg=GOLD, fg='#141008'):
    """丸いスタンプ（NEW OPEN・2026年7月）。"""
    s = f'<g transform="rotate({rot} {cx} {cy})">'
    s += f'<circle cx="{cx}" cy="{cy + 3}" r="{r + 2}" fill="#000" opacity=".5" filter="url(#soft)"/>'
    s += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{bg}"/>'
    s += f'<circle cx="{cx}" cy="{cy}" r="{r - 5}" fill="none" stroke="{fg}" stroke-width="1" stroke-dasharray="3 2.4"/>'
    s += T(cx, cy - r * .1, 'NEW', r * .42, fg, NUM, 700, ls=2)
    s += T(cx, cy + r * .3, 'OPEN', r * .42, fg, NUM, 700, ls=2)
    s += T(cx, cy + r * .6, OPEN_D, r * .2, fg, JPB, 700)
    return s + '</g>'


def open_corner(c=104, bw=46, bg=GOLD, fg='#141008'):
    """右上の角にかける斜めのリボン（NEW OPEN・2026年7月）。"""
    s = f'<g transform="translate({PW},0) rotate(45)">'
    s += f'<rect x="-300" y="{c - bw / 2}" width="600" height="{bw}" fill="#000" opacity=".45" filter="url(#soft)"/>'
    s += f'<rect x="-300" y="{c - bw / 2}" width="600" height="{bw}" fill="{bg}"/>'
    s += f'<path d="M-300 {c - bw / 2 + 4} H300 M-300 {c + bw / 2 - 4} H300" stroke="{fg}" stroke-width=".8" opacity=".55"/>'
    s += T(0, c + 1, OPEN_EN, 21, fg, NUM, 700, ls=3)
    s += T(0, c + 17, OPEN_D, 12.5, fg, JPB, 700)
    return s + '</g>'


def prices_inline(y, size=16, lh=24, lab='#ebe5d8', val=GOLD_L):
    """値段を2行に並べる（1行目: ビール・ウイスキー・カクテル、2行目: フード・ダーツ）。"""
    s = ''
    for i, ids in enumerate((('beer', 'whisky', 'cocktail'), ('food', 'darts'))):
        parts = []
        for j, (k, v) in enumerate(rows(*ids)):
            sep = f'<tspan fill="{lab}" opacity=".45" dx="{size * .6:.1f}">／</tspan>' if j else ''
            first = f' dx="{size * .6:.1f}"' if j else ''
            parts.append(f'{sep}<tspan fill="{lab}" font-weight="500"{first}>{esc(k)}</tspan>'
                         f'<tspan fill="{val}" font-weight="700" dx="{size * .35:.1f}">{esc(v)}</tspan>')
        s += f'<text x="297" y="{y + i * lh}" text-anchor="middle" font-family="{JPB}" font-size="{size}">{"".join(parts)}</text>'
    return s


def prices_cols(y, size=16.5, lh=24, lab='#ebe5d8', val=GOLD_L, lead='#7d6c48'):
    """値段を2列に並べる（左: ビール・ウイスキー・カクテル、右: フード・ダーツ）。"""
    return (plist(64, y, 212, rows('beer', 'whisky', 'cocktail'), size, lab, val, lead, lh)
            + plist(318, y, 212, rows('food', 'darts'), size, lab, val, lead, lh))


def pol(name, x, y, w, h, rot, cid, fx=.5, fy=.5):
    """白いふちの写真（説明の文字は入れない）とテープ。"""
    cx, cy = x + w / 2, y + h / 2
    s = f'<g transform="rotate({rot} {cx} {cy})">'
    s += f'<rect x="{x + 4}" y="{y + 6}" width="{w}" height="{h}" fill="#000" opacity=".55" filter="url(#soft)"/>'
    s += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#f3f0e8"/>'
    s += ph(name, x + 10, y + 10, w - 20, h - 42, cid, fx, fy)
    s += f'<rect x="{cx - 34}" y="{y - 12}" width="68" height="24" fill="#e9d9a6" opacity=".85" transform="rotate({-rot * 2} {cx} {y})"/>'
    return s + '</g>'


def bg_dark(p, g):
    return f'<defs>{gold_grad(g)}</defs><rect width="{PW}" height="{PH}" fill="#0c0b0e"/>'


def poster_base(p):
    """01 案06をそのまま直した形（NEW OPEN は金の帯、タバコは写真の下の帯）。"""
    g = f'{p}-g'
    s = bg_dark(p, g) + head06(g) + line(192)
    s += open_banner(200, 40)
    s += photos_big2(p, 250, 188, 138)
    s += smoke_band(598, 62)
    s += T(297, 684, SMOKE_N, 14.5, '#cfc8bb', JPB, 500)
    s += line(700, 60, 534, op=.5)
    s += T(297, 728, CHARGE, 20, GOLD_L, JPB, 700)
    s += prices_inline(756, 16)
    s += T(297, 808, FOOT, 12.5, '#bdb6a8', JPB, 500)
    return s


def poster_corner(p):
    """02 角のリボンと、丸いシール。"""
    g = f'{p}-g'
    s = bg_dark(p, g)
    s += logo(297, 38, 236)
    s += T(297, 222, 'BAR · 3F', 54, f'url(#{g})', NUM, 700, ls=8)
    s += T(297, 254, 'このビルの3階・エレベーターでどうぞ', 18, '#e6dfd0', JPB, 500)
    s += open_corner()
    s += photos_big2(p, 272, 190, 136)
    s += smoke_badge(468, 456, 72)
    s += T(297, 634, f'{SMOKE_S}・{SMOKE_N}', 15, '#e6dfd0', JPB, 500)
    s += line(650, 60, 534, op=.5)
    s += T(297, 680, CHARGE, 20, GOLD_L, JPB, 700)
    s += prices_cols(712, 16.5, 24)
    s += T(297, 796, FOOT, 12.5, '#bdb6a8', JPB, 500)
    return s


def poster_smokebig(p):
    """03 「タバコ吸えます」を大きな見出しに。NEW OPEN は丸いスタンプ。"""
    g = f'{p}-g'
    s = bg_dark(p, g) + head06(g) + line(192)
    s += line(206, op=.9) + line(290, op=.9)
    s += cigarette(62, 264, 104, rot=-12)
    s += T(192, 266, SMOKE_T, 48, WHITE, JPB, 900, 'start')
    s += T(297, 316, f'{SMOKE_S}・{SMOKE_N}', 15, GOLD_L, JPB, 700)
    s += photos_big2(p, 332, 192, 138)
    s += open_stamp(98, 386, 58, -12)
    s += T(297, 708, CHARGE, 20, GOLD_L, JPB, 700)
    s += prices_inline(738, 16)
    s += T(297, 796, FOOT, 12.5, '#bdb6a8', JPB, 500)
    return s


def poster_openbig(p):
    """04 「NEW OPEN」をいちばん上に大きく。"""
    g = f'{p}-g'
    s = bg_dark(p, g)
    s += T(297, 104, OPEN_EN, 78, f'url(#{g})', NUM, 700, ls=12)
    s += T(297, 142, OPEN_JP, 24, WHITE, JPB, 700, ls=4)
    s += line(162)
    s += logo(168, 174, 200)
    s += T(548, 236, 'BAR', 70, f'url(#{g})', SERIF, 700, 'end', ls=12)
    s += T(548, 286, '3F', 50, f'url(#{g})', NUM, 700, 'end')
    s += T(480, 281, 'このビルの', 19, WHITE, JPB, 700, 'end')
    s += line(300)
    s += photos_big2(p, 310, 172, 124)
    s += smoke_band(624, 56, size=32)
    s += T(297, 702, SMOKE_N, 14.5, '#cfc8bb', JPB, 500)
    s += T(297, 732, CHARGE, 20, GOLD_L, JPB, 700)
    s += prices_inline(760, 16)
    s += T(297, 808, FOOT, 12.5, '#bdb6a8', JPB, 500)
    return s


def poster_stack(p):
    """05 写真3枚を、同じ大きさで縦に。"""
    g = f'{p}-g'
    s = bg_dark(p, g) + head_small(g)
    s += open_banner(162, 36)
    for i, (name, fx, fy) in enumerate(PHOTO3):
        s += ph(name, 40, 208 + i * 126, 514, 118, f'{p}-p{i}', fx, fy)
    s += smoke_band(592, 58, size=34)
    s += T(297, 672, SMOKE_N, 14.5, '#cfc8bb', JPB, 500)
    s += line(688, 60, 534, op=.5)
    s += T(297, 716, CHARGE, 20, GOLD_L, JPB, 700)
    s += prices_inline(744, 16)
    s += T(297, 800, FOOT, 12.5, '#bdb6a8', JPB, 500)
    return s


def poster_tall(p):
    """06 縦長の写真3枚を、横に並べる。"""
    g = f'{p}-g'
    s = bg_dark(p, g) + head06(g) + line(192)
    s += open_banner(200, 38)
    for i, (name, fx, fy, z) in enumerate((('counter-dark', .78, .5, 1), ('tables', .5, .68, 1.3), ('darts', .5, .56, 1.2))):
        x = 40 + i * 176
        s += ph(name, x, 250, 162, 286, f'{p}-p{i}', fx, fy, zoom=z)
        s += f'<rect x="{x}" y="250" width="162" height="286" fill="none" stroke="{GOLD}" stroke-width=".9" opacity=".8"/>'
    s += smoke_band(552, 58, size=34)
    s += T(297, 632, SMOKE_N, 14.5, '#cfc8bb', JPB, 500)
    s += line(648, 60, 534, op=.5)
    s += T(297, 676, CHARGE, 20, GOLD_L, JPB, 700)
    s += prices_cols(708, 16.5, 24)
    s += T(297, 792, FOOT, 12.5, '#bdb6a8', JPB, 500)
    return s


def poster_red(p):
    """07 赤を少し足して（NEW OPEN の帯と、タバコの帯のふちを赤に）。"""
    g = f'{p}-g'
    s = bg_dark(p, g) + head06(g) + line(192, color=RED, w=1.6, op=1)
    s += open_banner(200, 40, bg=RED, fg='#fbeede')
    s += photos_big2(p, 250, 188, 138)
    s += smoke_band(598, 62, accent=RED, bg='#1b1215', ember='#ff5a2a')
    s += T(297, 684, SMOKE_N, 14.5, '#e9cfca', JPB, 500)
    s += line(700, 60, 534, color=RED, op=.8)
    s += T(297, 728, CHARGE, 20, GOLD_L, JPB, 700)
    s += prices_inline(756, 16)
    s += T(297, 808, FOOT, 12.5, '#bdb6a8', JPB, 500)
    return s


def poster_circle(p):
    """08 丸い写真3枚。"""
    g = f'{p}-g'
    s = bg_dark(p, g) + head06(g) + line(192)
    s += line(226, 60, 168, op=.8) + line(226, 426, 534, op=.8)
    s += T(297, 238, OPEN_EN, 36, f'url(#{g})', NUM, 700, ls=10)
    s += T(297, 266, OPEN_JP, 17, WHITE, JPB, 700, ls=3)

    def disc(i, cx, cy, r):
        name, fx, fy = PHOTO3[i]
        d = f'M{cx - r} {cy} a{r} {r} 0 1 0 {2 * r} 0 a{r} {r} 0 1 0 {-2 * r} 0 Z'
        return (f'<circle cx="{cx}" cy="{cy + 4}" r="{r + 2}" fill="#000" opacity=".6" filter="url(#soft)"/>'
                + ph(name, cx - r, cy - r, 2 * r, 2 * r, f'{p}-p{i}', fx, fy, clip=d)
                + f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{GOLD}" stroke-width="2.6"/>'
                + f'<circle cx="{cx}" cy="{cy}" r="{r + 6}" fill="none" stroke="{GOLD}" stroke-width=".7" opacity=".8"/>')
    s += disc(0, 297, 410, 124) + disc(1, 112, 484, 76) + disc(2, 482, 484, 76)
    s += smoke_band(578, 58, size=34)
    s += T(297, 658, SMOKE_N, 14.5, '#cfc8bb', JPB, 500)
    s += line(674, 60, 534, op=.5)
    s += T(297, 702, CHARGE, 20, GOLD_L, JPB, 700)
    s += prices_cols(732, 16, 23)
    s += T(297, 806, FOOT, 12.5, '#bdb6a8', JPB, 500)
    return s


def poster_wide(p):
    """09 大きい写真を上いっぱいに（ふちなし）。"""
    g = f'{p}-g'
    s = f'<defs>{gold_grad(g)}{shade(p + "-t", .93, 0)}<linearGradient id="{p}-b" x1="0" y1="0" x2="0" y2="1">' \
        f'<stop offset="0" stop-color="#0c0b0e" stop-opacity="0"/><stop offset="1" stop-color="#0c0b0e"/></linearGradient></defs>'
    s += f'<rect width="{PW}" height="{PH}" fill="#0c0b0e"/>'
    s += ph('counter-dark', 0, 0, PW, 410, f'{p}-p0', .6, .58)
    s += f'<rect width="{PW}" height="250" fill="url(#{p}-t)"/><rect y="320" width="{PW}" height="92" fill="url(#{p}-b)"/>'
    s += head_small(g)
    s += f'<rect x="40" y="350" width="356" height="42" rx="6" fill="{GOLD}"/>'
    s += open_text(54, 379, 25, 18, '#141008', gap=14, anchor='start')
    s += ph('tables', 40, 416, 253, 142, f'{p}-p1', .5, .62)
    s += ph('darts', 301, 416, 253, 142, f'{p}-p2', .48, .42)
    s += smoke_band(572, 58, size=34)
    s += T(297, 652, SMOKE_N, 14.5, '#cfc8bb', JPB, 500)
    s += line(668, 60, 534, op=.5)
    s += T(297, 696, CHARGE, 20, GOLD_L, JPB, 700)
    s += prices_cols(726, 16, 23)
    s += T(297, 802, FOOT, 12.5, '#bdb6a8', JPB, 500)
    return s


def poster_polaroid(p):
    """10 白いふちの写真を、斜めに貼ったように。NEW OPEN はスタンプ。"""
    g = f'{p}-g'
    s = bg_dark(p, g) + head06(g) + line(192)
    s += pol('counter-dark', 46, 216, 316, 250, -4, f'{p}-p0', .62, .55)
    s += pol('tables', 340, 228, 212, 192, 5, f'{p}-p1', .5, .62)
    s += pol('darts', 300, 414, 230, 196, -3, f'{p}-p2', .48, .42)
    s += open_stamp(124, 546, 62, -10)
    s += smoke_band(626, 58, size=34)
    s += T(297, 706, SMOKE_N, 14.5, '#cfc8bb', JPB, 500)
    s += T(297, 736, CHARGE, 20, GOLD_L, JPB, 700)
    s += prices_inline(764, 16)
    s += T(297, 810, FOOT, 12.5, '#bdb6a8', JPB, 500)
    return s


# ---- 仕上がり（2026-11-02 お店の返事: 案09をもとに、タバコは丸いシールで控えめに、Instagram の QR コードを足す） ----------
def insta_glyph(cx, cy, s, color):
    """Instagram の印（角の丸い四角・丸・点）。s は一辺の長さ。"""
    w = s * .09
    return (f'<rect x="{cx - s / 2 + w / 2:.2f}" y="{cy - s / 2 + w / 2:.2f}" width="{s - w:.2f}" height="{s - w:.2f}" rx="{s * .28:.2f}" '
            f'fill="none" stroke="{color}" stroke-width="{w:.2f}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{s * .22:.2f}" fill="none" stroke="{color}" stroke-width="{w:.2f}"/>'
            f'<circle cx="{cx + s * .26:.2f}" cy="{cy - s * .26:.2f}" r="{s * .055:.2f}" fill="{color}"/>')


def qr_tile(x, y, size, dark=INK, light='#f6f2ea', border=GOLD):
    """QR コードの札（まわりに4ます分の余白）。黒は明るい地に置く（白黒が逆だと読めないスマホがあるため）。
    横に続く黒のます目は1本にまとめ、境目に細い線が出ないよう crispEdges で描く。"""
    n = len(QR)
    m = size / (n + 8)
    d = []
    for r, row in enumerate(QR):
        c = 0
        while c < n:
            if not row[c]:
                c += 1
                continue
            c0 = c
            while c < n and row[c]:
                c += 1
            d.append(f'M{x + (c0 + 4) * m:.3f} {y + (r + 4) * m:.3f}h{(c - c0) * m:.3f}v{m:.3f}h{-(c - c0) * m:.3f}z')
    return (f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="{m * 1.6:.2f}" fill="{light}" stroke="{border}" stroke-width="1.2"/>'
            f'<path d="{"".join(d)}" fill="{dark}" shape-rendering="crispEdges"/>')


def poster_final(p, b=0, F=None):
    """仕上がり: 案09「写真を上いっぱいに」をもとに、タバコは丸いシール（案02のシールより小さく、控えめに）、
    右下に Instagram の QR コード。b は印刷用の塗り足し（mm）。ふちまである写真と地の色だけ、外へ広げる。
    F は丸で囲んだ所（NEW OPEN の札・値段の一覧・営業時間）の書体（書体の案。なければ final の font の書体）。"""
    F = F or FINAL_TYPE
    g = f'{p}-g'
    W = PW + 2 * b
    s = (f'<defs>{F.defs(p)}{gold_grad(g)}{shade(p + "-t", .93, 0)}<linearGradient id="{p}-b" x1="0" y1="0" x2="0" y2="1">'
         f'<stop offset="0" stop-color="#0c0b0e" stop-opacity="0"/><stop offset="1" stop-color="#0c0b0e"/></linearGradient></defs>')
    s += f'<rect x="{-b}" y="{-b}" width="{W}" height="{PH + 2 * b}" fill="#0c0b0e"/>'
    s += ph('counter-dark', -b, -b, W, 410 + b, f'{p}-p0', .6, .58)
    s += f'<rect x="{-b}" y="{-b}" width="{W}" height="{250 + b}" fill="url(#{p}-t)"/><rect x="{-b}" y="320" width="{W}" height="92" fill="url(#{p}-b)"/>'
    s += head_small(g)
    s += F.band(40, 350, 42, '#141008')
    s += ph('tables', 40, 416, 253, 142, f'{p}-p1', .5, .62)
    s += ph('darts', 301, 416, 253, 142, f'{p}-p2', .48, .42)
    s += smoke_badge(488, 402, 60)
    s += T(297, 592, f'{SMOKE_S}・{SMOKE_N}', 15, '#e6dfd0', JPB, 500)
    s += line(608, 40, 554, op=.5)
    # 左: 値段の目安（英語の表記。いちばん上にチャージ）と営業時間、右: Instagram の QR コード（12.4cm 角）
    s += F.prices(p, 48, 312)
    qs, qx, qy = 124, 430, 624
    cx = qx + qs / 2
    s += qr_tile(qx, qy, qs)
    s += insta_glyph(cx - 39, 773, 13, GOLD_L) + T(cx - 27, 778, 'Instagram', 15, GOLD_L, NUM, 700, 'start')
    s += T(cx, 800, INSTA, 13, '#ebe5d8', JPB, 500)
    return s


# 案の id → (ポスターを描く関数, 光ったときのまわりの色)
POSTERS = {
    'final': (poster_final, '#e6f5c4'),
    'base': (poster_base, '#ffe2a6'), 'corner': (poster_corner, '#ffe2a6'), 'smokebig': (poster_smokebig, '#ffe2a6'),
    'openbig': (poster_openbig, '#ffe2a6'), 'stack': (poster_stack, '#ffe2a6'), 'tall': (poster_tall, '#ffe2a6'),
    'red': (poster_red, '#ffc2b0'), 'circle': (poster_circle, '#ffe2a6'), 'wide': (poster_wide, '#e6f5c4'),
    'polaroid': (poster_polaroid, '#ffe2a6'),
}


def badge_of(pr):
    """画像の金の札の文字（仕上がりは「仕上がり」、10案は「案09」のように）。"""
    return pr.get('badge') or '案' + pr['no']


def poster(pr):
    func, _ = POSTERS[pr['id']]
    p = 'pf' if pr['id'] == 'final' else 'p' + pr['no']
    return (f'<clipPath id="{p}-all"><rect width="{PW}" height="{PH}"/></clipPath>'
            f'<g clip-path="url(#{p}-all)">{func(p)}</g>')


# ---- スタンド（正面・mm。左上が 0,0。幅 640・高さ 1185。上の 884 がボード面） ----------------------
def stand_svg(art, lit=True, cord=True):
    m = 'url(#metal)'
    rim = f'stroke="{RIM_OUT}" stroke-width="3"'
    s = ''
    s += f'<rect x="12" y="{BOARD_H - 30}" width="26" height="{STAND_H - BOARD_H + 14}" fill="{m}" {rim}/>'
    s += f'<rect x="{STAND_W - 38}" y="{BOARD_H - 30}" width="26" height="{STAND_H - BOARD_H + 14}" fill="{m}" {rim}/>'
    s += f'<rect x="38" y="{STAND_H - 120}" width="{STAND_W - 76}" height="14" fill="url(#metalV)" {rim}/>'
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
          f'<rect x="{LIP}" y="{LIP}" width="{STAND_W - 2 * LIP}" height="{BOARD_H - 2 * LIP}" fill="none" stroke="{RIM_IN}" stroke-width="2.5"/>'
          f'<rect x="1.5" y="1.5" width="{STAND_W - 3}" height="{BOARD_H - 3}" rx="7" fill="none" stroke="{RIM_OUT}" stroke-width="3"/>')
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
def chrome(badge, title, sub, caption, w=1600, h=1000, foot='ダイニングバー XⅢ クロスリー｜入口の置き看板のポスター'):
    """画像の上の帯（左に金の札・題名・説明）と、下の帯（説明・店名）。badge は札の文字（「案09」「仕上がり」。なしなら札を出さない）。"""
    bw = max(96, 26 * len(badge) + 34) if badge else 0
    s = f'<rect x="0" y="0" width="{w}" height="120" fill="#000" opacity=".45"/>'
    if badge:
        s += f'<rect x="40" y="36" rx="12" width="{bw}" height="46" fill="{GOLD}"/>' + T(40 + bw / 2, 69, badge, 26, '#1a1408', JP, 700)
    tx = 40 + bw + 16 if badge else 44
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
    over += T(x + 20, y + 68, f'光るスタンド（A1・{FRAME}）に、このポスターを入れたところ', 18, '#c9cad3', JP, 500, 'start')
    over += f'<clipPath id="zoomClip"><rect x="{zx}" y="{zy}" width="{zw}" height="{zh}" rx="10"/></clipPath>'
    over += (f'<g clip-path="url(#zoomClip)"><svg x="{zx}" y="{zy}" width="{zw}" height="{zh}" '
             f'viewBox="{CX - 4 - vw / 2:.2f} {vy:.2f} {vw:.2f} {vh:.2f}" preserveAspectRatio="xMidYMid slice">{world}</svg></g>')
    over += f'<rect x="{zx}" y="{zy}" width="{zw}" height="{zh}" rx="10" fill="url(#vignette)"/>'
    over += f'<rect x="{zx + 12}" y="{zy + 12}" width="66" height="32" rx="8" fill="#000" opacity=".6"/>' + T(zx + 45, zy + 34, '拡大', 18, GOLD_L, JP, 700)
    sx, sy = po(CX + STAND_W * S / 2 + 1, G - STAND_H * S * .62)
    over += f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{x}" y2="{y + h / 2}" stroke="{GOLD}" stroke-width="2" opacity=".85"/><circle cx="{sx:.1f}" cy="{sy:.1f}" r="5" fill="{GOLD}"/>'
    over += chrome(badge_of(pr), pr['name'], pr['catch'], '置いたイメージ（イラスト・夜）　ビルの敷地の中、入口のガラス扉の横に置いたところ')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000">{DEFS}{body}{over}</svg>'


# ---- デザイン（ポスターの全体） ----------------------------------------------------------
SHEET = (1200, 1800)


def sheet_svg(pr, art=None, lines=None):
    """デザインの画像（ポスターの全体と、下に札・題名・説明）。art はポスターの絵、lines は下の説明の2行（なければ案の説明）。"""
    W, H = SHEET
    k = 1060 / PW
    x0, y0 = 70, 60
    body = f'<rect width="{W}" height="{H}" fill="url(#bgDesign)"/><rect width="{W}" height="{H}" fill="url(#grid)"/>'
    body += f'<rect x="{x0 + 10}" y="{y0 + 18}" width="{PW * k}" height="{PH * k}" fill="#000" opacity=".55" filter="url(#softer)"/>'
    body += f'<g transform="translate({x0},{y0}) scale({k:.5f})">{art or poster(pr)}</g>'
    y = y0 + PH * k + 40
    badge = badge_of(pr)
    bw = max(104, 28 * len(badge) + 36)
    body += f'<rect x="{x0}" y="{y}" rx="12" width="{bw}" height="50" fill="{GOLD}"/>' + T(x0 + bw / 2, y + 35, badge, 28, '#1a1408', JP, 700)
    body += T(x0 + bw + 20, y + 37, pr['name'], 36, '#fff', JP, 700, 'start')
    if not lines:
        kind = '仕上がり' if pr['id'] == 'final' else 'デザイン案'
        note = '「〇〇〇」の値段は、決まったら入れます。' if any(x['tbd'] for x in PRICES.values()) or CHARGE_AMT.count('〇') else ''
        lines = (f'差し込むポスター（A1・59.4 × 84.1cm）の{kind}　{pr["style"]}',
                 note + '写真はお店の写真です（印刷の前に撮り直すと、もっときれいになります）。')
    body += T(x0, y + 92, lines[0], 22, '#c9cad3', JP, 500, 'start')
    body += T(x0, y + 128, lines[1], 20, '#9ea3b2', JP, 500, 'start')
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
    rim, front, back = SIDE
    for (xa, w, col) in ((x1, 12, front), (x1 + d, 7, back)):
        leg = f'M{xa} {base} L{x1 + d * .5} {top}'
        if rim:     # ブラックは、ふちの色を下に敷いて形を見せる
            body += f'<path d="{leg}" stroke="{rim}" stroke-width="{w + 4}" stroke-linecap="round"/>'
        body += f'<path d="{leg}" stroke="{col}" stroke-width="{w}" stroke-linecap="round"/>'
    body += f'<path d="M{x1 + d * .14} {base - 150} L{x1 + d * .86} {base - 150}" stroke="#7d838c" stroke-width="3" stroke-dasharray="6 5"/>'
    body += f'<circle cx="{x1 + d * .5}" cy="{top}" r="7" fill="{front}" stroke="{rim or front}" stroke-width="2"/>'
    body += dim_h(x1, x1 + d, base + 34, '奥行 49cm')
    body += T(x1 + d / 2, top - 22, '横から', 24, '#fff', JP, 700)
    # たたんだところ
    x2 = 950
    fh = 1225 * k
    body += f'<rect x="{x2}" y="{base - fh}" width="{60 * k}" height="{fh}" rx="2" fill="url(#metal)" stroke="{RIM_OUT}" stroke-width="1.5"/>'
    body += dim_v(x2 + 60 * k + 24, base - fh, base, 'たたむと 高さ 122.5cm', 'right')
    body += T(x2 + 12, base + 34, '厚さ 6cm', 19, '#aeb3c2', JP, 700)
    body += T(x2 + 12, base - fh - 22, 'たたむと', 24, '#fff', JP, 700)
    # 説明
    px = 1160
    facts = [('光る', ['中の LED パネルが、', 'ポスターを後ろから照らす']), ('電源', ['コンセントにつなぐ', '（AC アダプター）']),
             ('入れ替え', ['表の枠を開けて、', 'A1 のポスターを差し込む']), ('外に置ける', ['ポスターは水に強いもの', '（耐水）にする']),
             (f'値段（{FRAME}）', [f'{DATA["stand"]["price"]}（税込・送料無料）'])]
    body += f'<rect x="{px}" y="200" width="400" height="{70 + 100 * len(facts)}" rx="18" fill="#0b0d13" opacity=".75" stroke="#2c303b"/>'
    for i, (a, lines) in enumerate(facts):
        yy = 252 + i * 100
        body += T(px + 28, yy, a, 19, GOLD, JP, 700, 'start')
        for li, line in enumerate(lines):
            body += T(px + 28, yy + 32 + li * 28, line, 21, '#f2f2f5', JP, 500, 'start')
    over = chrome('', 'スタンドの大きさ', f'{DATA["stand"]["shop"]}の{DATA["stand"]["name"]}・{FRAME}（人と同じ縮尺）',
                  '大きさは販売ページの値（幅64 × 奥行49 × 高さ118.5cm、ボード面 64 × 88.4cm）', foot='ダイニングバー XⅢ クロスリー｜入口の置き看板')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{DEFS}{body}{over}</svg>'


# ---- 書き出し ---------------------------------------------------------------------
def capture(b, svg, tmp, size=(1600, 1000), dsf=1.5):
    """SVG を Edge で画像にする（保存はしない）。"""
    w, h = size
    page = tmp / 'render.html'
    page.write_text('<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#000}svg{display:block}</style>'
                    f'</head><body>{svg}</body></html>', encoding='utf-8')
    b.open(page.as_uri(), {'width': w, 'height': h, 'deviceScaleFactor': dsf, 'mobile': False})
    b.wait(1.0)
    r = b.call('Page.captureScreenshot', {'format': 'png', 'clip': {'x': 0, 'y': 0, 'width': w, 'height': h, 'scale': 1}})
    if b.errors:
        print('  エラー:', b.errors[:3])
    return Image.open(io.BytesIO(base64.b64decode(r['data']))).convert('RGB')


def render(b, svg, name, tmp, size=(1600, 1000), dsf=1.5, web=(1200, 750), jpg=True):
    """SVG を Edge で画像にする。jpg は保存用（大きい）、webp はページに出す用（小さい。web が None なら作らない）。"""
    im = capture(b, svg, tmp, size, dsf)
    if jpg:
        im.save(OUT / f'{name}.jpg', 'JPEG', quality=86, optimize=True, progressive=True)
    if web:
        im.resize(web, Image.LANCZOS).save(OUT / f'{name}.webp', 'WEBP', quality=82, method=6)
    return im.size


# ---- 書体の案の画像（ポスター全体・丸で囲んだ所の拡大・一覧用・大きい画像） ------------------------------
TYPE_K = 3        # 書体の案のポスターを、1mm＝3ピクセルで描く
CARD = (600, 850)  # ページに並べるポスター全体の画像の大きさ（10案を1枚に並べた画像にも使う）
ZOOM = ((30, 336, 424, 402), (30, 626, 424, 830))    # 丸で囲んだ所（上: NEW OPEN の札、下: 値段の一覧と営業時間。mm）


def type_base(t):
    return f'sign-font-{t["no"]}-{t["id"]}'


def type_art(t):
    p = 'ft' + t['no']
    return (f'<clipPath id="{p}-all"><rect width="{PW}" height="{PH}"/></clipPath>'
            f'<g clip-path="url(#{p}-all)">{poster_final(p, 0, TYPES[t["no"]])}</g>')


def where_svg():
    """書体を変える所（丸で囲んでいただいた所）の目印: もとの書体（00）のポスターに、黄色の枠を重ねる。"""
    t = next(t for t in DATA['fonts']['list'] if t.get('now'))
    marks = ''
    for x, y, w, h in ((28, 338, TYPES[t['no']].band_width() + 24, 66), (32, 626, 344, 206)):
        marks += (f'<rect x="{x}" y="{y}" width="{w:.1f}" height="{h}" rx="20" fill="none" stroke="#000" stroke-opacity=".55" stroke-width="11"/>'
                  f'<rect x="{x}" y="{y}" width="{w:.1f}" height="{h}" rx="20" fill="none" stroke="#ffe14d" stroke-width="6"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{PW}" height="{PH}" viewBox="0 0 {PW} {PH}">{DEFS}{type_art(t)}{marks}</svg>'


def render_type(b, tmp, t):
    """書体の案: ページに出すポスター全体（card）・丸で囲んだ所を大きくしたもの（zoom）・一覧用（thumb）・題名つきの大きい画像（poster）。"""
    base = type_base(t)
    art = type_art(t)
    im = capture(b, f'<svg xmlns="http://www.w3.org/2000/svg" width="{PW}" height="{PH}" viewBox="0 0 {PW} {PH}">{DEFS}{art}</svg>',
                 tmp, (PW, PH), TYPE_K)
    im.resize(CARD, Image.LANCZOS).save(OUT / f'{base}-card.webp', 'WEBP', quality=84, method=6)
    top, bottom = (im.crop(tuple(round(v * TYPE_K) for v in box)) for box in ZOOM)
    gap = 6 * TYPE_K
    z = Image.new('RGB', (top.width, top.height + gap + bottom.height), '#1c2029')
    z.paste(top, (0, 0))
    z.paste(bottom, (0, top.height + gap))
    for name, w in (('zoom', 1000), ('thumb', 360)):
        z.resize((w, round(w * z.height / z.width)), Image.LANCZOS).save(OUT / f'{base}-{name}.webp', 'WEBP', quality=84, method=6)
    pr = {'id': 'font', 'badge': t['name'] if t.get('now') else '書体' + t['no'], 'name': t['name']}
    lines = ('書体を変える前の仕上がりの書体です（くらべる用）' if t.get('now') else '丸で囲んだ所（NEW OPEN の札と、値段の一覧）の書体だけを変えた案',
             f'英語・数字：{t["en_name"]}　／　日本語：{t["ja_name"]}')
    render(b, sheet_svg(pr, art, lines), f'{base}-poster', tmp, size=SHEET, dsf=1.2, web=None)
    return im.size, z.size


def fonts_all_svg():
    """書体の10案を、ポスター全体で1枚に並べた画像（保存して LINE などで送れるように）。各案の card の画像を並べる。"""
    W, H, cols, pw, gap, y0 = 1800, 1240, 5, 312, 32, 150
    ph = pw * PH / PW
    x0 = (W - cols * pw - (cols - 1) * gap) / 2
    body = f'<rect width="{W}" height="{H}" fill="url(#bgDesign)"/><rect width="{W}" height="{H}" fill="url(#grid)"/>'
    body += T(x0, 72, '書体の10案（ポスター全体）', 36, '#fff', JP, 700, 'start')
    body += T(x0, 110, '丸で囲んでいただいた所（NEW OPEN の札と、値段の一覧）の書体だけを変えています。ほかの所は同じです。',
              20, '#cfd0d8', JP, 500, 'start')
    for i, t in enumerate(t for t in DATA['fonts']['list'] if not t.get('now')):
        x, y = x0 + i % cols * (pw + gap), y0 + i // cols * (ph + 76)
        body += f'<rect x="{x + 6}" y="{y + 10}" width="{pw}" height="{ph:.1f}" fill="#000" opacity=".55" filter="url(#soft)"/>'
        body += f'<image href="{(OUT / f"{type_base(t)}-card.webp").as_uri()}" x="{x}" y="{y}" width="{pw}" height="{ph:.1f}"/>'
        body += f'<rect x="{x}" y="{y + ph + 14:.1f}" rx="8" width="50" height="34" fill="{GOLD}"/>' + T(x + 25, y + ph + 38.5, t['no'], 22, '#1a1408', JP, 700)
        body += T(x + 62, y + ph + 39, t['name'], 22, '#fff', JP, 700, 'start')
    body += T(W - x0, H - 26, 'ダイニングバー XⅢ クロスリー｜入口の置き看板のポスター', 18, GOLD, JP, 700, 'end')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{DEFS}{body}</svg>'


# ---- 印刷用の PDF（仕上がり） ------------------------------------------------------------
BLEED = 3        # 塗り足し（mm）。仕上がりの A1（594×841）のまわりに 3mm ずつ広げる
PRINT_K = 8      # 1mm を 8 ピクセルで描く（約 200dpi。大判の印刷は原寸で 150〜200dpi あれば足りる。写真の元は 100dpi ほど）


def print_svg():
    """印刷用: 塗り足しまで描いた A1（600×847mm）。"""
    W, H = PW + 2 * BLEED, PH + 2 * BLEED
    body = (f'<clipPath id="pp-all"><rect x="{-BLEED}" y="{-BLEED}" width="{W}" height="{H}"/></clipPath>'
            f'<g clip-path="url(#pp-all)">{poster_final("pp", BLEED)}</g>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="{-BLEED} {-BLEED} {W} {H}">{DEFS}{body}</svg>'


def jpeg_pdf(path, jpg, px, size_mm, bleed_mm, title):
    """JPEG 1枚を、1ページの PDF にする。ページは size_mm（塗り足しこみ）、その内側の仕上がりを TrimBox に書く。"""
    pt = 72 / 25.4
    W, H, t = size_mm[0] * pt, size_mm[1] * pt, bleed_mm * pt
    content = f'q {W:.3f} 0 0 {H:.3f} 0 0 cm /Im0 Do Q'.encode()
    title_hex = 'FEFF' + title.encode('utf-16-be').hex().upper()
    objs = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        (f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W:.3f} {H:.3f}] /BleedBox [0 0 {W:.3f} {H:.3f}] '
         f'/TrimBox [{t:.3f} {t:.3f} {W - t:.3f} {H - t:.3f}] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>').encode(),
        (f'<< /Type /XObject /Subtype /Image /Width {px[0]} /Height {px[1]} /ColorSpace /DeviceRGB /BitsPerComponent 8 '
         f'/Filter /DCTDecode /Length {len(jpg)} >>\nstream\n').encode() + jpg + b'\nendstream',
        f'<< /Length {len(content)} >>\nstream\n'.encode() + content + b'\nendstream',
        f'<< /Title <{title_hex}> /Creator (tools/make_sign_images.py) >>'.encode(),
    ]
    out = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f'{i} 0 obj\n'.encode() + o + b'\nendobj\n'
    xref = len(out)
    out += f'xref\n0 {len(objs) + 1}\n0000000000 65535 f \n'.encode()
    out += b''.join(f'{off:010d} 00000 n \n'.encode() for off in offsets)
    out += f'trailer\n<< /Size {len(objs) + 1} /Root 1 0 R /Info {len(objs)} 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    path.write_bytes(bytes(out))


def render_print(b, tmp):
    """印刷用の PDF を作る（4800×6776 ピクセルを1回で撮る。分けて撮ってつなぐと、つなぎ目に黒い線が出たため）。"""
    W, H = PW + 2 * BLEED, PH + 2 * BLEED
    page = tmp / 'print.html'
    page.write_text('<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#000}svg{display:block}</style>'
                    f'</head><body>{print_svg()}</body></html>', encoding='utf-8')
    b.open(page.as_uri(), {'width': W, 'height': H, 'deviceScaleFactor': PRINT_K, 'mobile': False})
    b.wait(2.0)
    r = b.call('Page.captureScreenshot', {'format': 'png', 'clip': {'x': 0, 'y': 0, 'width': W, 'height': H, 'scale': 1}})
    im = Image.open(io.BytesIO(base64.b64decode(r['data']))).convert('RGB')
    if im.size != (W * PRINT_K, H * PRINT_K):
        raise SystemExit(f'印刷用の画像の大きさが違います: {im.size}')
    if b.errors:
        print('  エラー:', b.errors[:3])
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=92, subsampling=0, optimize=True)     # 色の境目がにじまないよう、色を間引かない
    jpeg_pdf(PDF, buf.getvalue(), im.size, (W, H), BLEED, 'ダイニングバー XⅢ クロスリー 入口の置き看板のポスター（A1・印刷用）')
    # 確かめる用の小さい画像（ページには出さない）
    im.resize((W, H), Image.LANCZOS).save(tmp / 'print-preview.png')
    return im.size, f'{PDF.stat().st_size / 1024 / 1024:.1f}MB'


def main():
    only = set(sys.argv[1].split(',')) if len(sys.argv) > 1 else None
    OUT.mkdir(parents=True, exist_ok=True)
    if not only:
        for f in OUT.glob('*'):          # 前の画像（前の提案の看板など）を残さない
            f.unlink()
        for old in OUT.parent.glob('xiii-sign-*.zip'):   # 前にあった「画像をまとめて保存」の ZIP（今は印刷用の PDF を渡す）
            old.unlink()
    tmp = Path(tempfile.mkdtemp())
    b = shoot.Browser()
    final = DATA['final']
    try:
        if not only or '00' in only:
            print('00 今のようす', render(b, scene_now(), 'sign-00-now', tmp))
        if not only or 'stand' in only:
            print('スタンドの大きさ', render(b, stand_figure_svg(), 'sign-stand', tmp))
        if not only or 'final' in only:
            print('仕上がり',
                  render(b, place_svg(final), 'sign-final-place', tmp),
                  render(b, sheet_svg(final), 'sign-final-poster', tmp, size=SHEET, dsf=1.2, web=(800, 1200)))
        if not only or 'pdf' in only:
            print('印刷用 PDF', PDF.name, *render_print(b, tmp), '（確かめる用の画像:', tmp / 'print-preview.png', '）')
        if not only or 'fonts' in only or 'where' in only:
            print('書体を変える所の目印', render(b, where_svg(), 'sign-font-where', tmp, size=(PW, PH), dsf=1, web=(480, 680), jpg=False))
        for t in DATA['fonts']['list']:  # 書体の案（丸で囲んだ所の書体だけを変えたもの）
            if only and 'fonts' not in only and f'font{t["no"]}' not in only:
                continue
            print('書体', t['no'], t['name'], *render_type(b, tmp, t))
        if not only or any(x == 'fonts' or x.startswith('font') for x in only):   # 10案をポスター全体で1枚に並べた画像
            print('書体の10案（1枚）', render(b, fonts_all_svg(), 'sign-font-all', tmp, size=(1800, 1240), dsf=1.5, web=None))
        for pr in DATA['proposals']:     # それまでの10案（参考）: デザインと一覧用の画像だけ
            if only and pr['no'] not in only:
                continue
            base = f'sign-{pr["no"]}-{pr["id"]}'
            print(pr['no'], pr['name'],
                  render(b, sheet_svg(pr), f'{base}-poster', tmp, size=SHEET, dsf=1.2, web=(800, 1200)),
                  render(b, thumb_svg(pr), f'{base}-thumb', tmp, size=(PW, PH), dsf=1, web=(480, 680), jpg=False))
    finally:
        b.close()


if __name__ == '__main__':
    main()
