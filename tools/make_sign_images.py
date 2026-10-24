"""看板の提案（1階入口の置き看板・10案）のイメージ画像を作る。

  python -I -X utf8 tools/make_sign_images.py [01,05 …]   … 番号を渡すと、その案だけ作り直す

建物はストリートビューの写真を加工せず、イラストで描き起こす（Google の画像は加工して公開できないため）。
青い角のビル、丸い角の大きな窓、1階の隣のお店の木の扉と入口のガラス扉、右の柱の案内板、手前の電柱と電線。
1案につき2枚: 設置イメージ（夜の入口に置いたところ）とデザイン（看板の正面・寸法入り）。ほかに「今のようす」1枚。
SVG で描き、画面なしの Edge で JPEG（2400×1500）に書き出す。ページ用の小さい WebP と、まとめてダウンロードする ZIP も作る。
文字や値段は signs.json と site.json から読む。
"""
import html
import io
import json
import sys
import tempfile
import time
import zipfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shoot  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / 'docs' / 'assets' / 'img'
OUT = ROOT / 'docs' / 'signs' / 'img'
ZIP = ROOT / 'docs' / 'signs' / 'xiii-sign-ideas.zip'
DATA = json.loads((ROOT / 'signs.json').read_text(encoding='utf-8'))
SITE = json.loads((ROOT / 'site.json').read_text(encoding='utf-8'))

LOGO = (IMG / 'logo-x-iii.png').as_uri()
LOGO_W = (IMG / 'logo-x-iii-white.png').as_uri()
PHOTO = (IMG / 'counter-dark-1600.webp').as_uri()
PHOTO2 = (IMG / 'backbar-1600.webp').as_uri()
BARLOW = (ROOT / 'tools' / 'fonts' / 'Barlow-Regular.ttf').as_uri()

JP = "'Yu Gothic','Meiryo',sans-serif"
SERIF = "'Palatino Linotype','Book Antiqua',Georgia,serif"
NUM = "'Bahnschrift','Barlow',sans-serif"
SCRIPT = "'Segoe Script','Segoe Print',cursive"
HAND = "'Segoe Print','Yu Gothic',cursive"

GOLD, GOLD_L, INK, WHITE = '#d9b66f', '#f4dfa8', '#0c0c0f', '#f6f2ea'
HOURS = f"{SITE['open']}–{int(SITE['close'][:2])}:{SITE['close'][3:]}"  # 19:00–7:00

S = 0.07          # 設置イメージの縮尺（1mm = 0.07。1m = 70）
G = 905           # 地面（入口の段の上）の高さ
VB = (430, 160, 1290, 806.25)   # 設置イメージで切り取る範囲（1600×1000 に拡大する）
K = 1600 / VB[2]


def esc(s):
    return html.escape(str(s), quote=True)


def o(x, y):
    """建物の絵の座標を、出来上がりの画像（1600×1000）の座標にする。"""
    return ((x - VB[0]) * K, (y - VB[1]) * K)


def T(x, y, s, size, fill=WHITE, fam=JP, w=700, anchor='middle', ls=0, extra=''):
    return (f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" font-weight="{w}" fill="{fill}" '
            f'text-anchor="{anchor}" letter-spacing="{ls}" {extra}>{esc(s)}</text>')


def logo(cx, y, w, white=False, extra=''):
    h = w * 234 / 444
    return f'<image href="{LOGO_W if white else LOGO}" x="{cx - w / 2}" y="{y}" width="{w}" height="{h:.1f}" {extra}/>'


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
<linearGradient id="cylShade" x1="0" x2="1"><stop offset="0" stop-color="#000" stop-opacity=".55"/><stop offset=".3" stop-color="#000" stop-opacity="0"/><stop offset=".7" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".6"/></linearGradient>
<radialGradient id="lamp" cx="1" cy=".62" r=".75"><stop offset="0" stop-color="#ffd9a0" stop-opacity=".30"/><stop offset="1" stop-color="#ffd9a0" stop-opacity="0"/></radialGradient>
<radialGradient id="lobbySpill" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#eaf2ff" stop-opacity=".45"/><stop offset="1" stop-color="#eaf2ff" stop-opacity="0"/></radialGradient>
<radialGradient id="spill" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ffd58c" stop-opacity=".8"/><stop offset="1" stop-color="#ffd58c" stop-opacity="0"/></radialGradient>
<radialGradient id="spillPink" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ff6fb4" stop-opacity=".7"/><stop offset="1" stop-color="#ff6fb4" stop-opacity="0"/></radialGradient>
<radialGradient id="spillCool" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#cfe7ff" stop-opacity=".7"/><stop offset="1" stop-color="#cfe7ff" stop-opacity="0"/></radialGradient>
<radialGradient id="faceLit" cx=".5" cy=".42" r=".75"><stop offset="0" stop-color="#25232a"/><stop offset="1" stop-color="#0c0c0f"/></radialGradient>
<radialGradient id="washi" cx=".5" cy=".55" r=".7"><stop offset="0" stop-color="#fff3d6"/><stop offset=".7" stop-color="#f3dcae"/><stop offset="1" stop-color="#d9b77e"/></radialGradient>
<radialGradient id="bgDesign" cx=".35" cy=".5" r=".8"><stop offset="0" stop-color="#262a33"/><stop offset="1" stop-color="#101217"/></radialGradient>
<linearGradient id="photoFade" x1="0" y1="0" x2="0" y2="1"><stop offset=".45" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".88"/></linearGradient>
<linearGradient id="screenFade" x1="0" y1="0" x2="0" y2="1"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".95"/></linearGradient>
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#fff" stroke-opacity=".035"/></pattern>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="22" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="halo" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="120"/></filter>
<filter id="neon" x="-60%" y="-60%" width="220%" height="220%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="9" result="a"/><feGaussianBlur stdDeviation="28" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="a"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="5"/></filter>
<filter id="softer" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="14"/></filter>
<filter id="chalk" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="4" result="n"/><feColorMatrix in="n" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 -1.6 1.25" result="m"/><feComposite in="SourceGraphic" in2="m" operator="in"/></filter>
<filter id="dust" x="0" y="0" width="1" height="1"><feTurbulence type="fractalNoise" baseFrequency=".02" numOctaves="3" seed="9"/><feColorMatrix type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .07 0"/></filter>
<clipPath id="arrowClip"><path d="M300 0 L600 420 L450 420 L450 1500 L150 1500 L150 420 L0 420 Z"/></clipPath>
</defs>"""


# ---- 看板の絵（mm 単位。左上が 0,0） ------------------------------------------------------
def frame(w, h, rx=10, gold=True, inset=14):
    s = f'<rect x="0" y="0" width="{w}" height="{h}" rx="{rx}" fill="url(#faceLit)"/>'
    if gold:
        s += f'<rect x="{inset}" y="{inset}" width="{w - 2 * inset}" height="{h - 2 * inset}" rx="{max(2, rx - 4)}" fill="none" stroke="{GOLD}" stroke-width="5"/>'
    return s


def up_arrow(cx, y, h, color, sw):
    """上を指す矢印（y が先端、h が長さ）。"""
    return (f'<path d="M{cx} {y + h} V{y + sw / 2} M{cx - h * .42} {y + h * .42} L{cx} {y} L{cx + h * .42} {y + h * .42}" fill="none" '
            f'stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')


def chevron(cx, y, w, color, sw):
    return f'<path d="M{cx - w / 2} {y + w / 2} L{cx} {y} L{cx + w / 2} {y + w / 2}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>'


def art_tower():
    w, h = 450, 1800
    s = frame(w, h - 100)
    s += T(225, 170, 'BAR', 132, GOLD_L, SERIF, 700, ls=22)
    s += f'<line x1="95" x2="355" y1="212" y2="212" stroke="{GOLD}" stroke-width="3"/>'
    s += logo(225, 240, 330)
    s += f'<g filter="url(#glow)">{up_arrow(225, 470, 150, GOLD_L, 20)}' + T(225, 900, '3F', 330, '#fff2d2', NUM, 700) + '</g>'
    s += T(225, 1010, 'このビルの3階', 58, WHITE, JP, 700)
    s += T(225, 1078, 'エレベーターでどうぞ', 40, '#d9d3c7', JP, 500)
    s += f'<line x1="95" x2="355" y1="1140" y2="1140" stroke="{GOLD}" stroke-width="3"/>'
    s += T(225, 1222, f'OPEN {HOURS}', 50, GOLD_L, NUM, 600, ls=2)
    s += T(225, 1285, SITE['closed'], 38, '#cfc8bb', JP, 500)
    s += T(225, 1420, 'ウイスキー', 40, '#e8e2d6', JP, 500, ls=4) + T(225, 1480, 'カクテル・ダーツ', 40, '#e8e2d6', JP, 500, ls=4)
    s += f'<rect x="0" y="{h - 100}" width="{w}" height="100" rx="6" fill="#1b1b20"/>'
    return s, w, h


def art_arrow():
    w, h = 600, 1700
    d = 'M300 0 L600 420 L450 420 L450 1500 L150 1500 L150 420 L0 420 Z'
    s = f'<path d="{d}" fill="url(#faceLit)"/>'
    s += f'<g filter="url(#glow)"><path d="{d}" fill="none" stroke="{GOLD_L}" stroke-width="14" stroke-linejoin="round"/></g>'
    s += f'<g filter="url(#glow)">' + T(300, 365, '3F', 200, '#fff2d2', NUM, 700) + '</g>'
    s += T(300, 545, 'BAR', 88, GOLD_L, SERIF, 700, ls=8)
    s += logo(300, 580, 262)
    s += f'<text x="300" y="800" writing-mode="vertical-rl" style="text-orientation:upright" font-family="{JP}" font-size="62" font-weight="700" fill="{WHITE}" letter-spacing="10">このビルの3階へ</text>'
    s += T(300, 1440, HOURS, 44, GOLD_L, NUM, 600)
    s += f'<rect x="80" y="1500" width="440" height="200" rx="14" fill="#1b1b20"/>' + T(300, 1620, 'OPEN', 56, '#8a7c62', NUM, 600, ls=10)
    return s, w, h


def prism_face(i):
    w, h = 400, 1600
    s = frame(w, h)
    if i == 0:
        s += T(200, 170, 'BAR', 110, GOLD_L, SERIF, 700, ls=16) + logo(200, 210, 300)
        s += f'<g filter="url(#glow)">' + T(200, 760, '3F', 300, '#fff2d2', NUM, 700) + '</g>'
        s += T(200, 880, 'このビルの3階', 50, WHITE) + T(200, 945, 'エレベーターで', 38, '#d9d3c7', JP, 500)
        s += f'<g filter="url(#glow)">{chevron(200, 1060, 130, GOLD_L, 20)}{chevron(200, 1130, 130, GOLD_L, 20)}</g>'
    elif i == 1:
        s += T(200, 230, 'OPEN', 120, GOLD_L, NUM, 600, ls=10)
        s += f'<g filter="url(#glow)">' + T(200, 520, SITE['open'], 150, '#fff2d2', NUM, 700) + '</g>'
        s += T(200, 640, '｜', 70, GOLD, JP, 500)
        s += f'<g filter="url(#glow)">' + T(200, 830, f"{int(SITE['close'][:2])}:{SITE['close'][3:]}", 150, '#fff2d2', NUM, 700) + '</g>'
        s += T(200, 940, '朝まで営業', 54, WHITE) + T(200, 1020, SITE['closed'], 40, '#cfc8bb', JP, 500)
        s += logo(200, 1250, 260)
    else:
        s += T(200, 330, '一人でも、', 66, WHITE) + T(200, 420, '気軽に。', 66, WHITE)
        s += f'<line x1="90" x2="310" y1="500" y2="500" stroke="{GOLD}" stroke-width="3"/>'
        for k, t in enumerate(['ウイスキー', 'カクテル', 'ダーツ']):
            s += T(200, 620 + k * 90, t, 50, GOLD_L, JP, 700, ls=6)
        s += f'<g filter="url(#glow)">' + T(200, 1260, 'BAR 3F', 96, '#fff2d2', NUM, 700) + '</g>'
    return s


def art_neon():
    w, h = 600, 1500
    s = f'<rect x="0" y="0" width="600" height="1000" rx="22" fill="#08080a" stroke="#2c2c33" stroke-width="6"/>'
    s += f'<g filter="url(#neon)"><text x="300" y="300" font-family="{SCRIPT}" font-size="250" font-weight="700" fill="none" stroke="#ff5aa8" stroke-width="10" text-anchor="middle">Bar</text></g>'
    s += f'<g filter="url(#neon)"><text x="300" y="560" font-family="{SERIF}" font-size="190" fill="none" stroke="#ffd27a" stroke-width="7" text-anchor="middle" letter-spacing="6">X-III</text>'
    s += f'<text x="300" y="640" font-family="{NUM}" font-size="46" fill="#ffd27a" text-anchor="middle" letter-spacing="22">CROSSLEY</text></g>'
    s += f'<g filter="url(#neon)"><text x="250" y="870" font-family="{NUM}" font-size="170" font-weight="600" fill="none" stroke="#8fe8ff" stroke-width="8" text-anchor="middle">3F</text>'
    s += f'<path d="M430 880 V720 M380 770 L430 720 L480 770" fill="none" stroke="#8fe8ff" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/></g>'
    # スタンド（イーゼル）
    s += '<path d="M120 990 L60 1500 M480 990 L540 1500 M300 990 L300 1440" stroke="#1d1d22" stroke-width="26" stroke-linecap="round"/>'
    s += '<path d="M110 1260 H490" stroke="#1d1d22" stroke-width="18"/>'
    return s, w, h


def art_photo():
    w, h = 600, 1350
    s = f'<rect x="0" y="0" width="600" height="1200" rx="12" fill="#0b0b0e"/>'
    s += '<clipPath id="phClip"><rect x="20" y="20" width="560" height="660" rx="6"/></clipPath>'
    s += f'<g clip-path="url(#phClip)"><image href="{PHOTO}" x="-300" y="20" width="1180" height="660" preserveAspectRatio="xMidYMid slice"/>'
    s += '<rect x="20" y="20" width="560" height="660" fill="url(#photoFade)"/></g>'
    s += T(300, 590, '3階に、', 54, WHITE) + T(300, 652, 'こんなお店があります。', 48, WHITE)
    s += logo(300, 706, 290)
    s += f'<g filter="url(#glow)">' + T(300, 950, 'BAR  3F', 76, GOLD_L, NUM, 700, ls=6) + '</g>'
    s += T(300, 1015, 'このビルの3階・エレベーターで', 33, '#dcd6ca', JP, 500)
    s += T(300, 1075, f'OPEN {HOURS} ／ {SITE["closed"]}', 31, GOLD_L, JP, 700)
    s += T(300, 1140, '一人でも気軽にどうぞ', 34, WHITE, JP, 700)
    s += f'<rect x="70" y="1200" width="460" height="150" rx="10" fill="#1b1b20"/>'
    return s, w, h


def art_chalk():
    w, h = 640, 1450
    s = '<g transform="translate(0,200)">'
    s += '<rect x="0" y="0" width="640" height="900" rx="14" fill="#5d3b22"/><rect x="34" y="34" width="572" height="832" rx="6" fill="#1b2823"/>'
    s += '<rect x="34" y="34" width="572" height="832" fill="#fff" filter="url(#dust)" opacity=".9"/>'
    c = '<g filter="url(#chalk)">'
    c += T(320, 150, 'BAR', 110, '#f4f1e6', HAND, 700, ls=10)
    c += logo(320, 172, 210, white=True, extra='opacity=".85"')
    c += T(235, 520, '3F', 220, '#f7df7c', HAND, 700)
    c += '<path d="M455 520 V350 M405 405 L455 350 L505 405" fill="none" stroke="#f7df7c" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>'
    c += T(320, 600, 'このビルの3階', 50, '#f4f1e6', JP, 700)
    c += T(320, 680, '今夜のおすすめ', 40, '#f6b9b9', JP, 700)
    c += T(320, 735, 'ジントニック・ハイボール', 33, '#f4f1e6', JP, 500)
    c += T(320, 785, 'ナポリタン ¥1,600', 33, '#f4f1e6', JP, 500)
    c += T(320, 840, f'OPEN {HOURS}', 34, '#bfe3ff', HAND, 700)
    c += '</g>'
    s += c
    s += '<path d="M60 900 L10 1250 M580 900 L630 1250" stroke="#5d3b22" stroke-width="30" stroke-linecap="round"/>'
    s += '</g>'
    # 上から照らすライト
    s += '<path d="M320 175 V40 H250" fill="none" stroke="#2a2a2e" stroke-width="12"/><path d="M215 25 h70 l-12 40 h-46 z" fill="#2a2a2e"/>'
    s += '<path d="M228 66 L120 260 H460 L273 66 Z" fill="#ffe7b0" opacity=".08"/>'
    return s, w, h


def art_digital():
    w, h = 640, 1850
    s = '<rect x="0" y="0" width="640" height="1650" rx="26" fill="#131418" stroke="#2c2e34" stroke-width="6"/>'
    s += '<clipPath id="scClip"><rect x="40" y="40" width="560" height="1000" rx="6"/></clipPath><g clip-path="url(#scClip)">'
    s += '<rect x="40" y="40" width="560" height="1000" fill="#050506"/>'
    s += f'<image href="{PHOTO2}" x="-320" y="40" width="1100" height="560" preserveAspectRatio="xMidYMid slice"/>'
    s += '<rect x="40" y="40" width="560" height="560" fill="url(#screenFade)"/>'
    s += '<rect x="66" y="66" width="200" height="56" rx="28" fill="#1fbf6a"/>' + T(166, 104, '● 営業中', 30, '#fff')
    s += logo(320, 560, 300)
    s += T(320, 800, 'BAR  3F', 74, GOLD_L, NUM, 700, ls=6)
    s += T(320, 860, '今夜のおすすめ：ジントニック', 30, WHITE, JP, 500)
    s += '<rect x="40" y="960" width="560" height="80" fill="#1d1e24"/>' + T(320, 1012, 'お知らせ：12/30〜1/3 は年末年始のお休み', 26, '#ffcf8a', JP, 500)
    s += '</g>'
    s += '<rect x="250" y="1100" width="140" height="10" rx="5" fill="#2c2e34"/>'
    s += logo(320, 1220, 280) + T(320, 1520, 'BAR  3F', 70, GOLD, NUM, 700, ls=6)
    s += '<rect x="90" y="1650" width="460" height="200" rx="12" fill="#1b1c21"/>'
    return s, w, h


def art_slim():
    w, h = 200, 1800
    s = frame(w, h - 80, rx=6, inset=10)
    s += T(100, 130, 'BAR', 62, GOLD_L, SERIF, 700, ls=4)
    s += f'<text x="100" y="200" writing-mode="vertical-rl" style="text-orientation:upright" font-family="{SERIF}" font-size="92" font-weight="700" fill="{GOLD_L}" letter-spacing="2">XⅢ</text>'
    s += f'<text x="100" y="440" writing-mode="vertical-rl" style="text-orientation:upright" font-family="{JP}" font-size="56" font-weight="700" fill="{WHITE}" letter-spacing="8">クロスリー</text>'
    s += f'<g filter="url(#glow)">' + T(100, 1080, '3', 230, '#fff2d2', NUM, 700) + T(100, 1250, 'F', 160, '#fff2d2', NUM, 700) + '</g>'
    s += f'<g filter="url(#glow)">{chevron(100, 1330, 90, GOLD_L, 14)}{chevron(100, 1380, 90, GOLD_L, 14)}</g>'
    s += T(100, 1600, HOURS, 30, GOLD_L, NUM, 600)
    s += f'<rect x="0" y="{h - 80}" width="{w}" height="80" rx="6" fill="#1b1b20"/>'
    return s, w, h


def art_andon():
    w, h = 300, 900
    s = '<rect x="0" y="0" width="300" height="900" rx="6" fill="#1a120c"/>'
    s += '<rect x="22" y="40" width="256" height="760" fill="url(#washi)"/>'
    s += '<rect x="22" y="40" width="256" height="760" fill="#fff" filter="url(#dust)" opacity=".5"/>'
    s += '<g stroke="#1a120c" stroke-width="7" opacity=".85"><line x1="22" x2="278" y1="250" y2="250"/><line x1="22" x2="278" y1="590" y2="590"/></g>'
    s += T(150, 172, 'BAR', 72, '#2a1a10', SERIF, 700, ls=12)
    s += (f'<text x="150" y="292" writing-mode="vertical-rl" style="text-orientation:upright" font-family="{SERIF}" '
          f'font-size="118" font-weight="700" fill="#1a120c">XⅢ</text>')
    s += T(150, 712, '3F', 112, '#7a1d14', NUM, 700)
    s += T(150, 772, 'クロスリー', 30, '#2a1a10', JP, 700, ls=6)
    s += '<rect x="0" y="0" width="300" height="40" rx="4" fill="#120c08"/><rect x="0" y="800" width="300" height="100" rx="4" fill="#120c08"/>'
    return s, w, h


def spin_band():
    """円柱のまわりの中身（展開図。幅 848mm = 直径270mm の円周）。表（左半分）と裏（右半分）で中身を分け、
    回るたびに交互に見えるようにする。上下には、回っているとわかる斜めの金の帯。"""
    s = ''
    for y0 in (0, 1150):
        for k in range(-3, 18):
            x = k * 56
            s += f'<line x1="{x}" y1="{y0 + 140}" x2="{x + 90}" y2="{y0}" stroke="{GOLD}" stroke-width="6" opacity=".6"/>'
        s += f'<line x1="0" x2="848" y1="{y0 + (140 if y0 == 0 else 0)}" y2="{y0 + (140 if y0 == 0 else 0)}" stroke="{GOLD}" stroke-width="4" opacity=".8"/>'
    a, b = 212, 636                            # 表と裏の真ん中
    s += T(a, 330, 'BAR', 92, GOLD_L, SERIF, 700, ls=10) + logo(a, 370, 230)
    s += f'<g filter="url(#glow)">{up_arrow(a, 560, 120, GOLD_L, 18)}' + T(a, 900, '3F', 210, '#fff2d2', NUM, 700) + '</g>'
    s += T(a, 990, 'このビルの3階', 40, WHITE)
    s += T(b, 330, 'OPEN', 86, GOLD_L, NUM, 600, ls=8)
    s += f'<g filter="url(#glow)">' + T(b, 520, SITE['open'], 112, '#fff2d2', NUM, 700) + T(b, 720, f"{int(SITE['close'][:2])}:{SITE['close'][3:]}", 112, '#fff2d2', NUM, 700) + '</g>'
    s += T(b, 605, '｜', 50, GOLD, JP, 500) + T(b, 830, '朝まで営業', 46, WHITE) + T(b, 900, SITE['closed'], 34, '#cfc8bb', JP, 500)
    s += T(b, 1010, 'エレベーターで3階へ', 34, '#d9d3c7', JP, 500)
    return s


def art_spin():
    w, h = 270, 1650
    s = '<rect x="0" y="0" width="270" height="1450" rx="40" fill="#0c0c0f"/>'
    s += '<clipPath id="cylClip"><rect x="0" y="80" width="270" height="1290" rx="24"/></clipPath>'
    s += '<g clip-path="url(#cylClip)"><rect x="0" y="80" width="270" height="1290" fill="url(#faceLit)"/>'
    s += f'<g transform="translate(-77,80)">{spin_band()}</g>'
    s += '<rect x="0" y="80" width="270" height="1290" fill="url(#cylShade)"/></g>'
    s += '<ellipse cx="135" cy="80" rx="135" ry="26" fill="#26262c" stroke="#3a3a42" stroke-width="4"/>'
    s += '<path d="M0 1370 A135 26 0 0 0 270 1370" fill="#1a1a1f"/>'
    s += '<rect x="100" y="1390" width="70" height="170" fill="#1b1b20"/><ellipse cx="135" cy="1600" rx="130" ry="40" fill="#1b1b20"/>'
    return s, w, h


ARTS = {'tower': art_tower, 'arrow': art_arrow, 'neon': art_neon, 'photo': art_photo, 'chalk': art_chalk,
        'digital': art_digital, 'slim': art_slim, 'andon': art_andon, 'spin': art_spin}
SPILL = {'neon': 'spillPink', 'digital': 'spillCool', 'photo': 'spill', 'andon': 'spill'}


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


def prism_group(k, cx, base):
    """三角柱を、角を手前にして斜めから見た形（k は 1mm あたりの大きさ、base は地面）。"""
    top = base - 1700 * k
    fw = 400 * k * .93                      # 斜めから見た1面の幅
    lift = 400 * k * .18                    # 奥へ向かって上がる分
    def face(i, a, b, e, f, shade):
        return (f'<g transform="matrix({a} {b} 0 {k} {e} {f})">{prism_face(i)}'
                f'<rect x="0" y="0" width="400" height="1600" fill="#000" opacity="{shade}"/></g>')
    s = f'<g opacity=".55" filter="url(#softer)"><rect x="{cx - fw}" y="{top}" width="{fw * 2}" height="{1600 * k}" fill="#ffd58c"/></g>'
    s += face(0, fw / 400, lift / 400, cx - fw, top - lift, .12) + face(1, fw / 400, -lift / 400, cx, top, 0)
    s += f'<path d="M{cx - fw} {top - lift} L{cx} {top - lift * 2} L{cx + fw} {top - lift} L{cx} {top} Z" fill="#26262b"/>'
    s += f'<rect x="{cx - fw * .95}" y="{top + 1600 * k - lift}" width="{fw * 1.9}" height="{100 * k + lift}" fill="#1b1b20"/>'
    return s


# ---- 置き方（設置イメージ） --------------------------------------------------------------
def place(art_id, cx):
    """看板を、入口の横の段の上（ビルの敷地の中）に置く。"""
    if art_id == 'prism':
        s = f'<ellipse cx="{cx}" cy="{G + 6}" rx="70" ry="12" fill="url(#spill)"/>'
        return s + prism_group(S, cx, G)
    art, w, h = ARTS[art_id]()
    x0, y0 = cx - w * S / 2, G - h * S
    lit = art_id != 'chalk'
    s = ''
    if lit:
        s += f'<ellipse cx="{cx}" cy="{G + 6}" rx="{max(55, w * S * 1.6)}" ry="12" fill="url(#{SPILL.get(art_id, "spill")})"/>'
        s += f'<g opacity=".45" filter="url(#softer)"><rect x="{x0}" y="{y0}" width="{w * S}" height="{h * S * .85}" fill="{"#ff6fb4" if art_id == "neon" else "#ffd58c"}"/></g>'
    if art_id in ('tower', 'slim', 'andon', 'digital'):
        d = {'tower': 300, 'slim': 200, 'andon': 300, 'digital': 160}[art_id] * S * .45
        s += f'<path d="M{x0 + w * S} {y0} l{d} {-d * .35} v{h * S} l{-d} {d * .35} z" fill="#0a0a0d"/>'
        if art_id == 'andon':
            s += f'<path d="M{x0 + w * S} {y0 + 40 * S} l{d} {-d * .35} v{760 * S} l{-d} {d * .35} z" fill="#e7c78f" opacity=".75"/>'
    s += f'<g transform="translate({x0},{y0}) scale({S})">{art}</g>'
    if art_id == 'spin':
        s += (f'<g fill="none" stroke="#f4dfa8" stroke-width="2" opacity=".75"><path d="M{cx - 18} {y0 + 30} q 18 -10 36 0"/>'
              f'<path d="M{cx + 14} {y0 + 26} l4 4 l-6 2"/></g>')
    return s


# ---- 画像の枠（題名・説明・吹き出し） ------------------------------------------------------
def chrome(no, title, sub, caption):
    badge = (f'<rect x="40" y="36" rx="12" width="{96 if no else 0}" height="46" fill="{GOLD}"/>'
             f'{T(88, 69, "案" + no, 26, "#1a1408", JP, 700) if no else ""}')
    tx = 152 if no else 44
    s = f'<rect x="0" y="0" width="1600" height="120" fill="#000" opacity=".35"/>{badge}'
    s += T(tx, 70, title, 34, '#fff', JP, 700, 'start')
    s += T(tx, 104, sub, 19, '#cfd0d8', JP, 500, 'start')
    s += f'<rect x="0" y="952" width="1600" height="48" fill="#000" opacity=".55"/>'
    s += T(40, 983, caption, 18, '#d9d9e0', JP, 500, 'start')
    s += T(1560, 983, 'ダイニングバー XⅢ クロスリー｜1階入口の看板の提案', 18, '#d9b66f', JP, 700, 'end')
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


def floor_tags():
    s = ''
    for label, y1, y2, hl in (('3F', 258, 392, True), ('2F', 470, 600, False), ('1F', 690, 905, False)):
        a, b = o(0, y1)[1], o(0, y2)[1]
        col = GOLD if hl else '#8a8fa3'
        s += f'<rect x="14" y="{a}" width="6" height="{b - a}" rx="3" fill="{col}" opacity="{.95 if hl else .6}"/>'
        s += T(30, (a + b) / 2 + 10, label, 30, col, NUM, 700, 'start')
        if hl:
            s += T(30, (a + b) / 2 + 40, 'お店', 20, GOLD, JP, 700, 'start')
    return s


def scene_svg(inner_world, overlay):
    vb = ' '.join(map(str, VB))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000">{DEFS}'
            f'<svg x="0" y="0" width="1600" height="1000" viewBox="{vb}" preserveAspectRatio="xMidYMid slice">{inner_world}</svg>'
            f'{overlay}</svg>')


TALL = {'andon': 900, 'chalk': 1450, 'photo': 1350, 'neon': 1500, 'spin': 1650, 'arrow': 1700, 'prism': 1700, 'digital': 1850}
WIDE = {'prism': 760, 'chalk': 640, 'neon': 600, 'photo': 600, 'arrow': 600, 'digital': 640, 'slim': 200, 'andon': 300, 'spin': 270}


def zoom_inset(world, cx, tall, title, sub, box=(1196, 196, 370, 712)):
    """看板のまわりを拡大した枠（同じ絵を、看板の近くだけ切り取って大きく見せる）。"""
    x, y, w, h = box
    zx, zy, zw, zh = x + 14, y + 112, w - 28, h - 126
    wh = tall * S * 1.32 + 24                 # 看板の高さの1.3倍ほどが入るように
    ww = wh * zw / zh
    vb = f'{cx - ww / 2:.1f} {G - tall * S - (wh - tall * S) * .55:.1f} {ww:.1f} {wh:.1f}'
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="#0b0d14" opacity=".93" stroke="{GOLD}" stroke-width="1.5"/>'
    s += T(x + 18, y + 38, title, 22, '#fff', JP, 700, 'start')
    for i, line in enumerate(wrap(sub, 18)[:2]):
        s += T(x + 18, y + 70 + i * 26, line, 17 if i else 18, '#c9cad3' if i == 0 else '#9ea3b2', JP, 500, 'start')
    s += f'<clipPath id="zoomClip"><rect x="{zx}" y="{zy}" width="{zw}" height="{zh}" rx="10"/></clipPath>'
    s += f'<g clip-path="url(#zoomClip)"><svg x="{zx}" y="{zy}" width="{zw}" height="{zh}" viewBox="{vb}" preserveAspectRatio="xMidYMid slice">{world}</svg></g>'
    s += f'<rect x="{zx + 10}" y="{zy + 10}" width="64" height="30" rx="8" fill="#000" opacity=".6"/>' + T(zx + 42, zy + 31, '拡大', 17, GOLD_L, JP, 700)
    return s


def scene(p, cx):
    world = building() + people(820) + place(p['id'], cx) + pole_and_wires()
    tall = TALL.get(p['id'], 1800)
    over = floor_tags()
    sx, sy = o(cx + WIDE.get(p['id'], 450) * S / 2, G - tall * S * .6)
    over += f'<line x1="{sx}" y1="{sy}" x2="1196" y2="{196 + 360}" stroke="{GOLD}" stroke-width="2" opacity=".85"/><circle cx="{sx}" cy="{sy}" r="5" fill="{GOLD}"/>'
    over += zoom_inset(world, cx, tall, p['short'], p['size'])
    over += chrome(p['no'], p['name'], p['catch'], '設置イメージ（イラスト・夜）　入口のガラス扉の横、ビルの敷地の中に置いたところ')
    return scene_svg(world, over)


def scene_now():
    world = building() + people(820) + pole_and_wires()
    over = floor_tags()
    x3, y3 = o(800, 320)
    over += callout(x3, y3, 230, 180, ['3階がお店。でも外からは気づけない', '中は見えず、窓は電線にも隠れる'], 'start')
    xe, ye = o(1195, 800)
    over += callout(xe, ye, 1575, 520, ['入口はこのガラス扉', '隣のお店の扉と並び、わかりにくい'], 'end')
    xb, yb = o(1376, 770)
    over += callout(xb, yb, 1575, 760, ['今の看板は、案内板の', '3階の小さなプレートだけ'], 'end')
    over += chrome('', '今のようす（夜）', '3階にバーがあること、入口がどこかが、ビルの前から伝わっていない', '今のようす（イラスト）　ストリートビュー（2024年11月）の建物をもとに描き起こしたもの')
    return scene_svg(world, over)


# ---- デザイン（看板の正面・寸法入り） ------------------------------------------------------
def dim_h(x1, x2, y, label):
    return (f'<g stroke="#8d93a3" stroke-width="1.5"><line x1="{x1}" x2="{x2}" y1="{y}" y2="{y}"/><line x1="{x1}" x2="{x1}" y1="{y - 8}" y2="{y + 8}"/>'
            f'<line x1="{x2}" x2="{x2}" y1="{y - 8}" y2="{y + 8}"/></g>' + T((x1 + x2) / 2, y + 28, label, 18, '#aeb3c2', NUM, 600))


def dim_v(x, y1, y2, label):
    return (f'<g stroke="#8d93a3" stroke-width="1.5"><line x1="{x}" x2="{x}" y1="{y1}" y2="{y2}"/><line x1="{x - 8}" x2="{x + 8}" y1="{y1}" y2="{y1}"/>'
            f'<line x1="{x - 8}" x2="{x + 8}" y1="{y2}" y2="{y2}"/></g>'
            f'<text x="{x - 14}" y="{(y1 + y2) / 2}" font-family="{NUM}" font-size="18" font-weight="600" fill="#aeb3c2" text-anchor="middle" '
            f'transform="rotate(-90 {x - 14} {(y1 + y2) / 2})">{esc(label)}</text>')


def place_design(art_svg, w, h, box=(170, 150, 740, 700), dims=True, label_w=None, label_h=None, lit=True):
    bx, by, bw, bh = box
    k = min(bw / w, bh / h)
    x0 = bx + (bw - w * k) / 2
    y0 = by + (bh - h * k)
    s = (f'<g opacity=".5" filter="url(#halo)"><rect x="{x0}" y="{y0}" width="{w * k}" height="{h * k * .8}" fill="#ffcf7a" opacity=".18"/></g>'
         if lit else '')
    s += f'<g transform="translate({x0},{y0}) scale({k})">{art_svg}</g>'
    s += f'<line x1="{bx - 40}" x2="{bx + bw + 40}" y1="{y0 + h * k}" y2="{y0 + h * k}" stroke="#4a4f5c" stroke-width="2"/>'
    if dims:
        s += dim_h(x0, x0 + w * k, y0 + h * k + 26, label_w or f'{w} mm')
        s += dim_v(x0 - 34, y0, y0 + h * k, label_h or f'{h} mm')
    return s


def wrap(text, n):
    """n 文字ほどで折り返す。なるべく「／」「、」「）」の後ろで折り、英数字の途中では折らない。"""
    out, rest = [], text
    while len(rest) > n:
        cut = max((rest.rfind(c, 0, n + 1) + 1 for c in '／、）'), default=0)
        if cut < n * .5:
            cut = n
            while cut > 1 and rest[cut - 1].isascii() and rest[cut - 1].isalnum() and rest[cut].isascii() and rest[cut].isalnum():
                cut -= 1
        out.append(rest[:cut])
        rest = rest[cut:]
    return out + [rest] if rest else out


def spec_panel(p, x=980, y=190):
    s = f'<rect x="{x}" y="{y}" width="560" height="{100 + 98 * len(p["spec"])}" rx="18" fill="#0b0d13" opacity=".7" stroke="#2c303b"/>'
    s += T(x + 32, y + 52, 'デザインのポイント', 24, GOLD, JP, 700, 'start')
    for i, (k, v) in enumerate(p['spec']):
        yy = y + 104 + i * 98
        s += T(x + 32, yy, k, 18, '#9ea3b2', JP, 700, 'start')
        lines = wrap(v, 24)
        for li, line in enumerate(lines[:2]):
            s += T(x + 32, yy + 34 + li * 28, line, 22, '#f2f2f5', JP, 500, 'start')
    s += T(x + 32, y + 150 + 98 * len(p['spec']), '※イメージです。色・文字・大きさは、製作会社と相談して決めます。', 16, '#8d92a1', JP, 500, 'start')
    return s


def design_svg(p):
    body = '<rect x="0" y="0" width="1600" height="1000" fill="url(#bgDesign)"/><rect x="0" y="0" width="1600" height="1000" fill="url(#grid)"/>'
    pid = p['id']
    if pid == 'prism':
        for i in range(3):
            body += place_design(prism_face(i), 400, 1600, box=(110 + i * 270, 220, 230, 620), dims=(i == 0))
            body += T(110 + i * 270 + 115, 205, f'面{i + 1}', 20, GOLD, JP, 700)
        body += T(450, 935, '3つの面を広げたところ（どの面も光る）', 17, '#8d92a1', JP, 500)
    elif pid == 'spin':
        a, w, h = art_spin()
        body += place_design(a, w, h, box=(120, 150, 260, 700))
        band = (f'<rect x="0" y="0" width="848" height="1290" rx="8" fill="url(#faceLit)"/>'
                f'<clipPath id="bandClip"><rect x="0" y="0" width="848" height="1290" rx="8"/></clipPath><g clip-path="url(#bandClip)">{spin_band()}</g>')
        band += '<line x1="424" x2="424" y1="150" y2="1140" stroke="#3a3a42" stroke-width="3" stroke-dasharray="14 12"/>'
        body += place_design(band, 848, 1290, box=(450, 200, 470, 600), label_w='848 mm（ひと回り）', label_h='1290 mm')
        body += T(560, 190, '表', 22, GOLD, JP, 700) + T(810, 190, '裏', 22, GOLD, JP, 700)
        body += T(685, 935, '円柱のまわりを広げたところ（回るたびに表と裏が交互に見える）', 17, '#8d92a1', JP, 500)
    else:
        a, w, h = ARTS[pid]()
        body += place_design(a, w, h, lit=(pid != 'chalk'))
    over = chrome(p['no'], p['name'], 'デザイン案（正面）・夜に点灯したところ' if pid != 'chalk' else 'デザイン案（正面）・夜にライトで照らしたところ',
                  f'デザイン案　大きさの目安 {p["size"]}　相場の目安 {p["price"]}')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000">{DEFS}{body}'
            f'{spec_panel(p)}{over}</svg>')


# ---- 一覧用の画像（看板だけ）・大きさ比べ ----------------------------------------------------
def sign_alone(pid, k, cx, base, halo=True):
    """看板だけを、地面 base の上の cx に、1mm = k の大きさで描く。"""
    if pid == 'prism':
        return prism_group(k, cx, base)
    a, w, h = ARTS[pid]()
    x0, y0 = cx - w * k / 2, base - h * k
    s = ''
    if halo and pid != 'chalk':
        col = '#ff6fb4' if pid == 'neon' else ('#cfe7ff' if pid == 'digital' else '#ffd58c')
        s += f'<g opacity=".45" filter="url(#softer)"><rect x="{x0}" y="{y0}" width="{w * k}" height="{h * k * .85}" fill="{col}"/></g>'
    return s + f'<g transform="translate({x0},{y0}) scale({k})">{a}</g>'


def thumb_svg(p):
    pid = p['id']
    a_h = {'prism': 1700}.get(pid) or ARTS[pid]()[2]
    a_w = {'prism': 760}.get(pid) or ARTS[pid]()[1]
    k = min(560 / a_h, 520 / a_w)
    body = '<rect x="0" y="0" width="800" height="800" fill="url(#bgDesign)"/>'
    body += '<ellipse cx="400" cy="690" rx="300" ry="34" fill="url(#spill)" opacity=".55"/>'
    body += '<line x1="60" x2="740" y1="690" y2="690" stroke="#3a3f4c" stroke-width="2"/>'
    body += sign_alone(pid, k, 400, 690)
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800">{DEFS}{body}</svg>'


def person(x, base, k, label=True):
    h = 1700 * k
    u = h / 17                                # 体の大きさの単位
    s = (f'<g fill="#5f6577"><circle cx="{x}" cy="{base - h + u * 1.1}" r="{u * 1.1}"/>'
         f'<path d="M{x - u * 1.6} {base - h + u * 2.6} Q{x} {base - h + u * 2.2} {x + u * 1.6} {base - h + u * 2.6} '
         f'L{x + u * 2} {base - h + u * 9} L{x + u * 1.2} {base - h + u * 9} L{x + u * 1} {base} L{x + u * .2} {base} '
         f'L{x} {base - h + u * 10} L{x - u * .2} {base} L{x - u * 1} {base} L{x - u * 1.2} {base - h + u * 9} '
         f'L{x - u * 2} {base - h + u * 9} Z"/></g>')
    if label:
        s += T(x, base + 40, '人', 20, '#aeb3c2', JP, 700) + T(x, base + 66, '170cm', 18, '#8d92a1', NUM, 600)
    return s


LINEUP_W = {'prism': 560}


def lineup_width(k=0.3):
    """大きさ比べの画像の幅（扉・人・10案を並べた分）。"""
    x = 70 + 1300 * k + 110 + 120
    for p in DATA['proposals']:
        x += (LINEUP_W.get(p['id']) or ARTS[p['id']]()[1]) * k + 82
    return int(x + 40)


def lineup_svg():
    H, base, k = 1000, 800, 0.3
    W = lineup_width(k)
    body = f'<rect x="0" y="0" width="{W}" height="{H}" fill="url(#bgDesign)"/><rect x="0" y="0" width="{W}" height="{H}" fill="url(#grid)"/>'
    body += T(60, 78, '10案の大きさ比べ', 40, '#fff', JP, 700, 'start')
    body += T(60, 122, '同じ縮尺で、人（170cm）と入口の扉の横に並べたところ', 22, '#b9bcc8', JP, 500, 'start')
    body += f'<line x1="40" x2="{W - 40}" y1="{base}" y2="{base}" stroke="#4a4f5c" stroke-width="3"/>'
    # 入口のガラス扉（目安）と人
    dx, dw, dh = 70, 1300 * k, 2100 * k
    body += (f'<g fill="#cfd8e3" fill-opacity=".08" stroke="#9aa3ad" stroke-width="3">'
             f'<rect x="{dx}" y="{base - dh}" width="{dw / 2}" height="{dh}"/><rect x="{dx + dw / 2}" y="{base - dh}" width="{dw / 2}" height="{dh}"/></g>')
    body += T(dx + dw / 2, base + 40, '入口の扉', 20, '#aeb3c2', JP, 700) + T(dx + dw / 2, base + 66, '高さ約2.1m（目安）', 18, '#8d92a1', JP, 500)
    x = dx + dw + 110
    body += person(x, base, k)
    x += 120
    for p in DATA['proposals']:
        pid = p['id']
        w = LINEUP_W.get(pid) or ARTS[pid]()[1]
        h = 1700 if pid == 'prism' else ARTS[pid]()[2]
        cx = x + w * k / 2
        body += sign_alone(pid, k, cx, base)
        body += T(cx, base - h * k - 18, f'{h / 10:.0f}cm', 18, '#c9a45c', NUM, 600)
        body += f'<rect x="{cx - 24}" y="{base + 18}" width="48" height="28" rx="7" fill="{GOLD}"/>' + T(cx, base + 39, p['no'], 18, '#1a1408', NUM, 700)
        for i, line in enumerate(p['short_lines']):
            body += T(cx, base + 76 + i * 26, line, 19, '#e6e7ec', JP, 700)
        x += w * k + 82
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{DEFS}{body}</svg>'


# ---- 書き出し ---------------------------------------------------------------------
PLACE_X = {'slim': 1290, 'andon': 1300}


def render(b, svg, name, tmp, size=(1600, 1000), dsf=1.5, web=(1200, 750), jpg=True):
    """SVG を Edge で画像にする。jpg は保存用（大きい）、webp はページに出す用（小さい）。"""
    import base64
    w, h = size
    page = tmp / 'render.html'
    page.write_text('<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#000}svg{display:block}</style>'
                    f'</head><body>{svg}</body></html>', encoding='utf-8')
    b.open(page.as_uri(), {'width': w, 'height': h, 'deviceScaleFactor': dsf, 'mobile': False})
    b.wait(1.2)
    r = b.call('Page.captureScreenshot', {'format': 'png', 'clip': {'x': 0, 'y': 0, 'width': w, 'height': h, 'scale': 1}})
    im = Image.open(io.BytesIO(base64.b64decode(r['data']))).convert('RGB')
    if jpg:
        im.save(OUT / f'{name}.jpg', 'JPEG', quality=86, optimize=True, progressive=True)
    im.resize(web, Image.LANCZOS).save(OUT / f'{name}.webp', 'WEBP', quality=80, method=6)
    if b.errors:
        print('  エラー:', b.errors[:3])
    return im.size


def main():
    only = set(sys.argv[1].split(',')) if len(sys.argv) > 1 else None
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    b = shoot.Browser()
    try:
        if not only or '00' in only:
            print('00 今のようす', render(b, scene_now(), 'sign-00-now', tmp))
        if not only or 'lineup' in only:
            lw = lineup_width()
            print('大きさ比べ', render(b, lineup_svg(), 'sign-lineup', tmp, size=(lw, 1000), dsf=1, web=(lw // 2, 500)))
        for p in DATA['proposals']:
            if only and p['no'] not in only:
                continue
            cx = PLACE_X.get(p['id'], 1310)
            print(p['no'], p['name'], render(b, scene(p, cx), f'sign-{p["no"]}-{p["id"]}-scene', tmp),
                  render(b, design_svg(p), f'sign-{p["no"]}-{p["id"]}-design', tmp),
                  render(b, thumb_svg(p), f'sign-{p["no"]}-{p["id"]}-thumb', tmp, size=(800, 800), dsf=1, web=(600, 600), jpg=False))
    finally:
        b.close()
    # まとめてダウンロードする ZIP（画像はすでに JPEG なので圧縮しない）
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_STORED) as z:
        for f in sorted(OUT.glob('sign-*.jpg')):
            z.write(f, f'xiii-sign-ideas/{f.name}')
    print('ZIP', ZIP.name, f'{ZIP.stat().st_size // 1024} KB')


if __name__ == '__main__':
    main()
