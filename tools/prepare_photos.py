"""依頼者から預かった写真を、Web で使う形に整える。

- 大きさを数段階に縮め、WebP で書き出す（画面の幅に合わせてブラウザが選ぶ）。
- 撮影情報（EXIF。撮った場所が入っていることがある）は書き出さない。
- テレビに映っている人の顔はぼかす（写っているのは番組の出演者で、使ってよいか分からないため）。
- チラシの「X-III」ロゴを、黒い背景を抜いた PNG にする（元データが届いたら差し替える）。
  ロゴの下の「CROSS THREE」は「CROSSLEY」に描き直す（書体は Barlow。tools/fonts）。

使い方: python -I -X utf8 tools/prepare_photos.py <写真のフォルダ> <書き出し先>
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

# 書き出す名前 → (元のファイル, 幅の段階)
PHOTOS = {
    'counter-dark': ('S__98983957_0.jpg', [2400, 1600, 960]),
    'backbar': ('S__98983953_0.jpg', [2400, 1600, 960]),
    'counter-wide': ('S__98983951_0.jpg', [1108, 720]),
    'neon-counter': ('S__98983955_0.jpg', [1477, 960]),
    'tables': ('S__98983954_0.jpg', [1108, 720]),
    'darts': ('S__98983956_0.jpg', [1108, 720]),
}

# テレビの画面の位置（元の写真 1108x1477 の座標）。
TV_BOX = (40, 355, 352, 590)


def load(name):
    im = Image.open(SRC / name)
    im = ImageOps.exif_transpose(im)
    return im.convert('RGB')


def blur_tv(im):
    region = im.crop(TV_BOX)
    # 顔が分からなくなるまで強くぼかし、少し暗くして「点いている画面」に見せる。
    region = region.resize((region.width // 12, region.height // 12)).resize(region.size, Image.BILINEAR)
    region = region.filter(ImageFilter.GaussianBlur(14))
    region = Image.blend(region, Image.new('RGB', region.size, (10, 12, 20)), 0.35)
    mask = Image.new('L', region.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, region.width - 1, region.height - 1), radius=6, fill=255)
    im.paste(region, TV_BOX[:2], mask)
    return im


sizes = {}
for key, (fname, widths) in PHOTOS.items():
    im = load(fname)
    if key == 'tables':
        im = blur_tv(im)
    for w in widths:
        w = min(w, im.width)
        h = round(im.height * w / im.width)
        im.resize((w, h), Image.LANCZOS).save(OUT / f'{key}-{w}.webp', 'WEBP', quality=78, method=6)
    sizes[key] = (im.width, im.height, widths)
    print(key, im.size, widths)

# SNS で共有したときの画像（1200x630、JPEG。WebP を読めない SNS があるため）。
og = load('S__98983957_0.jpg')
og = ImageOps.fit(og, (1200, 630), Image.LANCZOS, centering=(0.6, 0.55))
og = Image.blend(og, Image.new('RGB', og.size, (0, 0, 0)), 0.45)


def extract_logo(box, threshold=48, full=170):
    """黒い背景の上の白・金の文字を、背景を抜いた RGBA にする（黒を引いて不透明度に戻す）。"""
    flyer = load('S__98983952_0.jpg').crop(box)
    px = flyer.load()
    out = Image.new('RGBA', flyer.size)
    po = out.load()
    for y in range(flyer.height):
        for x in range(flyer.width):
            r, g, b = px[x, y]
            m = max(r, g, b)
            a = 0.0 if m <= threshold else min(1.0, (m - threshold) / (full - threshold))
            if a == 0:
                po[x, y] = (0, 0, 0, 0)
            else:
                # 背景が黒なので、見えている色 = 文字の色 × 不透明度。割り戻し、色味を保ったまま 255 に収める。
                k = min(1 / a, 255 / m)
                po[x, y] = (round(r * k), round(g * k), round(b * k), round(a * 255))
    return out.crop(out.getbbox())


TAGLINE_TEXT = 'CROSSLEY'
TAGLINE_FONT = Path(__file__).resolve().parent / 'fonts' / 'Barlow-Regular.ttf'  # SIL Open Font License（tools/fonts/OFL.txt）


def runs(xs):
    """並んだ x の集まりを、続いている区間 [(始め, 終わり), …] に分ける。"""
    out = []
    for x in xs:
        if out and x == out[-1][1] + 1:
            out[-1][1] = x
        else:
            out.append([x, x])
    return out


def replace_tagline(logo, text):
    """チラシのロゴの下の行（左右の金の線と「CROSS THREE」）を消し、同じ色・高さ・文字間隔で text と線を描き直す。
    英語の店名は CROSSLEY（利用者の指摘。食べログも CROSSLEY。チラシには CROSS THREE と印刷されている）。"""
    W, H = logo.size
    alpha = logo.getchannel('A')
    px = logo.load()

    def opaque(y):
        return [x for x in range(W) if alpha.getpixel((x, y)) > 60]

    # 下の行の範囲: いちばん下から上へ、何も無い行に当たるまで
    top = H - 1
    while top > 0 and opaque(top - 1):
        top -= 1
    rows = list(range(top, H))
    line_rows = [y for y in rows if len(opaque(y)) > W * 0.5]
    text_px = [(x, y) for y in rows if y not in line_rows for x in opaque(y)]
    tx0, tx1 = min(x for x, _ in text_px), max(x for x, _ in text_px)
    ty0, ty1 = min(y for _, y in text_px), max(y for _, y in text_px)
    line = runs(opaque(line_rows[0]))
    gap_l, gap_r = tx0 - line[0][1] - 1, line[-1][0] - tx1 - 1
    # 文字の色（不透明さで重みを付けた平均）
    tot = [0, 0, 0, 0]
    for x, y in text_px:
        r, g, b, a = px[x, y]
        tot[0] += r * a; tot[1] += g * a; tot[2] += b * a; tot[3] += a
    color = tuple(round(c / tot[3]) for c in tot[:3])
    # 線の1列（縦の色と不透明さ）を、元の左の線の真ん中から写し取る
    line_col = logo.crop((line[0][1] // 2, top, line[0][1] // 2 + 1, H))

    # 元の文字と同じ高さ（H の高さ）になる大きさを探し、元の幅になる文字間隔を求めて、新しい文字に使う
    scale = 4
    cap = ty1 - ty0  # O や S のはみ出し（約1px）を除いた高さ
    size = 8.0
    while True:
        font = ImageFont.truetype(str(TAGLINE_FONT), round(size * scale))
        hb = font.getbbox('H')
        if hb[3] - hb[1] >= cap * scale:
            break
        size += 0.25

    def draw(s, track):
        adv = [font.getlength(c) for c in s]
        w = int(sum(adv) + track * (len(s) - 1)) + 8 * scale
        m = Image.new('L', (w, (cap + 8) * scale), 0)
        d = ImageDraw.Draw(m)
        x, y = 0, 4 * scale - hb[1]
        for c, a in zip(s, adv):
            d.text((x, y), c, font=font, fill=255)
            x += a + track
        return m.crop(m.getbbox())

    natural = draw('CROSS THREE', 0).width
    track = ((tx1 - tx0 + 1) * scale - natural) / len('CROSS THRE')
    m = draw(text, track)
    m = m.resize((round(m.width / scale), round(m.height / scale)), Image.LANCZOS)

    # 下の行を消して、描き直す
    clear = Image.new('RGBA', (W, H - top), (0, 0, 0, 0))
    logo.paste(clear, (0, top))
    nx0 = round((tx0 + tx1 + 1) / 2 - m.width / 2)
    for x in list(range(0, nx0 - gap_l)) + list(range(nx0 + m.width + gap_r, W)):
        logo.paste(line_col, (x, top))
    glyphs = Image.new('RGBA', m.size, color + (0,))
    glyphs.putalpha(m)
    logo.alpha_composite(glyphs, (nx0, ty0 + round((ty1 - ty0 + 1 - m.height) / 2)))
    return logo


logo = extract_logo((55, 772, 525, 1028))
logo = replace_tagline(logo, TAGLINE_TEXT)
logo.save(OUT / 'logo-x-iii.png', optimize=True)
print('logo', logo.size)

# ロゴを白一色にしたもの（明るい背景の案では色を付け替えて使う）。
mono = Image.new('RGBA', logo.size, (255, 255, 255, 0))
mono.putalpha(logo.getchannel('A'))
mono.save(OUT / 'logo-x-iii-white.png', optimize=True)

# ホーム画面のアイコン（金の地に黒のロゴ）。黒地に白い X だと、X（旧 Twitter）のアプリのアイコンと似て見えるため。
GOLD = (201, 164, 98)
icon = Image.new('RGBA', (180, 180), GOLD + (255,))
dark = Image.new('RGBA', logo.size, (14, 12, 10, 0))
dark.putalpha(logo.getchannel('A'))
il = dark.resize((146, round(logo.height * 146 / logo.width)), Image.LANCZOS)
icon.alpha_composite(il, (17, (180 - il.height) // 2))
icon.convert('RGB').save(OUT / 'icon-180.png', optimize=True)
# 32px（タブ）は、金の丸に黒で「XIII」。白い「X」だけだと X（旧 Twitter）のマークと見分けが付かないため（利用者の指摘）。
# ロゴの大きな文字から X と III を切り出し、ハイフンを抜いて詰める。8倍の大きさで描いてから縮める。
alpha = logo.getchannel('A')
big_rows = (44, 196)  # 大きな文字の行（上の「クロスリー」と下の行を除く）
cols = [x for x in range(logo.width) if any(alpha.getpixel((x, y)) > 60 for y in range(*big_rows, 2))]
letters = runs(cols)  # X・ハイフン・I・I・I
glyph_x = logo.crop((letters[0][0], big_rows[0], letters[0][1] + 1, big_rows[1]))
glyph_iii = logo.crop((letters[2][0], big_rows[0], letters[-1][1] + 1, big_rows[1]))
mark = Image.new('RGBA', (glyph_x.width + glyph_iii.width + 14, glyph_x.height), (0, 0, 0, 0))
mark.alpha_composite(glyph_x, (0, 0))
mark.alpha_composite(glyph_iii, (glyph_x.width + 14, 0))
mark = mark.crop(mark.getbbox())
ink = Image.new('RGBA', mark.size, (14, 12, 10, 0))
ink.putalpha(mark.getchannel('A'))
big = 32 * 8
coin = Image.new('RGBA', (big, big), (0, 0, 0, 0))
ImageDraw.Draw(coin).ellipse((0, 0, big - 1, big - 1), fill=GOLD + (255,))
k = min(big * 0.74 / ink.width, big * 0.52 / ink.height)
ink = ink.resize((round(ink.width * k), round(ink.height * k)), Image.LANCZOS)
coin.alpha_composite(ink, ((big - ink.width) // 2, (big - ink.height) // 2))
coin.resize((32, 32), Image.LANCZOS).save(OUT / 'icon-32.png', optimize=True)

lw = 560
lg = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
og.paste(lg, ((1200 - lw) // 2, (630 - lg.height) // 2), lg)
og.save(OUT / 'og.jpg', 'JPEG', quality=85, optimize=True, progressive=True)
print('og', og.size)
