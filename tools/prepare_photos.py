"""依頼者から預かった写真を、Web で使う形に整える。

- 大きさを数段階に縮め、WebP で書き出す（画面の幅に合わせてブラウザが選ぶ）。
- 撮影情報（EXIF。撮った場所が入っていることがある）は書き出さない。
- テレビに映っている人の顔はぼかす（写っているのは番組の出演者で、使ってよいか分からないため）。
- チラシの「X-III」ロゴを、黒い背景を抜いた PNG にする（元データが届いたら差し替える）。

使い方: python -I -X utf8 tools/prepare_photos.py <写真のフォルダ> <書き出し先>
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

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


logo = extract_logo((55, 772, 525, 1028))
logo.save(OUT / 'logo-x-iii.png', optimize=True)
print('logo', logo.size)

# ロゴを白一色にしたもの（明るい背景の案では色を付け替えて使う）。
mono = Image.new('RGBA', logo.size, (255, 255, 255, 0))
mono.putalpha(logo.getchannel('A'))
mono.save(OUT / 'logo-x-iii-white.png', optimize=True)

# ブラウザのタブとホーム画面のアイコン（黒地にロゴ。32px は小さいので「X」だけ）。
icon = Image.new('RGBA', (180, 180), (11, 11, 11, 255))
il = logo.resize((150, round(logo.height * 150 / logo.width)), Image.LANCZOS)
icon.paste(il, (15, (180 - il.height) // 2), il)
icon.convert('RGB').save(OUT / 'icon-180.png', optimize=True)
x_only = logo.crop((0, 40, 160, logo.height - 30))
x_only = x_only.crop(x_only.getbbox())
small = Image.new('RGBA', (32, 32), (11, 11, 11, 255))
xs = x_only.resize((26, round(x_only.height * 26 / x_only.width)), Image.LANCZOS)
small.paste(xs, (3, (32 - xs.height) // 2), xs)
small.convert('RGB').save(OUT / 'icon-32.png', optimize=True)

lw = 560
lg = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
og.paste(lg, ((1200 - lw) // 2, (630 - lg.height) // 2), lg)
og.save(OUT / 'og.jpg', 'JPEG', quality=85, optimize=True, progressive=True)
print('og', og.size)
