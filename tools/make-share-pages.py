#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build one shareable page per essay.

Everything on this site lives at a #/fragment, and a fragment never
reaches the server — so WhatsApp, Facebook and the rest only ever see
the front page and show the site's own title and picture.  This writes a
small real page per essay at /p/<id>.html carrying that essay's own
Open Graph tags, plus a 1200x630 preview image at /og/<id>.jpg taken
from the essay's own photograph.  A person opening one is sent straight
on to the essay; a preview crawler reads the tags and stops there.

While an essay is open the site rewrites the address bar to its page
here, so one of these must exist for every essay on the page.

Re-run after adding an essay, or after changing a title, excerpt or
photograph:   python3 tools/make-share-pages.py
"""
import base64, html, io, os, re, shutil, sys

BASE = 'https://cogitoergodukkha.github.io'
SITE = 'reflections on reflections'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, 'index.html')

try:
    from PIL import Image
except ImportError:
    sys.exit('needs Pillow:  pip install Pillow')


def text_of(fragment):
    return html.unescape(re.sub(r'<[^>]+>', '', fragment)).strip()


def read_posts(doc):
    """id -> {title, excerpt, photo bytes} for every essay on the page."""
    posts = {}

    for m in re.finditer(r'<a [^>]*class="post-link[^>]*>', doc):
        pid = re.search(r'data-id="([a-z0-9-]+)"', m.group())
        if not pid:
            continue
        pid = pid.group(1)
        entry = doc[m.start():doc.index('</a>', m.start())]
        ex = re.search(r'<span class="post-link__excerpt">(.*?)</span>', entry, re.S)
        posts[pid] = {'excerpt': text_of(ex.group(1)) if ex else ''}

    for m in re.finditer(r'<article class="post" id="([a-z0-9-]+)"', doc):
        pid = m.group(1)
        if pid not in posts:
            continue
        art = doc[m.start():doc.index('</article>', m.start())]

        h1 = re.search(r'<h1 class="post__title">(.*?)</h1>', art, re.S).group(1)
        sub = re.search(r'<span class="sub">(.*?)</span>', h1, re.S)
        main = text_of(re.sub(r'<span class="sub">.*?</span>', '', h1, flags=re.S))
        posts[pid]['title'] = (main + ' · ' + text_of(sub.group(1))) if sub else main

        img = re.search(r'<figure class="lede">\s*<img src="data:image/jpeg;base64,'
                        r'([A-Za-z0-9+/=]+)"', art)
        posts[pid]['photo'] = base64.b64decode(img.group(1)) if img else None

    return posts


def preview_image(raw, out):
    """1200x630 is what the preview services expect; metadata is dropped."""
    im = Image.open(io.BytesIO(raw)).convert('RGB')
    TW, TH = 1200, 630
    sa, ta = im.width / im.height, TW / TH
    if sa > ta:
        w = int(im.height * ta)
        im = im.crop(((im.width - w) // 2, 0, (im.width - w) // 2 + w, im.height))
    else:
        h = int(im.width / ta)
        top = int((im.height - h) * 0.35)        # faces and subjects sit high
        im = im.crop((0, top, im.width, top + h))
    im.resize((TW, TH), Image.LANCZOS).save(out, 'JPEG', quality=80, optimize=True)


PAGE = '''<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · {site}</title>
<link rel="canonical" href="{base}/p/{pid}.html">
<meta name="description" content="{desc}">
<meta name="author" content="Abraham Lim">

<meta property="og:type" content="article">
<meta property="og:site_name" content="{site}">
<meta property="og:url" content="{base}/p/{pid}.html">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{base}/og/{pid}.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="zh_TW">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{base}/og/{pid}.jpg">

<!-- A reader is sent straight on by this; a preview crawler does not run
     scripts, so it reads the tags above and stops there. Deliberately a
     script and not a refresh meta: some crawlers follow one of those, and
     would end up reading the front page instead of this essay. -->
<script>location.replace('/#/{pid}');</script>
<style>
:root{{color-scheme:light dark}}
body{{margin:0;min-height:100vh;display:grid;place-items:center;
     background:#EDEFE9;color:#45525C;
     font:16px/1.8 "Newsreader",Georgia,serif;padding:2rem;text-align:center}}
a{{color:#356F5C}}
@media (prefers-color-scheme:dark){{body{{background:#101413;color:#AFB9B1}}a{{color:#84C1A8}}}}
</style>
</head>
<body>
  <p>前往〈<a href="/#/{pid}">{title}</a>〉⋯</p>
</body>
</html>
'''


def main():
    doc = open(SRC, encoding='utf-8').read()
    posts = read_posts(doc)

    for d in ('p', 'og'):
        shutil.rmtree(os.path.join(ROOT, d), ignore_errors=True)
        os.makedirs(os.path.join(ROOT, d))

    fallback = os.path.join(ROOT, 'og.jpg')
    for pid, p in posts.items():
        out = os.path.join(ROOT, 'og', pid + '.jpg')
        if p.get('photo'):
            preview_image(p['photo'], out)
        else:
            # every essay must have a page: while one is open the site puts
            # /p/<id>.html in the address bar, and reloading it has to work
            print('  !! %s has no photograph, using the site picture' % pid)
            shutil.copyfile(fallback, out)
        page = PAGE.format(
            base=BASE, site=html.escape(SITE, quote=True), pid=pid,
            title=html.escape(p['title'], quote=True),
            desc=html.escape(p['excerpt'], quote=True))
        open(os.path.join(ROOT, 'p', pid + '.html'), 'w', encoding='utf-8').write(page)
        print('  %-9s %-44s %6d B' % (
            pid, p['title'][:40],
            os.path.getsize(os.path.join(ROOT, 'og', pid + '.jpg'))))

    print('\n%d essays -> p/*.html + og/*.jpg' % len(posts))


if __name__ == '__main__':
    main()
