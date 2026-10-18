"""案11（機能モリモリ版）で使う「見本の写真」を、ウィキメディア・コモンズから取ってきて Web 用に整える。

  python -I -X utf8 tools/get_sample_photos.py

どれも、誰でも使ってよい条件（著作権放棄 CC0、または作者名を書けば使える CC BY）の写真だけ。
作者名と条件は site.json の sample_photos に書いてあり、ページの写真の下に表示する。
お店の写真が届いたら差し替える（見本なので、本番では使わない）。
"""
import io
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs' / 'assets' / 'img'
SITE = json.loads((ROOT / 'site.json').read_text(encoding='utf-8'))

# 書き出す名前 → 切り抜く範囲（元の写真に対する割合: 左, 上, 右, 下）と幅の段階
CROPS = {
    'sample-bartender': ((0.22, 0.02, 0.66, 1.0), [900, 600]),
    'sample-cocktail': ((0.05, 0.0, 0.95, 1.0), [1200, 720]),
    'sample-stir': ((0.0, 0.05, 1.0, 0.85), [900, 600]),
    'sample-julep': ((0.0, 0.12, 1.0, 0.82), [900, 600]),
}


def fetch(title):
    q = urllib.parse.urlencode({'action': 'query', 'titles': 'File:' + title, 'prop': 'imageinfo',
                                'iiprop': 'url', 'iiurlwidth': 1600, 'format': 'json'})
    req = urllib.request.Request('https://commons.wikimedia.org/w/api.php?' + q, headers={'User-Agent': 'crossley-proposal/1.0'})
    page = next(iter(json.load(urllib.request.urlopen(req, timeout=60))['query']['pages'].values()))
    url = page['imageinfo'][0]['thumburl']
    req = urllib.request.Request(url, headers={'User-Agent': 'crossley-proposal/1.0'})
    return Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=120).read())).convert('RGB')


def main():
    for name, ((l, t, r, b), widths) in CROPS.items():
        info = SITE['sample_photos'][name]
        im = fetch(info['title'])
        im = im.crop((round(im.width * l), round(im.height * t), round(im.width * r), round(im.height * b)))
        for w in widths:
            w = min(w, im.width)
            im.resize((w, round(im.height * w / im.width)), Image.LANCZOS).save(OUT / f'{name}-{w}.webp', 'WEBP', quality=78, method=6)
        print(name, im.size, info['license'], info['artist'])


if __name__ == '__main__':
    sys.exit(main())
