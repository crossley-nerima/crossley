"""練馬駅から店までの道順の図（SVG）を、OpenStreetMap の地図データから作る。

  python -I -X utf8 tools/make_route_map.py [地図データ.json]

地図データを渡さなければ、Overpass API から取ってくる（取ったものは tools/osm-cache.json に残し、次からはそれを使う）。できた図は src/_parts/route-map.svg に置き、
build.py が各案の「練馬駅からの行き方」に差し込む（色は各案の CSS の --rm-… で変える）。
道の形・建物・目印の位置は地図データのまま。道順（どこを歩くか）と、目印の名前の出し方はこのファイルに書く。
"""
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'src' / '_parts' / 'route-map.svg'
CACHE = ROOT / 'tools' / 'osm-cache.json'  # 取った地図データ（記録には入れない）

# 店の位置（Google マップの登録の位置）。図の座標は、ここから東へ何 m・南へ何 m かで表す。
SHOP = (35.7360887, 139.6539949)
COS = math.cos(math.radians(SHOP[0]))

# 図に入れる範囲（m）と縮尺（1m を何単位で描くか）
X0, X1, Y0, Y1 = -120, 130, -240, 95
S = 1.25

# 歩く道（m）。駅の南側から「練馬駅前」交差点で千川通りを渡り、マクドナルドの角を南へ。
ROUTE = [(64, -183), (60, -158), (59, -150), (61, -136), (25, -128), (-10, -123),
         (-6, -90), (2, -44), (6, -12), (7, -5), (4, -1)]
# 番号の位置（site.json の route の順番と合わせる）
STEPS = [(59, -150), (-10, -123), (-4, -68), (-8, 10)]

# 目印（地図データの名前 → 図に出す名前、文字を置く側）
LANDMARKS = {
    'マクドナルド': ('マクドナルド', 'right'),
    '大鳥神社': ('大鳥神社', 'right'),
    'ファミリーマート': ('ファミリーマート', 'right'),
    '七輪焼肉牛繁': ('七輪焼肉 牛繁', 'left'),
}
ROAD_LABELS = [('千川通り', -78, -121, -8.5), ('目白通り', 40, 87, 4.0)]
STATION = {'cx': -4, 'cy': -205, 'w': 176, 'h': 30, 'angle': -5}

ROAD_W = {'primary': 12, 'secondary': 12, 'tertiary': 8, 'residential': 5, 'unclassified': 5, 'living_street': 5}


def xy(lat, lon):
    return ((lon - SHOP[1]) * 111320 * COS, (SHOP[0] - lat) * 111320)


def to_svg(p):
    return (round((p[0] - X0) * S, 1), round((p[1] - Y0) * S, 1))


def fetch():
    lat_s, lat_n = SHOP[0] - Y1 / 111320 - 0.0005, SHOP[0] - Y0 / 111320 + 0.0005
    lon_w, lon_e = SHOP[1] + X0 / (111320 * COS) - 0.0005, SHOP[1] + X1 / (111320 * COS) + 0.0005
    bb = f'{lat_s},{lon_w},{lat_n},{lon_e}'
    q = (f'[out:json][timeout:60];(way({bb})["highway"];way({bb})["railway"="rail"];'
         f'way({bb})["building"];node({bb})["name"];);out body geom;')
    req = urllib.request.Request('https://overpass-api.de/api/interpreter',
                                 data=urllib.parse.urlencode({'data': q}).encode(),
                                 headers={'User-Agent': 'crossley-route-map'})
    for i in range(4):
        try:
            data = json.load(urllib.request.urlopen(req, timeout=120))
            break
        except urllib.error.HTTPError as e:
            # 502・504・429 は混んでいるだけのことが多いので、少し待って取り直す。
            if e.code not in (429, 502, 503, 504) or i == 3:
                raise
            print(f'地図データの取得先が混んでいます（{e.code}）。取り直します')
            time.sleep(15 * (i + 1))
    CACHE.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    return data


def inside(p, poly):
    x, y = p
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def simplify(pts, tol=0.8):
    """細かすぎる折れ線を間引く（Douglas-Peucker）。"""
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    L = math.hypot(x2 - x1, y2 - y1) or 1e-9
    far, idx = 0, 0
    for i, (x, y) in enumerate(pts[1:-1], 1):
        dd = abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1) / L
        if dd > far:
            far, idx = dd, i
    if far <= tol:
        return [pts[0], pts[-1]]
    return simplify(pts[:idx + 1], tol)[:-1] + simplify(pts[idx:], tol)


def near_box(pts, m=40):
    return any(X0 - m < x < X1 + m and Y0 - m < y < Y1 + m for x, y in pts)


def path_d(pts):
    q = [to_svg(p) for p in pts]
    return 'M' + ' L'.join(f'{x} {y}' for x, y in q)


def main():
    if len(sys.argv) > 1:
        data = json.load(open(sys.argv[1], encoding='utf-8'))
    elif CACHE.exists():
        print(f'前に取った地図データを使います（取り直すときは {CACHE.name} を消す）')
        data = json.load(open(CACHE, encoding='utf-8'))
    else:
        data = fetch()
    els = data['elements']
    W, H = round((X1 - X0) * S), round((Y1 - Y0) * S)

    roads = {w: [] for w in sorted(set(ROAD_W.values()))}
    rails = []
    shop_poly = None
    for e in els:
        t = e.get('tags', {})
        if e['type'] != 'way' or 'geometry' not in e:
            continue
        pts = [xy(g['lat'], g['lon']) for g in e['geometry']]
        if not near_box(pts):
            continue
        if t.get('highway') in ROAD_W:
            roads[ROAD_W[t['highway']]].append(path_d(simplify(pts)))
        elif t.get('railway') == 'rail':
            rails.append(path_d(simplify(pts)))
        elif 'building' in t and inside((0, 0), pts):
            shop_poly = pts
    if not shop_poly:
        raise SystemExit('店の建物が地図データに見つかりません')

    marks = []
    found = set()
    for e in els:
        t = e.get('tags', {})
        if e['type'] == 'node' and t.get('name') in LANDMARKS:
            p = xy(e['lat'], e['lon'])
            if X0 < p[0] < X1 and Y0 < p[1] < Y1:
                marks.append((LANDMARKS[t['name']], p))
                found.add(t['name'])
    missing = set(LANDMARKS) - found
    if missing:
        raise SystemExit(f'目印が地図データに見つかりません: {missing}')

    walked = sum(math.dist(a, b) for a, b in zip(ROUTE, ROUTE[1:]))

    o = []
    o.append(f'<svg class="rm" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
             f'aria-labelledby="rm-title rm-desc" overflow="hidden">')
    o.append('<title id="rm-title">練馬駅からの道順の図</title>')
    o.append('<desc id="rm-desc">練馬駅の南側から千川通りを渡り、マクドナルドの角を南へ。'
             'ファミリーマートと七輪焼肉 牛繁のあいだを進み、斜めの通りを渡ってすぐ右の角のビルの3階。</desc>')
    o.append('<rect class="rm-bg" x="0" y="0" width="100%" height="100%"/>')
    # 道（1つのまとまりにして、重なっても濃くならないように透かす）
    o.append('<g class="rm-roads" fill="none" stroke-linecap="round" stroke-linejoin="round">')
    for w, ds in roads.items():
        if ds:
            o.append(f'<path stroke-width="{w}" d="{" ".join(ds)}"/>')
    o.append('</g>')
    # 線路と駅
    o.append('<g class="rm-rail" fill="none">')
    o.append(f'<path class="rm-rail__base" stroke-width="6" d="{" ".join(rails)}"/>')
    o.append(f'<path class="rm-rail__tie" stroke-width="3" stroke-dasharray="6 6" d="{" ".join(rails)}"/>')
    o.append('</g>')
    sx, sy = to_svg((STATION['cx'], STATION['cy']))
    sw, sh = STATION['w'] * S, STATION['h'] * S
    o.append(f'<g transform="translate({sx} {sy}) rotate({STATION["angle"]})">'
             f'<rect class="rm-station" x="{-sw / 2}" y="{-sh / 2}" width="{sw}" height="{sh}" rx="8"/>'
             f'<text class="rm-station__name" y="-1" text-anchor="middle">練馬駅</text>'
             f'<text class="rm-station__sub" y="12" text-anchor="middle">西武池袋線・都営大江戸線</text></g>')
    for name, x, y, a in ROAD_LABELS:
        px, py = to_svg((x, y))
        o.append(f'<text class="rm-road-label" transform="translate({px} {py}) rotate({a})" text-anchor="middle" dy=".35em">{name}</text>')
    # 店の建物（小さいので、まわりを丸く光らせて目立たせる）
    cx = sum(x for x, _ in shop_poly) / len(shop_poly)
    cy = sum(y for _, y in shop_poly) / len(shop_poly)
    hx, hy = to_svg((cx, cy))
    o.append(f'<circle class="rm-shop-glow" cx="{hx}" cy="{hy}" r="17"/>')
    o.append(f'<path class="rm-shop" d="{path_d(shop_poly)} Z"/>')
    # 歩く道
    o.append(f'<path class="rm-route" fill="none" stroke-linecap="round" stroke-linejoin="round" d="{path_d(ROUTE)}"/>')
    # 目印
    for (label, side), p in marks:
        px, py = to_svg(p)
        dx, anchor = (8, 'start') if side == 'right' else (-8, 'end')
        o.append(f'<g class="rm-mark"><circle cx="{px}" cy="{py}" r="3.6"/>'
                 f'<text x="{px + dx}" y="{py}" dy=".35em" text-anchor="{anchor}">{label}</text></g>')
    # 店の札
    bx, by = to_svg((-8, 10))
    o.append(f'<g class="rm-pin" transform="translate({bx} {by})">'
             f'<path class="rm-pin__lead" d="M0 0 L-18 22"/>'
             f'<rect class="rm-pin__box" x="-112" y="20" width="98" height="40" rx="8"/>'
             f'<text class="rm-pin__name" x="-63" y="39" text-anchor="middle">X-III</text>'
             f'<text class="rm-pin__sub" x="-63" y="53" text-anchor="middle">エクセル豊玉 3F</text></g>')
    # 番号
    for i, p in enumerate(STEPS[:-1], 1):
        px, py = to_svg(p)
        o.append(f'<g class="rm-step"><circle cx="{px}" cy="{py}" r="10"/>'
                 f'<text x="{px}" y="{py}" dy=".36em" text-anchor="middle">{i}</text></g>')
    px, py = to_svg(STEPS[-1])
    o.append(f'<g class="rm-step"><circle cx="{px - 14}" cy="{py - 10}" r="10"/>'
             f'<text x="{px - 14}" y="{py - 10}" dy=".36em" text-anchor="middle">{len(STEPS)}</text></g>')
    # 方位と縮尺
    o.append(f'<g class="rm-north" transform="translate({W - 22} 26)"><path d="M0 -14 L7 6 L0 2 L-7 6 Z"/>'
             f'<text y="20" text-anchor="middle">N</text></g>')
    bar = 50 * S
    o.append(f'<g class="rm-scale" transform="translate(14 {H - 16})"><path d="M0 -4 V0 H{bar} V-4"/>'
             f'<text x="{bar + 6}" y="0">50m</text></g>')
    o.append('</svg>')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text('\n'.join(o) + '\n', encoding='utf-8', newline='\n')
    print(f'道順の図を書き出しました → {OUT}（{OUT.stat().st_size // 1024} KB）')
    print(f'歩く距離 約{walked:.0f}m（80m＝1分で 約{math.ceil(walked / 80)}分）')


if __name__ == '__main__':
    main()
