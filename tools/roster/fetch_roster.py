"""Refresh roster data from overwatch.blizzard.com.
Usage: python -I fetch_roster.py <workdir>
Writes <workdir>/cards.json (slug, name, role, subrole, portrait url), <workdir>/abilities.json,
and downloads portraits to D:/counterwatch/assets/heroes/<id>.png. Then run build_heroes_json.py <workdir> <out.json>.
"""
import re, json, html, os, sys, urllib.request, io
from PIL import Image
W = sys.argv[1]; os.makedirs(W, exist_ok=True)
ASSETS = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'heroes')
UA = {'User-Agent': 'Mozilla/5.0'}
get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read()
h = get('https://overwatch.blizzard.com/en-us/heroes/').decode('utf8')
cards = []
for attrs, body in re.findall(r'<a class="hero-card"([^>]*)>(.*?)</a>', h, re.S):
    a = dict(re.findall(r'([\w-]+)="([^"]*)"', attrs))
    cards.append(dict(slug=a['id'], name=html.unescape(re.search(r'<h2 slot="heading">(.*?)</h2>', body).group(1)),
                      role=a.get('data-role'), sub=a.get('data-subrole'),
                      src=re.search(r'heroCardPortrait"[^>]*src="([^"]+)"', body).group(1)))
json.dump(cards, open(os.path.join(W, 'cards.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
ab = {}
for c in cards:
    p = get('https://overwatch.blizzard.com/en-us/heroes/%s/' % c['slug']).decode('utf8')
    ab[c['slug']] = [(html.unescape(n), re.sub(r'<[^>]+>', '', html.unescape(d)).strip())
                     for n, d in re.findall(r'<h3 class="heading" slot="heading">(.*?)</h3><p slot="description">(.*?)</p>', p, re.S)]
    Image.open(io.BytesIO(get(c['src']))).convert('RGBA').save(os.path.join(ASSETS, c['slug'].replace('-', '') + '.png'))
json.dump(ab, open(os.path.join(W, 'abilities.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print(len(cards), 'heroes')
