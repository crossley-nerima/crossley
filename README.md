# X-III（クロスリー）ホームページ デザイン案

練馬駅のバー「X-III（クロスリー）」のホームページの、デザイン案 10 パターンです。

- 公開アドレス: https://crossley-nerima.github.io/crossley/ （開くと案01が表示されます。上の帯の「10案を切り替え」で切り替えられます）
- 提案中なので、検索エンジンには出ない設定（noindex）にしています。

## 中身

| フォルダ・ファイル | 内容 |
|---|---|
| `site.json` | 店の情報（店名・住所・営業時間・料金・メニューなど）。**情報はここだけに書く** |
| `patterns.json` | 10 案の名前・説明・構成 |
| `src/<案>/` | 各案のひな形（HTML・CSS・JavaScript） |
| `src/_common/` | 提案のときだけ使う部品（案の切り替えの帯・「仮」の札） |
| `src/_parts/` | 全案に差し込む部品。`route-map.svg`（道順の図）と、その見た目 `route-map.css` |
| `docs/` | 書き出したサイト（GitHub Pages はここを公開する） |
| `build.py` | `site.json` をひな形に差し込んで `docs/` に書き出す |
| `tools/prepare_photos.py` | 写真を Web 用に縮め、撮影情報を消し、テレビの画面をぼかす。チラシからロゴを抜き出す |
| `tools/shoot.py` | 書き出したページを画面なしの Edge で撮って、崩れを確かめる |
| `tools/make_route_map.py` | 練馬駅から店までの道順の図を、OpenStreetMap の地図データから作る（歩く道・番号の位置はこの中に書く） |

## 道順を直すとき

1. 手順の文は `site.json` の `route`。図の番号（1〜4）と順番を合わせる。
2. 歩く道や番号の位置を変えるときは `tools/make_route_map.py` の `ROUTE`・`STEPS` を直し、`python -I -X utf8 tools/make_route_map.py` で図を作り直す。
3. 図の色は各案の `style.css` の `.route-map { --rm-… }` で変える。

## 店の情報を直すとき

1. `site.json` を直す。まだ決まっていない値は `{"v": "値", "tbd": true}` の形で、ページに「仮」の札が付く。決まったら `tbd` を消す。
2. `python -I -X utf8 build.py` で書き出す（全 10 案に反映される）。

## 写真を差し替えるとき

`python -I -X utf8 tools/prepare_photos.py <写真のフォルダ> docs/assets/img`

## 本番にするとき

1. 案を 1 つに決め、`site.json` の `"proposal"` を `false` にする（検索に出る設定になり、案の切り替えの帯と「仮」の札が消える）。
   まだ「仮」の値が残っていると、書き出しが止まる。
2. 独自ドメインを使うなら `base_url` を直す（共有したときの画像・検索エンジン向けの店舗情報に使う）。
