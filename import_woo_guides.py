#!/usr/bin/env python3
"""One-off import (2026-11-06): one page per YouTube video for the two WooCommerce guides, like the PS guides.

Writes src/sizechart-woo/ and src/minmax-woo/ (pages.json + <slug>.html + assets/). Each video page has the video,
the timed narration, the reference text of the matching PrestaShop page reworded for WooCommerce, and numbered steps
with the screen at the end of each step (from the final clip). Group pages are written here by hand.
After this import the pages are edited by hand; do not run it again unless you want to throw those edits away.

    python3 tools/docsite/import_woo_guides.py
"""
import html
import json
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGINS = Path('/home/asha/projects/wordpress/plugins')

SC_PRO = '<p class="note"><b>Pro add-on.</b> This feature needs <a href="{{link:sizechart-woo-pro}}">ILM Size Chart Pro</a>.</p>\n'
MM_PRO = '<p class="note"><b>Pro add-on.</b> This feature needs the Pro add-on. See <a href="{{page:minmax-woo:free-and-pro}}">Free and Pro</a>.</p>\n'

COMMON = [
    (r'\bthe module\b', 'the plugin'), (r'\bThe module\b', 'The plugin'), (r'\bthis module\b', 'this plugin'),
    (r'\bmodule\b', 'plugin'), (r'\bModule\b', 'Plugin'), (r'back office', 'WordPress admin'),
    (r'\bcombinations\b', 'variations'), (r'\bcombination\b', 'variation'), (r'\bCombinations\b', 'Variations'), (r'\bCombination\b', 'Variation'),
    (r'\bcolor\b', 'colour'),
]
SC_WORDS = COMMON + [
    (r'\bsuppliers\b', 'tags'), (r'\bSuppliers\b', 'Tags'), (r'\bSupplier\b', 'Tag'), (r'\bsupplier\b', 'tag'),
    (r'\bfeatures\b', 'attributes'), (r'\bFeatures\b', 'Attributes'), (r'\bFeature\b', 'Attribute'), (r'\bfeature\b', 'attribute'),
]
MM_WORDS = COMMON + [
    (r'\bsuppliers\b', 'tags'), (r'\bSuppliers\b', 'Tags'), (r'\bSupplier\b', 'Tag'), (r'\bsupplier\b', 'tag'),
    (r'\bcustomer groups\b', 'user roles'), (r'\bcustomer group\b', 'user role'), (r'\bCustomer Group\b', 'User Role'),
    (r'\bgroups\b', 'roles'), (r'\bgroup\b', 'role'),
]

SC_TREE = [
    ('getting-started', 'Getting started',
     '<p>Install the plugin, activate the Pro licence if you have it, find your way in the size chart list and make your first chart.</p>\n'
     '<h2>Requirements</h2>\n<table class="fieldtable">\n<tr><th>Requirement</th><th>Minimum</th></tr>\n<tr><td>WordPress</td><td>6.2</td></tr>\n'
     '<tr><td>WooCommerce</td><td>7.0</td></tr>\n<tr><td>PHP</td><td>7.4</td></tr>\n</table>\n',
     [('01-install-licence', 'install-and-activate', 'install-and-activate', 0), ('02-size-chart-list', 'the-size-chart-list', 'the-size-chart-list', 0),
      ('03-first-size-chart', 'your-first-size-chart', 'your-first-size-chart', 0)]),
    ('general', 'General tab', '<p>The General tab names the chart, switches it on or off, and decides how it shows on the product page.</p>\n',
     [('04-show-on-page', 'show-on-the-page', 'show-on-the-page', 0), ('05-status-and-priority', 'status-and-priority', 'status-and-priority', 0),
      ('06-find-my-size', 'find-my-size', 'find-my-size', 1)]),
    ('popup-button', 'Popup Button tab', None,
     [('07-popup-button-basics', 'popup-button-text-and-place', 'popup-button-text-and-place', 0), ('08-popup-button-text', 'popup-button-font-and-text', 'popup-button-font-and-text', 0),
      ('09-popup-button-colours', 'popup-button-colours-and-border', 'popup-button-colours-and-border', 0), ('10-popup-button-icon', 'popup-button-icon', 'popup-button-icon', 0),
      ('11-popup-window-size', 'popup-window-size-and-position', 'popup-window-size-and-position', 0), ('12-popup-window-style', 'popup-window-style-and-animation', 'popup-window-style-and-animation', 0),
      ('13-close-button', 'close-button', 'close-button', 0), ('14-preview-devices', 'preview-on-phone-and-tablet', 'preview-on-phone-and-tablet', 0)]),
    ('designer', 'Sizechart Designer', None,
     [('15-rows-and-columns', 'rows-and-columns', 'rows-and-columns', 0), ('16-table-content', 'table-sizes-and-measurements', 'table-sizes-and-measurements', 0),
      ('17-table-units', 'table-units', 'table-units', 0), ('18-table-style', 'table-style', 'table-style', 0), ('19-text-editor', 'text-editor', 'text-editor', 0),
      ('20-image', 'image', 'image', 0), ('21-video', 'video', 'video', 0), ('22-tabs', 'tabs', 'tabs', 0), ('23-themes', 'themes', 'themes', 0),
      ('24-export-import', 'export-and-import', 'export-and-import', 0)]),
    ('display-rules', 'Display rules', None,
     [('25-rule-categories', 'categories', 'categories', 0), ('26-rule-brands-tags', 'brands-and-tags', 'brands-and-suppliers', 0),
      ('27-rule-attributes', 'attributes', 'features', 0), ('28-apply-constrain', 'any-or-all', 'any-or-all', 0), ('29-shortcode', 'shortcode', None, 0)]),
    ('ai-assistant', 'AI assistant', None,
     [('30-ai-settings', 'ai-settings', 'ai-settings', 1), ('31-create-with-ai', 'create-with-ai', 'create-with-ai', 1), ('32-ai-design-assistant', 'ai-design-assistant', 'ai-design-assistant', 1)]),
]
SC_LAST = [('33-uninstall', 'uninstall-and-delete', None, 0)]

MM_TREE = [
    ('getting-started', 'Getting started',
     '<p>Install the plugin, add the Pro add-on if you have it, and activate your licence. The plugin sits under <b>WooCommerce &gt; ILM Min Max</b>.</p>\n'
     '<h2>Requirements</h2>\n<table class="fieldtable">\n<tr><th>Requirement</th><th>Minimum</th></tr>\n<tr><td>WordPress</td><td>6.2</td></tr>\n'
     '<tr><td>WooCommerce</td><td>8.2</td></tr>\n<tr><td>PHP</td><td>7.4</td></tr>\n</table>\n',
     [('01-install-licence', 'install-and-activate', 'install-and-activate', 0)]),
    ('configuration', 'Configuration', 'PS:configuration',
     [('03-minimum-quantity', 'minimum-quantity', 'minimum-quantity', 0), ('04-maximum-quantity', 'maximum-quantity', 'maximum-quantity', 0),
      ('05-multiples-of-quantity', 'multiples-of-quantity', 'multiples-of-quantity', 0), ('06-limit-multiple-quantity', 'limit-multiple-quantity', 'limit-multiple-quantity', 0),
      ('07-allowed-quantities', 'allowed-quantities', 'allowed-quantities', 1), ('08-minimum-maximum-amount', 'minimum-and-maximum-amount', 'minimum-and-maximum-amount', 1),
      ('09-amounts-include-tax', 'amounts-include-tax', 'amounts-include-tax', 1), ('10-different-products-per-order', 'different-products-per-order', 'different-products-per-order', 1),
      ('11-auto-save', 'auto-save', 'auto-save', 0), ('18-rule-priority', 'rule-priority-order', 'rule-priority-order', 1), ('19-attributes', 'attributes', 'attributes', 0)]),
    ('rules', 'Quantity / Amount rules', 'PS:rules',
     [('12-product-rule-variations', 'product-rules-and-variations', 'product-rules-and-combinations', 0), ('40-product-edit-fields', 'limits-on-the-product-edit-page', None, 0),
      ('13-category-rule', 'category-rule', 'category-rule', 1), ('14-brand-rule', 'brand-rule', 'brand-rule', 1), ('15-tag-rule', 'tag-rule', 'supplier-rule', 1),
      ('16-user-role-rule', 'user-role-rule', 'customer-group-rule', 1), ('17-global-rule', 'global-rule', 'global-rule', 0), ('23-table-filters', 'rule-table-filters', 'rule-table-filters', 0),
      ('20-status-bulk', 'status-and-bulk-actions', 'status-and-bulk-actions', 1), ('21-conditions', 'conditions', 'conditions', 1), ('22-one-customer-rule', 'rule-for-one-customer', 'rule-for-one-customer', 1)]),
    ('duration-rules', 'Duration rules', 'PS:duration-rules',
     [('24-duration-per-order', 'per-order-no-time-limit', 'per-order-no-time-limit', 1), ('25-duration-date-range', 'active-only-in-a-date-range', 'active-only-in-a-date-range', 1),
      ('26-duration-lifetime', 'lifetime-total', 'lifetime-total', 1), ('27-duration-fixed-range', 'total-in-a-fixed-date-range', 'total-in-a-fixed-date-range', 1),
      ('28-duration-rolling', 'rolling-window', 'rolling-window', 1), ('29-duration-custom-start', 'custom-start-and-length', 'custom-start-and-length', 1),
      ('30-duration-order-statuses', 'which-order-statuses-count', 'which-order-statuses-count', 1)]),
    ('tools', 'Templates, CSV and log', 'PS:tools',
     [('31-rule-templates', 'rule-templates', 'rule-templates', 1), ('32-export-import', 'export-and-import', 'export-and-import', 1), ('33-blocked-attempts', 'blocked-attempts', 'blocked-attempts', 1)]),
    ('messages-and-storefront', 'Messages and storefront', 'PS:messages-and-storefront',
     [('34-messages', 'customer-messages', 'customer-messages', 0), ('35-pack-price', 'pack-price-message-and-position', 'pack-price-message-and-position', 1),
      ('36-product-page-info', 'product-page-information', 'product-page-information', 1), ('37-checkout-protection', 'checkout-protection', 'checkout-protection', 1),
      ('38-custom-css', 'custom-css', 'custom-css', 1)]),
    ('ai-assistant', 'AI Assistant', '<p>Describe your limits in your own words and let the AI build the rules. It needs the Pro add-on.</p>\n',
     [('39-ai-assistant', 'ai-assistant-rules', None, 1)]),
]
MM_LAST = [('02-uninstall', 'uninstall-and-delete', 'uninstall-and-delete', 0)]


def words(text, table):
    for a, b in table:
        text = re.sub(a, b, text)
    return text


def ps_details(ps_dir, name, table):
    """The PrestaShop page text without its pictures (they show PrestaShop), reworded for WooCommerce."""
    if not name:
        return ''
    f = ps_dir / f'{name}.html'
    if not f.exists():
        raise SystemExit('missing PS page ' + name)
    text = f.read_text(encoding='utf-8')
    text = re.sub(r'<p class="caption">.*?</p>\s*', '', text, flags=re.S)
    text = re.sub(r'<img [^>]*>\s*', '', text)
    return words(text, table).strip()


def srt_starts(path):
    cues = []
    for block in path.read_text(encoding='utf-8').strip().split('\n\n'):
        lines = block.split('\n')
        h, m, s = lines[1].split(' --> ')[0].replace(',', '.').split(':')
        cues.append((int(h) * 3600 + int(m) * 60 + float(s), ' '.join(lines[2:]).strip()))
    return cues


def steps(video, cid):
    tl = json.loads((video / 'work' / 'tl' / f'{cid}.json').read_text(encoding='utf-8'))
    cues = srt_starts(video / 'out' / f'{cid}-en.srt')
    out, c = [], 0
    for s in tl:
        say = (s.get('say') or '').strip()
        if not say:
            continue
        k = c
        while k < len(cues) and not say.startswith(cues[k][1][:20]):
            k += 1
        if k < len(cues):
            c = k
            t = cues[c][0]
        else:
            t = out[-1]['t'] if out else 0
        out.append({'t': t, 'text': say})
    return out


def duration(mp4):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(mp4)]))


def build(key, video, ps_key, tree, last, table, pro_note, extra):
    out = HERE / 'src' / key
    out.mkdir(parents=True, exist_ok=True)
    (out / 'assets').mkdir(exist_ok=True)
    ps_dir = HERE / 'src' / ps_key
    yt = json.loads((video / 'out' / 'youtube.json').read_text(encoding='utf-8'))
    used = set()

    def clip_page(cid, slug, ps, pro):
        c = subprocess.check_output(['node', '-e', f"const c=require('{video}/clips/{cid}.cjs');console.log(JSON.stringify({{title:c.title,sub:c.sub}}))"])
        c = json.loads(c)
        mp4 = video / 'out' / f'{cid}-en.mp4'
        total = duration(mp4)
        st = steps(video, cid)
        body = [pro_note] if pro else []
        det = ps_details(ps_dir, ps, table)
        if det:
            body.append(det)
        body.append('<h2>Step by step</h2>\n<ol class="steps">')
        rest = st[1:]
        for i, s in enumerate(rest):
            nxt = rest[i + 1]['t'] if i + 1 < len(rest) else total
            stop = max(nxt - 3.0, s['t'] + (nxt - s['t']) * 0.6)  # the voice leads: later frames already show the next action
            name = f'{slug}-{i + 1}.jpg'
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{stop:.2f}', '-i', str(mp4), '-frames:v', '1', '-vf', 'scale=1280:-2',
                            '-q:v', '5', str(out / 'assets' / name)], check=True)
            body.append(f'<li><p>{html.escape(s["text"], quote=False)}</p>\n<img class="shot" src="assets/{name}" alt="{html.escape(c["title"], quote=False)}, step {i + 1}"></li>')
        body.append('</ol>')
        (out / f'{slug}.html').write_text('\n'.join(body) + '\n', encoding='utf-8')
        used.add(cid)
        return {'slug': slug, 'title': c['title'], 'file': f'{slug}.html', 'lead': c['sub'],
                'video': {'yt': yt['videos'][cid], 'len': f'{int(total // 60)}:{int(total % 60):02d}', 'clip': cid},
                'intro': st[0]['text'], 'steps': [{'t': int(s['t']), 'text': s['text']} for s in rest]}

    pages = []
    for slug, title, text, kids in tree:
        if text is None or text.startswith('PS:'):
            text = ps_details(ps_dir, text[3:] if text else slug, table)
        (out / f'{slug}.html').write_text(text + '\n', encoding='utf-8')
        pages.append({'slug': slug, 'title': title, 'file': f'{slug}.html', 'pages': [clip_page(*k) for k in kids]})
        print(key, slug, len(kids), flush=True)
    pages += extra(out)
    pages += [clip_page(*k) for k in last]
    missing = set(yt['videos']) - used
    if missing:
        raise SystemExit('videos without a page: ' + ' '.join(sorted(missing)))
    (out / 'pages.json').write_text(json.dumps({'playlist': yt['playlist'], 'pages': pages}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def plain_page(out, slug, title, text):
    (out / f'{slug}.html').write_text(text.strip() + '\n', encoding='utf-8')
    return {'slug': slug, 'title': title, 'file': f'{slug}.html'}


def sc_extra(out):
    old = HERE / 'src' / 'sizechart-woo-free'
    def chapter(name):
        text = (old / name).read_text(encoding='utf-8')
        text = re.sub(r'^<h1>.*?</h1>\s*', '', text, flags=re.S)
        return re.sub(r'<h3 class="sub">\d+\.\d+ (.*?)</h3>', r'<h2>\1</h2>', text)
    front = chapter('04-on-the-storefront.html').replace('{{link:sizechart-woo-free:3}}', '{{page:sizechart-woo:your-first-size-chart}}')
    for a in re.findall(r'src="assets/([^"]+)"', front):
        shutil.copyfile(old / 'assets' / a, out / 'assets' / a)
    return [plain_page(out, 'on-the-storefront', 'On the storefront', front),
            plain_page(out, 'free-and-pro', 'Free and Pro', chapter('06-free-and-pro.html'))]


def mm_extra(out):
    return [plain_page(out, 'free-and-pro', 'Free and Pro', '''
<p>The free plugin handles the quantity limits of each product and variation. The Pro add-on is a separate plugin that needs the free plugin and adds every other rule type.</p>
<table class="fieldtable">
<tr><th>Feature</th><th>Free</th><th>Pro</th></tr>
<tr><td>Minimum, maximum and multiple quantity per product and variation</td><td>Yes</td><td>Yes</td></tr>
<tr><td>Limits on the product edit page and in the rule table, with search, category filter and Auto Save</td><td>Yes</td><td>Yes</td></tr>
<tr><td>Shop-wide global value for these limits</td><td>Yes</td><td>Yes</td></tr>
<tr><td>Checked on the product page, in the cart and at checkout, classic and block</td><td>Yes</td><td>Yes</td></tr>
<tr><td>Customer messages</td><td>Yes</td><td>Yes</td></tr>
<tr><td>Category, brand, tag, user role, customer and global rules</td><td>&mdash;</td><td>Yes</td></tr>
<tr><td>Minimum and maximum amounts, allowed quantity lists, different products per order</td><td>&mdash;</td><td>Yes</td></tr>
<tr><td>Duration rules, conditions, rule templates</td><td>&mdash;</td><td>Yes</td></tr>
<tr><td>CSV export and import, blocked attempts log</td><td>&mdash;</td><td>Yes</td></tr>
<tr><td>Pack price, product page information, Custom CSS</td><td>&mdash;</td><td>Yes</td></tr>
<tr><td>AI Assistant</td><td>&mdash;</td><td>Yes</td></tr>
</table>
''')]


if __name__ == '__main__':
    build('sizechart-woo', PLUGINS / 'ilmsizechart-woo/marketplace/video/guide', 'sizechart-ps', SC_TREE, SC_LAST, SC_WORDS, SC_PRO, sc_extra)
    build('minmax-woo', PLUGINS / 'ilm-minmax-woo/marketplace/video/guide', 'minmax-ps', MM_TREE, MM_LAST, MM_WORDS, MM_PRO, mm_extra)
