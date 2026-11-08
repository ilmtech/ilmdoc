#!/usr/bin/env python3
"""One-off import (2026-10-25): split the Min/Max readme into one page per YouTube video.

Writes src/minmax-ps/pages.json (page tree, video, timed steps) and src/minmax-ps/<slug>.html
(the reference text of each page), and copies the readme pictures to src/minmax-ps/assets.
After this import the pages are edited by hand in src/minmax-ps; do not run it again unless
you want to throw those edits away.

    python3 tools/docsite/import_minmax_pages.py
"""
import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOD = Path('/home/asha/projects/prestashop/modules/ilmminmaxorderqty/marketplace')
README = MOD / 'docs' / 'readme_en.html'
VIDEO = MOD / 'video' / 'guide'
OUT = HERE / 'src' / 'minmax-ps'

src = README.read_text(encoding='utf-8')
BODY = re.search(r'<body[^>]*>(.*)</body>', src, re.S).group(1)
BODY = re.sub(r'<footer class="pagefoot">.*?</footer>', '', BODY, flags=re.S)
LICENCE = (HERE / 'src' / 'minmax-licence.html').read_text(encoding='utf-8').replace('extra:minmax-assets/', 'assets/')


def cut(start, end=None, text=BODY):
    """The readme from `start` (included) up to `end` (excluded); both must exist."""
    i = text.index(start)
    j = text.index(end, i + len(start)) if end else len(text)
    return text[i:j].strip()


def row(name):
    """One row of a settings table, as a two-column table with its header."""
    m = re.search(r'<tr><td>' + re.escape(name) + r'</td>.*?</tr>', BODY, re.S)
    return m.group(0)


def table(*rows, head=('Setting', 'What it does')):
    return ('<table class="fieldtable">\n  <tr><th>%s</th><th>%s</th></tr>\n  ' % head
            + '\n  '.join(rows) + '\n</table>')


def sub_to_h2(html):
    html = re.sub(r'<h3 class="sub">\d+\.\d+ (.*?)</h3>', r'<h2>\1</h2>', html)
    html = re.sub(r'<h4 class="subsub">(.*?)</h4>', r'<h2>\1</h2>', html)
    return re.sub(r'\s*\(see Section [\d.]+\)', '', html)


# "Section n.n" of the readme -> a link to the page that now holds it
SECTION_LINKS = [
    (' (see Section 3.3)', ' (see <a href="{{page:minmax-ps:rule-for-one-customer}}">A rule for one customer</a>)'),
    (' (see Section 3.1)', ' (see <a href="{{page:minmax-ps:status-and-bulk-actions}}">Status</a>)'),
    (' (see Section 3.2)', ' (see <a href="{{page:minmax-ps:conditions}}">Conditions</a>)'),
    (' (see Section 4)', ' (see <a href="{{page:minmax-ps:duration-rules}}">Duration rules</a>)'),
    (' (see Checkout protection in Section 8.3)', ' (see <a href="{{page:minmax-ps:checkout-protection}}">Checkout protection</a>)'),
    (' switched on (Section 8.3)', ' switched on'),
]


LEVELS = cut('<table class="fieldtable">\n  <tr><th>Level</th>', '<p><b>Apply Rule')
INDIVIDUAL = cut('<p><b>Apply Rule to Individual Products</b>', '<p><b>Attributes:</b>')
DURATION_TYPES = cut('<table class="fieldtable">\n  <tr><th>Type</th>', '<p>Types that need extra input')
ADV = cut('<h3 class="sub">8.3 Advanced</h3>', '<h2 class="section">9.')


def li(name):
    return re.search(r'<li><b>' + re.escape(name) + r'</b>.*?</li>', ADV, re.S).group(0)


# slug, menu title, video number (or None), page text
TREE = [
    ('getting-started', 'Getting started', None, None, [
        ('install-and-activate', 'Install and activate', '01',
         cut('<h2 class="section">1. Installation</h2>', '<h2 class="section">2.').split('</h2>', 1)[1] + '\n'
         + LICENCE.replace('<h3 class="sub">1.1 Activating your licence</h3>', '<h2>Activating your licence</h2>')),
        ('the-six-tabs', 'The six tabs', None,
         cut('<h2 class="section">2. Configure', '<h2 class="section">3.').split('</h2>', 1)[1]),
    ]),
    ('configuration', 'Configuration', None,
     '<p>The <b>Configuration</b> tab has three sub-tabs: <b>General</b>, <b>Messages</b> and <b>Advanced</b>. '
     'On <b>General</b>, each switch adds its own column to the Quantity/Amount Rule table, and the value next to it '
     'is the shop-wide (Global) default, used until a more specific rule overrides it.</p>\n'
     '<img class="shot" src="assets/07a_config_general_top.png">\n'
     + cut('<table class="fieldtable">\n  <tr><th>Setting</th>', '<img class="shot" src="assets/07c'), [
        ('minimum-quantity', 'Minimum Quantity', '03', table(row('Minimum Quantity'))),
        ('maximum-quantity', 'Maximum Quantity', '04', table(row('Maximum Quantity'))),
        ('multiples-of-quantity', 'Multiples of Quantity', '05',
         table(row('Multiplies of Quantity').replace('Multiplies', 'Multiples'), row('Start from the minimum'))),
        ('limit-multiple-quantity', 'Limit Multiple Quantity', '06', table(row('Limit Multiple Quantity'))),
        ('allowed-quantities', 'Allowed Quantities', '07', table(row('Allowed Quantities'), row('Allowed Qty'))),
        ('minimum-and-maximum-amount', 'Minimum and Maximum Amount', '08',
         table(row('Minimum Amount'), row('Maximum Amount'))
         + '\n<img class="shot" src="assets/07c_config_general_new.png">\n'
           '<p class="caption">Allowed Quantities, Minimum Amount, Maximum Amount, Amounts include tax and Different products per order.</p>'),
        ('amounts-include-tax', 'Amounts include tax', '09', table(row('Amounts include tax'))),
        ('different-products-per-order', 'Different products per order', '10', table(row('Different products per order'))),
        ('auto-save', 'Auto Save', '11', table(row('Auto Save'))),
        ('rule-priority-order', 'Rule priority order', '18',
         sub_to_h2(cut('<p>Choose which levels a rule can be attached to.', '<p><b>Attributes:</b>'))),
        ('attributes', 'Attributes setting', '19', cut('<p><b>Attributes:</b>', '<h3 class="sub">8.2')),
    ]),
    ('rules', 'Quantity / Amount rules', None,
     sub_to_h2(cut('<h2 class="section">3. Quantity', '<h3 class="sub">3.1').split('</h2>', 1)[1]), [
        ('product-rules-and-combinations', 'Product rules and combinations', '12', table(row('Product Rule'), head=('Level', 'What it does'))),
        ('category-rule', 'Category rule', '13', table(row('Category Rule'), head=('Level', 'What it does')) + '\n' + INDIVIDUAL),
        ('brand-rule', 'Brand rule', '14', table(row('Brand Rule'), head=('Level', 'What it does')) + '\n' + INDIVIDUAL),
        ('supplier-rule', 'Supplier rule', '15', table(row('Supplier Rule'), head=('Level', 'What it does')) + '\n' + INDIVIDUAL),
        ('customer-group-rule', 'Customer group rule', '16', table(row('Customer Group Rule'), head=('Level', 'What it does')) + '\n' + INDIVIDUAL),
        ('global-rule', 'Global rule', '17', table(row('Global Rule'), head=('Level', 'What it does')) + '\n' + INDIVIDUAL),
        ('rule-table-filters', 'Rule table filters', '23',
         table(row('Search'), row('Customer Group'), row('Customer'), row('Category'), row('Rule Type'), head=('Field', 'What it does'))),
        ('status-and-bulk-actions', 'Status, switching off and bulk actions', '20',
         cut('<h3 class="sub">3.1', '<h3 class="sub">3.2').split('</h3>', 1)[1]),
        ('conditions', 'Conditions', '21', cut('<h3 class="sub">3.2', '<h3 class="sub">3.3').split('</h3>', 1)[1]),
        ('rule-for-one-customer', 'A rule for one customer', '22', cut('<h3 class="sub">3.3', '<h2 class="section">4.').split('</h3>', 1)[1]),
    ]),
    ('duration-rules', 'Duration rules', None,
     sub_to_h2(cut('<h2 class="section">4. Duration', '<h2 class="section">5.').split('</h2>', 1)[1]), [
        ('per-order-no-time-limit', 'Per order, no time limit', '24', table(row('<b>Per order &middot; No time limit</b>'), head=('Type', 'Meaning'))),
        ('active-only-in-a-date-range', 'Active only in a date range', '25', table(row('<b>Per order &middot; Active only in date range</b>'), head=('Type', 'Meaning'))),
        ('lifetime-total', 'Lifetime total', '26', table(row('<b>Total &middot; All-time (lifetime)</b>'), head=('Type', 'Meaning'))),
        ('total-in-a-fixed-date-range', 'Total in a fixed date range', '27', table(row('<b>Total &middot; Fixed date range</b>'), head=('Type', 'Meaning'))),
        ('rolling-window', 'Rolling window', '28', table(row('<b>Total &middot; Rolling window</b>'), head=('Type', 'Meaning'))
         + '\n' + cut('<p>Types that need extra input', '<p><span class="step-label">Step 3')),
        ('custom-start-and-length', 'Custom start and length', '29', table(row('<b>Total &middot; Custom start + duration</b>'), head=('Type', 'Meaning'))),
        ('which-order-statuses-count', 'Which order statuses count', '30', cut('<p><span class="step-label">Step 3 &mdash;', '<h2 class="section">5.')),
    ]),
    ('tools', 'Templates, CSV and log', None,
     '<p>Three tabs help you work faster and see what happens in the shop: Rule Templates, Export / Import and Blocked Attempts.</p>', [
        ('rule-templates', 'Rule templates', '31', cut('<h2 class="section">5.', '<h2 class="section">6.').split('</h2>', 1)[1]),
        ('export-and-import', 'Export and import (CSV)', '32', cut('<h2 class="section">6.', '<h2 class="section">7.').split('</h2>', 1)[1]),
        ('blocked-attempts', 'Blocked attempts log', '33', sub_to_h2(cut('<h2 class="section">7.', '<h2 class="section">8.').split('</h2>', 1)[1])),
    ]),
    ('messages-and-storefront', 'Messages and storefront', None,
     '<p>What the shopper sees: the messages shown when a rule stops them, the information on the product page, '
     'the pack price, the checkout lock and your own CSS. All of it is set on <b>Configuration &gt; Messages</b> and '
     '<b>Configuration &gt; Advanced</b>.</p>\n<img class="shot" src="assets/11_config_advanced.png">', [
        ('customer-messages', 'Customer messages', '34', cut('<h3 class="sub">8.2', '<h3 class="sub">8.3').split('</h3>', 1)[1]),
        ('pack-price-message-and-position', 'Pack price message and position', '35',
         '<ul class="legend">\n  ' + li('Step Quantity Price Message') + '\n  ' + li('Product Position / Product List Position') + '\n</ul>'),
        ('product-page-information', 'Product page information', '36',
         '<ul class="legend">\n  ' + li('Product page information') + '\n</ul>\n'
         + cut('<p>With <b>Product page information</b>', '<p>If the cart still breaks')),
        ('checkout-protection', 'Checkout protection', '37',
         '<ul class="legend">\n  ' + li('Checkout protection') + '\n</ul>\n'
         + cut('<img class="shot" src="assets/11b', '<h2 class="section">9.')
         + '\n' + cut('<p>If the cart still breaks', '<h2 class="section">10.')),
        ('custom-css', 'Custom CSS', '38', '<ul class="legend">\n  ' + li('Custom CSS') + '\n</ul>'),
        ('on-the-storefront', 'Seeing it on the storefront', None,
         re.sub(r'\s*\(Section [\d.]+\)|,? (in|from) Section [\d.]+|\s*&mdash; this attempt is the same one that appears in the Blocked Attempts log in Section 7',
                '', cut('<h2 class="section">9.', '<h2 class="section">10.').split('</h2>', 1)[1])),
    ]),
    ('uninstall-and-delete', 'Uninstall and delete', '02', cut('<h2 class="section">10.').split('</h2>', 1)[1], None),
]


def srt_starts(path):
    cues = []
    for block in path.read_text(encoding='utf-8').strip().split('\n\n'):
        lines = block.split('\n')
        h, m, s = lines[1].split(' --> ')[0].replace(',', '.').split(':')
        cues.append((int(h) * 3600 + int(m) * 60 + float(s), ' '.join(lines[2:]).strip()))
    return cues


def steps(clip_id):
    """Narration of the clip with the time each line starts in the published video."""
    tl = json.loads((VIDEO / 'work' / 'tl' / f'{clip_id}.json').read_text(encoding='utf-8'))
    cues = srt_starts(VIDEO / 'out' / f'{clip_id}-en.srt')
    out, c = [], 0
    for s in tl:
        say = s['say'].strip()
        while c < len(cues) and not say.startswith(cues[c][1][:20]):
            c += 1
        t = cues[c][0] if c < len(cues) else s['t']
        if out and say[:1].islower():
            out[-1]['text'] += ' ' + say
        else:
            out.append({'t': round(t), 'text': say})
    return out


def main():
    videos = {v['id'][:2]: v for v in json.loads((HERE / 'src' / 'minmax-videos.json').read_text(encoding='utf-8'))['videos']}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'assets').mkdir(exist_ok=True)
    pictures = set()

    def page(slug, title, num, html, kids):
        p = {'slug': slug, 'title': title}
        if num:
            v = videos[num]
            st = steps(v['id'])
            p.update({'title': v['title'] if not v['title'].startswith('Duration: ') else title,
                      'video': {'yt': v['yt'], 'len': v['len'], 'clip': v['id']},
                      'lead': v['sub'], 'intro': st[0]['text'], 'steps': st[1:]})
        if html:
            for a, b in SECTION_LINKS:
                html = html.replace(a, b)
            pictures.update(re.findall(r'src="assets/([^"]+)"', html))
            (OUT / f'{slug}.html').write_text(html.strip() + '\n', encoding='utf-8')
            p['file'] = f'{slug}.html'
        if kids:
            p['pages'] = [page(*k, None) for k in kids]
        return p

    tree = [page(*t) for t in TREE]
    for name in pictures:
        for d in (MOD / 'docs' / 'assets', HERE / 'src' / 'minmax-assets'):
            if (d / name).is_file():
                shutil.copyfile(d / name, OUT / 'assets' / name)
                break
        else:
            raise SystemExit('missing picture ' + name)
    (OUT / 'pages.json').write_text(json.dumps({'playlist': 'https://www.youtube.com/playlist?list=PLPYTROnNCGQA',
                                                'pages': tree}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    n = sum(1 + len(p.get('pages', [])) for p in tree)
    print(f'{n} pages, {len(pictures)} pictures -> {OUT}')


if __name__ == '__main__':
    main()
