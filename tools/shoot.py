"""書き出したページを、画面なしの Edge で撮る（パソコンの幅とスマホの幅）。崩れの確認用（依頼者には出さない）。

  python -I -X utf8 tools/shoot.py check <出力先> <docs からのパス> …
      … ページ全体を撮り、JavaScript のエラーや読めなかったファイルを表示する（作りの確認用）。

pip install websocket-client が要る。
"""
import base64
import io
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import websocket
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
EDGE = os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)') + r'\Microsoft\Edge\Application\msedge.exe'
PORT = 9347

PC = {'width': 1366, 'height': 860, 'deviceScaleFactor': 1, 'mobile': False}
SP = {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True}
IPHONE_UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 '
             '(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1')


class Browser:
    def __init__(self):
        self.proc = subprocess.Popen(
            [EDGE, '--headless=new', '--disable-gpu', '--hide-scrollbars', f'--remote-debugging-port={PORT}',
             f'--remote-allow-origins=http://127.0.0.1:{PORT}', '--window-size=1366,860',
             '--user-data-dir=' + os.path.join(os.environ['TEMP'], 'edge-cdp-crossley'), 'about:blank'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        page = None
        for _ in range(60):
            try:
                tabs = json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json'))
                page = [t for t in tabs if t['type'] == 'page'][0]
                break
            except Exception:
                time.sleep(0.25)
        self.ws = websocket.create_connection(page['webSocketDebuggerUrl'], timeout=60)
        self.nid = 0
        self.errors = []
        for m in ('Runtime.enable', 'Log.enable', 'Page.enable', 'Network.enable'):
            self.call(m)
        self.call('Network.setCacheDisabled', {'cacheDisabled': True})

    def call(self, method, params=None):
        self.nid += 1
        self.ws.send(json.dumps({'id': self.nid, 'method': method, 'params': params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            m = msg.get('method')
            if m == 'Runtime.exceptionThrown':
                self.errors.append(msg['params']['exceptionDetails'].get('exception', {}).get('description', 'exception'))
            elif m == 'Runtime.consoleAPICalled' and msg['params']['type'] == 'error':
                self.errors.append('console.error: ' + ' '.join(str(a.get('value', a.get('description', ''))) for a in msg['params']['args']))
            elif m == 'Log.entryAdded' and msg['params']['entry']['level'] == 'error':
                e = msg['params']['entry']
                self.errors.append(f"{e.get('text', '')} {e.get('url', '')}")
            if msg.get('id') == self.nid:
                return msg.get('result', {})

    def js(self, expr):
        r = self.call('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
        return r.get('result', {}).get('value')

    def wait(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            self.js('1')
            time.sleep(0.1)

    def open(self, url, device, hide_bar=False):
        self.call('Emulation.setDeviceMetricsOverride', device)
        self.call('Emulation.setTouchEmulationEnabled', {'enabled': device['mobile']})
        self.call('Emulation.setUserAgentOverride', {'userAgent': IPHONE_UA if device['mobile'] else ''})
        self.errors = []
        self.call('Page.navigate', {'url': url})
        self.wait(1.2)
        self.js('document.fonts.ready.then(() => 1)')
        if hide_bar:
            self.js("document.querySelector('.pp-bar')?.remove(); 1")

    def scroll_through(self):
        """遅れて読み込む写真と、スクロールで出てくる演出を、全部出してから撮る。"""
        h = self.js('document.documentElement.scrollHeight') or 0
        y = 0
        while y < h:
            self.js(f'window.scrollTo(0, {y}); 1')
            self.wait(0.15)
            y += 500
            h = self.js('document.documentElement.scrollHeight') or h
        self.js('window.scrollTo(0, 0); 1')
        self.wait(0.8)

    def shot(self, full):
        if full:
            m = self.call('Page.getLayoutMetrics')
            size = m['cssContentSize']
            r = self.call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': True,
                                                     'clip': {'x': 0, 'y': 0, 'width': size['width'],
                                                              'height': min(size['height'], 16000), 'scale': 1}})
        else:
            r = self.call('Page.captureScreenshot', {'format': 'png'})
        return Image.open(io.BytesIO(base64.b64decode(r['data'])))

    def close(self):
        try:
            self.ws.close()
        finally:
            self.proc.kill()


def url_of(rel):
    return (DOCS / rel).resolve().as_uri()


def check(out, rels):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    b = Browser()
    try:
        for rel in rels:
            name = rel.replace('/', '_').replace('.html', '')
            for label, dev in (('pc', PC), ('sp', SP)):
                b.open(url_of(rel), dev)
                # 開いた直後の1画面（全体を撮る方式は、固定のヘッダーの位置がずれて写ることがあるため別に撮る）。
                first = b.shot(full=False)
                if label == 'sp':
                    first = first.resize((390, round(first.height * 390 / first.width)), Image.LANCZOS)
                first.convert('RGB').save(out / f'{name}-{label}-first.png')
                b.scroll_through()
                im = b.shot(full=True)
                # 確かめやすい幅に縮める（パソコンは半分、スマホは 390px）。
                w = 683 if label == 'pc' else 390
                im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
                # 縦に長いページは、読みやすいように区切って保存する。
                step = 1400 if label == 'pc' else 1700
                n = 0
                for top in range(0, im.height, step):
                    im.crop((0, top, w, min(im.height, top + step))).convert('RGB').save(out / f'{name}-{label}-{n}.png')
                    n += 1
                overflow = b.js('document.documentElement.scrollWidth - window.innerWidth')
                errs = [e for e in b.errors if 'favicon' not in e]
                print(f'{rel} [{label}] {n}枚 高さ{im.height}px 横はみ出し{overflow}px' + (f' エラー: {errs}' if errs else ''))
    finally:
        b.close()


if __name__ == '__main__':
    if sys.argv[1] == 'check':
        check(sys.argv[2], sys.argv[3:])
