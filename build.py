"""X-III（クロスリー）のデザイン案を書き出す。

src/ のひな形に site.json（店の情報）を差し込んで docs/ に置く。docs/ が GitHub Pages で公開される。
店の情報は site.json の1か所だけを直せば、全パターンに反映される。

ひな形の書き方:
  {{name}}                  … site.json の値（未確定なら「仮」の印付き）
  {{img name="backbar" sizes="100vw" alt="…"}} などの部品 … 下の HELPERS を参照

使い方: python -I -X utf8 build.py
"""
import base64
import hashlib
import html
import json
import re
import shutil
import sys
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'src'
OUT = ROOT / 'docs'
SITE = json.loads((ROOT / 'site.json').read_text(encoding='utf-8'))
ALL_PATTERNS = json.loads((ROOT / 'patterns.json').read_text(encoding='utf-8'))
PATTERNS = list(ALL_PATTERNS)
PROPOSAL = SITE.get('proposal', True)

TOKEN = re.compile(r'\{\{\s*([\w.]+)((?:\s+[\w-]+(?:="[^"]*")?)*)\s*\}\}')
ARG = re.compile(r'([\w-]+)(?:="([^"]*)")?')

used_tbd = set()


def esc(s):
    return html.escape(str(s), quote=True)


def lookup(key):
    cur = SITE
    for part in key.split('.'):
        if isinstance(cur, list):
            # menu.cocktail.price のように、番号の代わりに項目の id で参照できる（並べ替えても表示がずれない）
            cur = cur[int(part)] if part.isdigit() else next(x for x in cur if isinstance(x, dict) and x.get('id') == part)
        elif isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(key)
    return cur


def raw(key):
    v = lookup(key)
    if isinstance(v, dict) and 'v' in v:
        return v['v'], v.get('tbd', False)
    return v, False


def tbd_span(text):
    return f'<span class="tbd">{esc(text)}</span>'


def show_value(v, label=''):
    if isinstance(v, dict) and 'v' in v:
        if v.get('tbd'):
            used_tbd.add(label or v['v'])
            return tbd_span(v['v'])
        return esc(v['v'])
    return esc(v)


def show(key):
    return show_value(lookup(key), key)


def fill(text):
    """「{charge} をいただいています」のような文の中の {名前} を、値（仮の印付き）にする。"""
    parts = re.split(r'\{(\w+)\}', text)
    out = []
    for i, p in enumerate(parts):
        out.append(show(p) if i % 2 else esc(p))
    return ''.join(out)


def plain(key):
    """属性やメタ情報に入れる文字。未確定の値は入れない（検索結果に「〇〇」が出るのを防ぐ）。"""
    text, tbd = raw(key)
    if tbd:
        raise ValueError(f'未確定の値 {key} は、属性やメタ情報には使えません')
    return str(text)


# ---- 写真 ----------------------------------------------------------------------
IMG_DIR = OUT / 'assets' / 'img'


def photo_widths(name):
    ws = sorted(int(p.stem.rsplit('-', 1)[1]) for p in IMG_DIR.glob(f'{name}-*.webp') if p.stem.rsplit('-', 1)[1].isdigit())
    if not ws:
        raise FileNotFoundError(f'写真 {name} がありません（tools/prepare_photos.py を先に動かす）')
    return ws


def photo_size(name):
    w = photo_widths(name)[-1]
    with Image.open(IMG_DIR / f'{name}-{w}.webp') as im:
        return im.size


ALT = {
    'counter-dark': '照明を落としたXⅢのカウンター。緑に光る酒棚と、山崎・白州のボトル',
    'backbar': 'カウンターに並ぶ山崎・白州とクラセアスール。奥に緑に光る酒棚',
    'counter-wide': '木のカウンターと、背もたれ付きのハイスツール',
    'neon-counter': 'L字のカウンターと、窓辺の赤いネオンサイン',
    'tables': '丸いハイテーブルの席と、奥のカウンター',
    'darts': 'ダーツマシンと、青い壁のテーブル席',
    # 案11の見本の写真（フリー素材。お店の写真ではない）
    'sample-bartender': '見本の写真：カウンターでカクテルを作るバーテンダー',
    'sample-cocktail': '見本の写真：オレンジの皮を添えた赤いカクテル',
    'sample-stir': '見本の写真：バースプーンでカクテルを混ぜる手元',
    'sample-julep': '見本の写真：銅のカップに入ったミントのカクテル',
}

# ---- アイコン（線画。色は文字の色に合わせる） -------------------------------------------
ICONS = {
    'glass': '<path d="M6 8h20l-2 18a3 3 0 0 1-3 2.6H11A3 3 0 0 1 8 26z"/><path d="M7 15h18"/><path d="M12 19.5l3 2.5 4-4"/>',
    'cocktail': '<path d="M5 6h22L16 18z"/><path d="M16 18v9"/><path d="M11 27h10"/><circle cx="23" cy="7" r="3.2"/>',
    'stool': '<path d="M8 8h16"/><path d="M9 8c0-2 3-3 7-3s7 1 7 3"/><path d="M10 8l-2 20M22 8l2 20M10.6 17h10.8"/>',
    'darts': '<circle cx="15" cy="17" r="10"/><circle cx="15" cy="17" r="6"/><circle cx="15" cy="17" r="2"/><path d="M15 17l12-12"/><path d="M23.5 4.5l3.5-.5-.5 3.5"/>',
    'clock': '<circle cx="16" cy="16" r="11"/><path d="M16 9v7l5 3"/>',
    'pin': '<path d="M16 28s-9-8.5-9-15a9 9 0 0 1 18 0c0 6.5-9 15-9 15z"/><circle cx="16" cy="13" r="3.2"/>',
    'phone': '<path d="M8 5h5l2 6-3 2a15 15 0 0 0 7 7l2-3 6 2v5a2 2 0 0 1-2 2A21 21 0 0 1 6 7a2 2 0 0 1 2-2z"/>',
    'train': '<rect x="8" y="4" width="16" height="19" rx="4"/><path d="M8 14h16"/><circle cx="12" cy="18.5" r="1"/><circle cx="20" cy="18.5" r="1"/><path d="M11 23l-3 5M21 23l3 5"/>',
    'insta': '<rect x="5" y="5" width="22" height="22" rx="6"/><circle cx="16" cy="16" r="5"/><circle cx="22.5" cy="9.5" r="1"/>',
    'map': '<path d="M4 8l8-3 8 3 8-3v19l-8 3-8-3-8 3z"/><path d="M12 5v19M20 8v19"/>',
    'walk': '<circle cx="17" cy="5" r="2.2"/><path d="M14 28l3-8-3-3 1-7 4 4 4 1"/><path d="M15 10l-4 3-1 5M17 20l3 8"/>',
    'arrow': '<path d="M6 16h20M19 9l7 7-7 7"/>',
    'calendar': '<rect x="5" y="7" width="22" height="20" rx="3"/><path d="M5 13h22M11 4v6M21 4v6"/>',
    'yen': '<path d="M9 5l7 10 7-10M16 15v12M10 17h12M10 22h12"/>',
    'smoke': '<path d="M4 21h18v5H4zM24 21v5M27 21v5"/><path d="M24 17c0-3 3-3 3-6s-3-3-3-6"/>',
    'card': '<rect x="4" y="8" width="24" height="17" rx="3"/><path d="M4 13h24M8 20h6"/>',
    'chair': '<path d="M9 4v14h14M9 18l-2 10M23 18l2 10M23 18V10"/>',
}


def icon(name, cls='icon', label=''):
    body = ICONS[name]
    aria = f'role="img" aria-label="{esc(label)}"' if label else 'aria-hidden="true"'
    return (f'<svg class="{esc(cls)}" viewBox="0 0 32 32" width="32" height="32" fill="none" stroke="currentColor" '
            f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" {aria}>{body}</svg>')


# ---- 部品 ------------------------------------------------------------------------
DAYS = [('月', 'Mon'), ('火', 'Tue'), ('水', 'Wed'), ('木', 'Thu'), ('金', 'Fri'), ('土', 'Sat'), ('日', 'Sun')]


def addr_query():
    return f"{SITE['region']}{SITE['locality']}{SITE['street']}"


def full_address():
    return f"{SITE['region']}{SITE['locality']}{SITE['street']} {SITE['building']}"


def map_url():
    # Google マップの店の登録（place_id）を開く。住所だけだと、店名や口コミが出ない。
    g = SITE['gmap']
    return ('https://www.google.com/maps/search/?api=1&query=' + urllib.parse.quote(g['name'])
            + '&query_place_id=' + g['place_id'])


def route_url():
    g = SITE['gmap']
    return ('https://www.google.com/maps/dir/?api=1&travelmode=walking&destination=' + urllib.parse.quote(g['name'])
            + '&destination_place_id=' + g['place_id'])


def h_img(ctx, name, sizes='100vw', alt=None, cls=None, eager=None, pos=None, scene=None):
    ws = photo_widths(name)
    w, h = photo_size(name)
    src = f"{ctx['root']}assets/img/{name}-{ws[0] if len(ws) == 1 else ws[-2]}.webp"
    srcset = ', '.join(f"{ctx['root']}assets/img/{name}-{x}.webp {x}w" for x in ws)
    attrs = [f'src="{src}"', f'srcset="{srcset}"', f'sizes="{esc(sizes)}"', f'width="{w}"', f'height="{h}"',
             f'alt="{esc(ALT[name] if alt is None else alt)}"', 'decoding="async"']
    if eager is not None:
        attrs.append('fetchpriority="high"')
    else:
        attrs.append('loading="lazy"')
    if cls:
        attrs.append(f'class="{esc(cls)}"')
    if pos:
        attrs.append(f'style="object-position:{esc(pos)}"')
    if scene:
        attrs.append(f'data-scene="{esc(scene)}"')
    return '<img ' + ' '.join(attrs) + '>'


def file_tag(name):
    return hashlib.sha256((IMG_DIR / name).read_bytes()).hexdigest()[:8]


def h_logo(ctx, cls='logo', variant='color', alt=None):
    file = 'logo-x-iii.png' if variant == 'color' else 'logo-x-iii-white.png'
    return (f'<img class="{esc(cls)}" src="{ctx["root"]}assets/img/{file}" width="444" height="234" '
            f'alt="{esc(alt or SITE["full_name"])}">')


def h_head(ctx, title=None, desc=None, theme='#0b0b0b', page=None):
    t = title or f"{SITE['full_name']}｜練馬駅のバー｜朝7時まで営業・ダーツあり"
    if PROPOSAL and ctx.get('pattern'):
        t = f"【案{ctx['pattern']['no']}】" + t
    d = desc or SITE['description']
    base = SITE.get('base_url', '').rstrip('/')
    lines = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
        f'<title>{esc(t)}</title>',
        f'<meta name="description" content="{esc(d)}">',
        f'<meta name="theme-color" content="{esc(theme)}">',
        '<meta name="format-detection" content="telephone=no">',
    ]
    if PROPOSAL:
        # 提案のページが検索に残ると、本番のページと競い合ってしまう。
        lines.append('<meta name="robots" content="noindex, nofollow">')
    elif base:
        lines.append(f'<link rel="canonical" href="{esc(base + "/" + ctx["path"])}">')
    lines += [
        '<meta property="og:type" content="website">',
        f'<meta property="og:site_name" content="{esc(SITE["full_name"])}">',
        f'<meta property="og:title" content="{esc(t)}">',
        f'<meta property="og:description" content="{esc(d)}">',
        '<meta property="og:locale" content="ja_JP">',
        '<meta name="twitter:card" content="summary_large_image">',
    ]
    if base:
        lines.append(f'<meta property="og:url" content="{esc(base + "/" + ctx["path"])}">')
        lines.append(f'<meta property="og:image" content="{esc(base)}/assets/img/og.jpg">')
    lines += [
        # ?v= は画像の中身から作る目印。ブラウザが古いアイコンを覚えていても、変わったら読み直す。
        f'<link rel="icon" href="{ctx["root"]}assets/img/icon-32.png?v={file_tag("icon-32.png")}" sizes="32x32">',
        f'<link rel="apple-touch-icon" href="{ctx["root"]}assets/img/icon-180.png?v={file_tag("icon-180.png")}">',
    ]
    lines += [
        f'<link rel="stylesheet" href="{ctx["root"]}assets/parts.css">',
        '<script type="application/json" id="hours-data">'
        + json.dumps(hours_data(), ensure_ascii=False).replace('</', '<\\/') + '</script>',
        f'<script src="{ctx["root"]}assets/notices.js" defer></script>',
    ]
    if PROPOSAL:
        lines.append(f'<link rel="stylesheet" href="{ctx["root"]}assets/common/proposal.css">')
        lines.append(f'<script src="{ctx["root"]}assets/common/proposal.js" defer></script>')
    return '\n'.join(lines)


def h_fonts(ctx, f):
    fams = '&'.join('family=' + x for x in f.split('|'))
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{esc(fams)}&amp;display=swap">')


def h_jsonld(ctx):
    base = SITE.get('base_url', '').rstrip('/')
    data = {
        '@context': 'https://schema.org',
        '@type': 'BarOrPub',
        'name': SITE['full_name'],
        'alternateName': SITE['alt_names'],
        'description': SITE['description'],
        'address': {
            '@type': 'PostalAddress', 'postalCode': SITE['postal'], 'addressRegion': SITE['region'],
            'addressLocality': SITE['locality'], 'streetAddress': f"{SITE['street']} {SITE['building']}",
            'addressCountry': 'JP',
        },
        'openingHoursSpecification': [{
            '@type': 'OpeningHoursSpecification',
            'dayOfWeek': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
            'opens': SITE['open'], 'closes': SITE['close'],
        }],
        'hasMap': map_url(),
        'amenityFeature': [{'@type': 'LocationFeatureSpecification', 'name': 'ダーツ', 'value': True}],
        'geo': {'@type': 'GeoCoordinates', 'latitude': SITE['gmap']['pin'][0], 'longitude': SITE['gmap']['pin'][1]},
        # 同じ店の Instagram と Google マップの登録。検索エンジンが同じ店だと結びつけやすくなる。
        'sameAs': [u for u in (SITE.get('instagram_url'), SITE.get('tabelog_url'), 'https://maps.google.com/?cid=' + str(int(SITE['gmap']['ftid'].split(':')[1], 16))) if u],
    }
    if not raw('smoking')[1]:
        data['smokingAllowed'] = SITE['smoking_allowed']
    # 臨時休業・臨時営業（見本は入れない）。休みは opens と closes を 00:00 にする決まり。
    special = []
    for n in notices():
        if n.get('sample') or n['type'] == 'info':
            continue
        sp = {'@type': 'OpeningHoursSpecification', 'validFrom': n['from'].isoformat(), 'validThrough': n['until'].isoformat()}
        if n['type'] == 'closed':
            sp.update(opens='00:00', closes='00:00')
        else:
            sp.update(opens=n.get('open', SITE['open']), closes=n.get('close', SITE['close']))
        special.append(sp)
    if special:
        data['specialOpeningHoursSpecification'] = special
    # 未確定の値（電話番号・料金）は、検索エンジンに渡すデータには入れない。
    if not raw('phone')[1]:
        data['telephone'] = raw('phone')[0]
    if base:
        data['url'] = base + '/' + ctx['path']
        data['image'] = [f'{base}/assets/img/og.jpg', f'{base}/assets/img/backbar-1600.webp']
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + '</script>'


def h_proposal(ctx):
    if not PROPOSAL or not ctx.get('pattern'):
        return ''
    p = ctx['pattern']
    i = [x['no'] for x in ALL_PATTERNS].index(p['no'])
    prev = ALL_PATTERNS[i - 1]
    nxt = ALL_PATTERNS[(i + 1) % len(ALL_PATTERNS)]
    r = ctx['root']
    items = []
    for x in ALL_PATTERNS:
        bg, fg = x['colors']
        cur = ' aria-current="page"' if x['no'] == p['no'] else ''
        items.append(
            f'<li><a class="pp-item" href="{r}{x["slug"]}/index.html"{cur}>'
            f'<span class="pp-item__swatch" style="background:{bg};color:{fg}" aria-hidden="true">{x["no"]}</span>'
            f'<span class="pp-item__name">{x["no"]} {esc(x["name"])}<small lang="en">{esc(x["en"])}</small></span>'
            f'<span class="pp-item__structure">{esc(x["structure"])}</span>'
            f'<span class="pp-item__concept">{esc(x["concept"])}</span></a></li>')
    return (f'<nav class="pp-bar" aria-label="デザイン案の切り替え">'
            f'<span class="pp-bar__now"><span>デザイン案 </span>{p["no"]}／{len(ALL_PATTERNS)}<b>{esc(p["name"])}</b></span>'
            f'<a class="pp-bar__step" href="{r}{prev["slug"]}/index.html" aria-label="前の案（{esc(prev["name"])}）">‹</a>'
            f'<a class="pp-bar__step" href="{r}{nxt["slug"]}/index.html" aria-label="次の案（{esc(nxt["name"])}）">›</a>'
            f'<details class="pp-switch"><summary>{len(ALL_PATTERNS)}案を切り替え</summary>'
            f'<div class="pp-panel"><p class="pp-panel__head"><strong>デザイン案を選ぶ</strong>'
            f'<span>中身は同じで、見た目と構成が違います</span></p>'
            f'<ul class="pp-list">{"".join(items)}</ul></div></details></nav>')


def h_menu(ctx, h='h3', cls='menu'):
    out = [f'<div class="{esc(cls)}">']
    for m in SITE['menu']:
        items = ''.join(f'<li>{esc(x)}</li>' for x in m['items'])
        mark = ' <span class="tbd tbd--only">品目は一例</span>' if m.get('items_tbd') else ''
        lead = f'<p class="{cls}__lead">{esc(m["lead"])}</p>' if m.get('lead') else ''
        out.append(f'<section class="{cls}__cat" id="{cls}-{m["id"]}"><{h} class="{cls}__title">{esc(m["cat"])}'
                   f'<span class="{cls}__en" lang="en">{esc(m["en"])}</span></{h}>'
                   f'<p class="{cls}__price">{show_value(m["price"], m["cat"] + "の価格")}{mark}</p>{lead}'
                   f'<ul class="{cls}__items">{items}</ul></section>')
    out.append('</div>')
    out.append(f'<p class="{cls}__note">{esc(SITE["menu_note"])}</p>')
    return ''.join(out)


def h_menu_nav(ctx, cls='menu'):
    """メニューの種類へ飛ぶ目次の項目（<li>）。メニューの並びから作るので、種類を足しても直さなくてよい。"""
    return ''.join(f'<li><a href="#{cls}-{m["id"]}">{esc(m["cat"])}</a></li>' for m in SITE['menu'])


def h_food(ctx, cls='food'):
    rows = ''.join(f'<li><span class="{cls}__name">{esc(f["name"])}</span>'
                   f'<span class="{cls}__price">{show_value(f["price"], f["name"] + "の価格")}</span></li>'
                   for f in SITE['food'])
    return f'<ul class="{esc(cls)}">{rows}</ul><p class="{cls}__note">{esc(SITE["food_note"])}</p>'


def h_faq(ctx, cls='faq', open=None):
    out = [f'<div class="{esc(cls)}">']
    for i, f in enumerate(SITE['faq']):
        # open … 最初の1問だけ開く。open="all" … すべて開いておく（読み物として見せる案）。
        o = ' open' if open == 'all' or (open is not None and i == 0) else ''
        out.append(f'<details class="{cls}__item"{o}><summary class="{cls}__q">{esc(f["q"])}</summary>'
                   f'<p class="{cls}__a">{fill(f["a"])}</p></details>')
    out.append('</div>')
    return ''.join(out)


def link_or_text(key, href, external=False):
    """値が決まっていてリンク先もあれば、押せるリンクにする（電話は電話がかかる、Instagram は別のタブで開く）。"""
    text, tbd = raw(key)
    if tbd or not href or href.startswith('#'):
        return show(key)
    ext = ' target="_blank" rel="noopener"' if external else ''
    return f'<a href="{esc(href)}"{ext}>{esc(text)}</a>'


def h_access(ctx):
    return f'{esc(SITE["lines"])}「{esc(SITE["station"])}」{show("exit")}から徒歩{show("walk")}分'


def h_info(ctx, cls='info'):
    rows = [
        ('店名', f'{esc(SITE["full_name"])}<br><span lang="en">{esc(SITE["en"])}</span>'),
        ('住所', f'〒{esc(SITE["postal"])}<br>{esc(SITE["region"] + SITE["locality"] + SITE["street"])}<br>{esc(SITE["building"])}'),
        ('アクセス', h_access(ctx)),
        ('営業時間', f'{esc(SITE["hours"])}<br><small>ラストオーダー {show("last_order")}</small>'),
        ('定休日', f'{esc(SITE["closed"])}<br><small>{show("closed_note")}</small>'),
        ('席数', show('seats')),
        ('チャージ', show('charge')),
        ('電話', link_or_text('phone', h_tel_href(ctx))),
        ('お支払い', show('payment')),
        ('たばこ', show('smoking')),
        ('Instagram', link_or_text('instagram', SITE.get('instagram_url'), external=True)),
    ]
    body = ''.join(f'<div class="{cls}__row"><dt>{k}</dt><dd>{v}</dd></div>' for k, v in rows)
    return f'<dl class="{esc(cls)}">{body}</dl>'


def h_hours_table(ctx, cls='hours'):
    rows = []
    for ja, en in DAYS:
        if en == 'Sun':
            rows.append(f'<tr class="is-closed" data-day="{en}"><th scope="row">{ja}</th><td>定休日</td></tr>')
        else:
            rows.append(f'<tr data-day="{en}"><th scope="row">{ja}</th><td>{esc(SITE["open"])}〜翌{esc(SITE["close"].lstrip("0"))}</td></tr>')
    return f'<table class="{esc(cls)}"><caption class="visually-hidden">営業時間</caption><tbody>{"".join(rows)}</tbody></table>'


def h_map(ctx, cls='map', title=None):
    # Google マップの「地図を埋め込む」の形。店の登録に印が立ち、駅と店が1画面に入る広さで開く。
    g = SITE['gmap']
    name = base64.b64encode(g['name'].encode()).decode().rstrip('=')
    lat, lng = g['view']
    src = ('https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d' + str(g['view_m']) + f'!2d{lng}!3d{lat}'
           '!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s' + urllib.parse.quote(g['ftid'])
           + '!2z' + name + '!5e0!3m2!1sja!2sjp!4v1792247389433!5m2!1sja!2sjp')
    return (f'<iframe class="{esc(cls)}" src="{esc(src)}" title="{esc(title or SITE["full_name"] + "の地図")}" '
            'loading="lazy" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>')


def h_route(ctx, cls='route'):
    items = ''.join(f'<li>{show_value(s, "道順")}</li>' for s in SITE['route'])
    return f'<ol class="{esc(cls)}">{items}</ol>'


def h_streetview(ctx, cls='streetview'):
    """入口のようす（Google ストリートビューの埋め込み）。画像を切り取って載せず、Google の正式な埋め込みで出す。"""
    sv = SITE['streetview']
    lat, lng = sv['pos']
    src = (f"https://www.google.com/maps/embed?pb=!4v1792247389433!6m8!1m7!1s{sv['pano']}!2m2!1d{lat}!2d{lng}"
           f"!3f{sv['heading']}!4f{sv['pitch']}!5f0.7820865974627469")
    return (f'<figure class="{esc(cls)}"><iframe class="{esc(cls)}__view" src="{esc(src)}" '
            f'title="{esc(SITE["full_name"])}の入口のようす（Google ストリートビュー）" loading="lazy" '
            'referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>'
            f'<figcaption><b>入口のようす</b>　青いビルの角。木の扉の右にあるガラスの扉から入り、エレベーターで3階へ。'
            f'<small>Google ストリートビュー（{esc(sv["date"])}撮影。看板は当時のものです）</small></figcaption></figure>')


ROUTE_MAP = SRC / '_parts' / 'route-map.svg'


def h_route_map(ctx, cls='route-map'):
    """駅から店までの道順の図（tools/make_route_map.py で作る）。色は各案の CSS の --rm-… で変える。"""
    svg = ROUTE_MAP.read_text(encoding='utf-8').strip()
    return (f'<figure class="{esc(cls)}">{svg}'
            '<figcaption>道順の図（縮尺はおおよそ）。地図データ © '
            '<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'
            '</figcaption></figure>')


# ---- お知らせ（臨時休業・臨時営業など） -----------------------------------------------
NOTICE_TYPES = {'closed': '臨時休業', 'open': '臨時営業', 'info': 'お知らせ'}
WEEK_JA = '月火水木金土日'


def notices():
    """site.json の notices を日付の順に返す。書き出す時点で終わっているものは除く。until が無ければ from の1日だけ。"""
    out = []
    for n in SITE.get('notices', []):
        if n.get('type') not in NOTICE_TYPES:
            raise ValueError(f'お知らせの type は {list(NOTICE_TYPES)} のどれか: {n}')
        f = date.fromisoformat(n['from'])
        u = date.fromisoformat(n.get('until', n['from']))
        if u < f:
            raise ValueError(f'お知らせの until が from より前です: {n}')
        if u < date.today() - timedelta(days=1) and not n.get('sample'):
            continue
        out.append({**n, 'from': f, 'until': u})
    return sorted(out, key=lambda n: n['from'])


def hours_data():
    """notices.js に渡す営業時間とお知らせ（見本は渡さない。「営業中」の表示を見本で変えないため）。"""
    real = []
    for n in notices():
        if n.get('sample'):
            continue
        real.append({k: v for k, v in (('from', n['from'].isoformat()), ('until', n['until'].isoformat()),
                                         ('type', n['type']), ('open', n.get('open')), ('close', n.get('close'))) if v})
    return {'open': SITE['open'], 'close': SITE['close'], 'closedDays': SITE['closed_weekdays'], 'notices': real}


def jp_date(d):
    return f'{d.month}月{d.day}日（{WEEK_JA[d.weekday()]}）'


def jp_time(t):
    h, m = t.split(':')
    return f'{int(h)}:{m}'


def h_notices(ctx, cls='notices', h='h2', title='お知らせ'):
    """お知らせの欄。終わった日の分は notices.js が隠し、1つも残らなければ欄ごと隠す。"""
    ns = notices()
    if not ns:
        return ''
    items = []
    for n in ns:
        # 日付の途中では折り返さない（何日も続くときは「〜」のところで折り返せる）
        when = f'<span>{jp_date(n["from"])}</span>' + ('' if n['until'] == n['from'] else f'〜<span>{jp_date(n["until"])}</span>')
        hours = ''
        if n['type'] == 'open':
            o, c = n.get('open', SITE['open']), n.get('close', SITE['close'])
            hours = f'<span class="{cls}__hours">{jp_time(o)}〜{"翌" if c <= o else ""}{jp_time(c)}</span>'
        text = esc(n['text'])
        if n.get('sample'):
            used_tbd.add('お知らせの見本')
            text = tbd_span(n['text'])
        until = '' if n.get('sample') else f' data-until="{n["until"].isoformat()}"'
        items.append(f'<li class="{cls}__item {cls}__item--{n["type"]}"{until}>'
                     f'<span class="{cls}__tag">{NOTICE_TYPES[n["type"]]}</span>'
                     f'<time class="{cls}__date" datetime="{n["from"].isoformat()}">{when}</time>{hours}'
                     f'<p class="{cls}__text">{text}</p></li>')
    note = ''
    if PROPOSAL and any(n.get('sample') for n in ns):
        note = (f'<p class="{cls}__note"><b>見本</b>　お店からお知らせが届いたら、このように表示します。'
                '臨時休業・臨時営業の日付を書くと、日付が過ぎたものは自動で消えます。</p>')
    return (f'<section class="{esc(cls)}" aria-labelledby="{cls}-h" data-notices><div class="{cls}__in">'
            f'<{h} class="{cls}__title" id="{cls}-h">{esc(title)}</{h}>{note}'
            f'<ul class="{cls}__list">{"".join(items)}</ul></div></section>')


# ---- 案11（機能モリモリ版）の部品 ------------------------------------------------------
def h_feature(ctx, id):
    """提案中だけ出す「機能○：何ができるか」の札。機能の名前と説明は patterns.json の features。本番では出さない。"""
    if not PROPOSAL:
        return ''
    feats = ctx['pattern']['features']
    i, f = next((i, f) for i, f in enumerate(feats, 1) if f['id'] == id)
    return (f'<p class="ft"><span class="ft__no">機能 {i}</span><b class="ft__name">{esc(f["name"])}</b>'
            f'<span class="ft__desc">{esc(f["desc"])}</span></p>')


def h_feature_list(ctx):
    """提案中だけ出す、この案に入っている機能の一覧（押すとその場所へ飛ぶ）。"""
    if not PROPOSAL:
        return ''
    items = ''.join(f'<li><a href="#{esc(f["anchor"])}"><span class="ft__no">機能 {i}</span><b>{esc(f["name"])}</b>'
                    f'<small>{esc(f["desc"])}</small></a></li>' for i, f in enumerate(ctx['pattern']['features'], 1))
    return (f'<section class="ft-list" aria-labelledby="ft-list-h"><div class="wrap"><h2 id="ft-list-h">この案に入っている機能（{len(ctx["pattern"]["features"])}個）</h2>'
            '<p>バーのホームページでよく使われる機能を、ひととおり入れた見本です。気に入った機能を、ほかの案に足すこともできます。'
            '<br>この説明の札は提案用で、本番のページには出ません。</p>'
            f'<ul>{items}</ul></div></section>')


def h_data(ctx, name):
    """ページの JavaScript に渡すデータ（今夜の一杯診断・営業カレンダー用のお知らせ）。"""
    if name == 'cocktail_guide':
        data = SITE['cocktail_guide']
    elif name == 'notices':
        data = [{'from': n['from'].isoformat(), 'until': n['until'].isoformat(), 'type': n['type'], 'text': n['text'],
                 'sample': bool(n.get('sample'))} for n in notices()]
    else:
        raise KeyError(name)
    return (f'<script type="application/json" id="data-{esc(name)}">'
            + json.dumps(data, ensure_ascii=False).replace('</', '<\\/') + '</script>')


def h_credit(ctx, name):
    """見本の写真の作者と条件（CC0 は作者名がいらないが、出どころとして書く）。"""
    c = SITE['sample_photos'][name]
    return (f'見本の写真（フリー素材）：{esc(c["artist"])} ／ '
            f'<a href="{esc(c["page"])}" target="_blank" rel="noopener">Wikimedia Commons</a> '
            f'（<a href="{esc(c["license_url"])}" target="_blank" rel="noopener">{esc(c["license"])}</a>）')


def h_features(ctx, cls='features', h='h3'):
    out = [f'<ul class="{esc(cls)}">']
    for f in SITE['features']:
        out.append(f'<li class="{cls}__item">{icon(f["icon"], cls + "__icon")}'
                   f'<{h} class="{cls}__title">{esc(f["title"])}</{h}><p class="{cls}__body">{esc(f["body"])}</p></li>')
    out.append('</ul>')
    return ''.join(out)


def h_icon(ctx, name, cls='icon', label=''):
    return icon(name, cls, label)


def h_addr(ctx):
    return esc(full_address())


def h_tel_href(ctx):
    text, tbd = raw('phone')
    if tbd or not SITE.get('tel'):
        return '#tel'
    return 'tel:' + SITE['tel']


def h_line_add_href(ctx):
    """LINE 公式アカウントの友だち追加のリンク（LINE の決まった形）。ID が決まるまでは、ページの中の LINE の欄へ。"""
    text, tbd = raw('line_oa')
    return '#line' if tbd else 'https://line.me/R/ti/p/' + urllib.parse.quote(text)


def h_line_qr(ctx, cls='line-oa__qr'):
    """友だち追加の QR コード。ID が決まるまでは見本の枠。決まったら、お店の管理画面から出せる QR の画像を
    docs/assets/img/line-qr.png に置き、site.json の line_qr に "line-qr.png" と書く。"""
    text, tbd = raw('line_oa')
    if tbd:
        used_tbd.add('LINE の QR コード')
        return f'<div class="{esc(cls)} {esc(cls)}--empty" aria-hidden="true">QRコード<small>アカウントができたら表示</small></div>'
    if SITE.get('line_qr'):
        return (f'<img class="{esc(cls)}" src="{ctx["root"]}assets/img/{esc(SITE["line_qr"])}" width="120" height="120" '
                f'alt="LINE 公式アカウント {esc(text)} の友だち追加の QR コード">')
    return ''


def h_line_msg_base(ctx):
    """LINE 公式アカウントに、文面を入れた状態でメッセージを送るリンクの前半（後ろに文面を足す）。ID が決まるまでは空。"""
    text, tbd = raw('line_oa')
    return '' if tbd else 'https://line.me/R/oaMessage/' + urllib.parse.quote(text) + '/?'


def h_insta_href(ctx):
    return SITE.get('instagram_url') or '#instagram'


def h_year(ctx):
    return str(date.today().year)


HELPERS = {
    'head': h_head, 'fonts': h_fonts, 'jsonld': h_jsonld, 'proposal': h_proposal, 'img': h_img, 'logo': h_logo,
    'menu': h_menu, 'menu_nav': h_menu_nav, 'food': h_food, 'faq': h_faq, 'info': h_info, 'hours_table': h_hours_table, 'map': h_map,
    'route': h_route, 'route_map': h_route_map, 'streetview': h_streetview, 'notices': h_notices, 'feature': h_feature, 'feature_list': h_feature_list, 'data': h_data, 'credit': h_credit, 'features': h_features, 'icon': h_icon, 'access': h_access, 'addr': h_addr,
    'tel_href': h_tel_href, 'line_add_href': h_line_add_href, 'line_qr': h_line_qr, 'line_msg_base': h_line_msg_base, 'insta_href': h_insta_href, 'year': h_year,
    'map_url': lambda ctx: esc(map_url()), 'route_url': lambda ctx: esc(route_url()),
    'root': lambda ctx: ctx['root'],
}


def render(text, ctx, where):
    def sub(m):
        name, argtext = m.group(1), m.group(2) or ''
        args = {k.replace('-', '_'): (v if v is not None else '') for k, v in ARG.findall(argtext)}
        if 'class' in args:
            args['cls'] = args.pop('class')
        if name in HELPERS:
            return HELPERS[name](ctx, **args)
        if name.startswith('pattern.'):
            return esc(ctx['pattern'][name.split('.', 1)[1]])
        # 未確定の値を属性の中（< … > の中）に入れると、印の span がタグを壊すので止める。
        before = text[:m.start()]
        v = lookup(name)
        if isinstance(v, dict) and v.get('tbd') and before.rfind('<') > before.rfind('>'):
            raise ValueError(f'{where}: 未確定の値 {name} を属性の中で使っています')
        return show(name)

    out = TOKEN.sub(sub, text)
    left = re.findall(r'\{\{.*?\}\}', out)
    if left:
        raise ValueError(f'{where}: 置き換えられなかった印があります: {left[:3]}')
    return out


def build():
    # 書き出し先の写真は残し、ページだけ作り直す。
    for p in PATTERNS:
        shutil.rmtree(OUT / p['slug'], ignore_errors=True)
    (OUT / 'assets' / 'common').mkdir(parents=True, exist_ok=True)
    for f in (SRC / '_common').glob('*'):
        shutil.copy2(f, OUT / 'assets' / 'common' / f.name)
    for name in ('parts.css', 'notices.js'):
        shutil.copy2(SRC / '_parts' / name, OUT / 'assets' / name)

    pages = 0
    for p in PATTERNS:
        src = SRC / p['slug']
        dst = OUT / p['slug']
        dst.mkdir(parents=True)
        for f in src.iterdir():
            if f.suffix == '.html':
                ctx = {'pattern': p, 'root': '../', 'path': f'{p["slug"]}/{f.name}'}
                (dst / f.name).write_text(render(f.read_text(encoding='utf-8'), ctx, f'{p["slug"]}/{f.name}'),
                                          encoding='utf-8', newline='\n')
                pages += 1
            else:
                shutil.copy2(f, dst / f.name)
        missing = [x for x in p['pages'] if not (dst / x).exists()]
        if missing:
            raise FileNotFoundError(f'{p["slug"]}: ページが足りません {missing}')

    # 入口（公開したアドレスそのもの）。開いたら最初の案を出す。切り替えは各案の上の帯で行う。
    first = ALL_PATTERNS[0]['slug']
    (OUT / 'index.html').write_text(
        '<!doctype html>\n<html lang="ja">\n<head>\n<meta charset="utf-8">\n'
        + ('<meta name="robots" content="noindex, nofollow">\n' if PROPOSAL else '')
        + f'<title>{esc(SITE["full_name"])}</title>\n'
        f'<meta http-equiv="refresh" content="0; url={first}/index.html">\n'
        f'<script>location.replace("{first}/index.html" + location.hash)</script>\n'
        f'</head>\n<body><p><a href="{first}/index.html">{esc(SITE["full_name"])} のページへ</a></p></body>\n</html>\n',
        encoding='utf-8', newline='\n')

    # GitHub Pages に Jekyll の加工をさせない（_ で始まるファイルを消されないように）。
    (OUT / '.nojekyll').write_text('', encoding='utf-8')
    print(f'{pages} ページを書き出しました → {OUT}')
    if used_tbd:
        print(f'未確定（仮）の値: {len(used_tbd)} 種類')
        if not PROPOSAL:
            print('本番の書き出しに未確定の値が残っています。site.json を埋めてください。')
            sys.exit(1)


if __name__ == '__main__':
    # --only 01,02 … 作りかけのときに、できた案だけ書き出す。
    if len(sys.argv) > 2 and sys.argv[1] == '--only':
        keep = sys.argv[2].split(',')
        PATTERNS[:] = [p for p in PATTERNS if p['no'] in keep]
    build()
