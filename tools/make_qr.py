"""Instagram のページを開く QR コードを作り、ポスターの画像（tools/make_sign_images.py）が読む形で書き出す。

  python -I -X utf8 tools/make_qr.py      … segno が要る（pip install segno）。URL が変わったときだけ動かす

中身は site.json の instagram_url（お店が送ってくれた Instagram の QR コードと同じページが開く。
アプリの QR コードには追跡用の文字が付いて長いので、短いページの URL で作り直す。短いほど、ます目が大きく読みやすい）。
書き出すのは tools/qr-instagram.txt: 1行目が URL・型番・誤り訂正の強さ、そのあとが 1＝黒・0＝白 の行（まわりの余白は含まない）。
画像を作るときは segno は要らない（このファイルを読むだけ）。
"""
import json
from pathlib import Path

import segno

ROOT = Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / 'site.json').read_text(encoding='utf-8'))
OUT = ROOT / 'tools' / 'qr-instagram.txt'

url = SITE['instagram_url']
qr = segno.make(url, error='q', micro=False)     # 誤り訂正 Q（25%まで汚れても読める）
rows = [''.join('1' if v else '0' for v in row) for row in qr.matrix]
OUT.write_bytes(('\n'.join([f'{url}\t{qr.designator}'] + rows) + '\n').encode('utf-8'))
print(OUT.name, qr.designator, f'{len(rows)}×{len(rows[0])}')
