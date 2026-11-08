#!/usr/bin/env python3
"""One-off import (2026-11-04): split the Size Chart (PrestaShop) readme into one page per YouTube video,
like the Min/Max guide (import_minmax_pages.py).

Writes src/sizechart-ps/pages.json (page tree, video, timed steps) and src/sizechart-ps/<slug>.html
(the reference text of each page), and copies the readme pictures to src/sizechart-ps/assets.
Video ids come from the guide's out/youtube.json, titles from its clips/NN-*.cjs, lengths from the mp4s.
After this import the pages are edited by hand in src/sizechart-ps; do not run it again unless
you want to throw those edits away.

    python3 tools/docsite/import_sizechart_pages.py
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOD = Path('/home/asha/projects/prestashop/modules/ilmsizechart/marketplace')
README = MOD / 'docs' / 'readme_en.html'
VIDEO = MOD / 'video' / 'guide'
OUT = HERE / 'src' / 'sizechart-ps'
KEY = 'sizechart-ps'

src = README.read_text(encoding='utf-8')
BODY = re.search(r'<body[^>]*>(.*)</body>', src, re.S).group(1)
BODY = re.sub(r'<footer class="pagefoot">.*?</footer>', '', BODY, flags=re.S)
# the readme only names the Addons Order ID; ilmtech.in orders activate the same way
BODY = BODY.replace(
    'type the <b>Order ID</b> of your purchase &mdash; you find it in your PrestaShop Addons account under <b>Orders</b>.',
    'type the <b>Order ID</b> of your purchase: the order reference on ilmtech.in (in your order e-mail and under '
    '<b>My account &gt; Order history</b>), or the Order ID in your PrestaShop Addons account under <b>Orders</b>.')


def cut(start, end=None, text=BODY):
    """The readme from `start` (included) up to `end` (excluded); both must exist."""
    i = text.index(start)
    j = text.index(end, i + len(start)) if end else len(text)
    return text[i:j].strip()


def after(start, end=None):
    """Like cut(), without the heading line that `start` opens."""
    return re.split(r'</h[234]>', cut(start, end), maxsplit=1)[1].strip()


def row(name, text=BODY):
    m = re.search(r'<tr><td>' + re.escape(name) + r'</td>.*?</tr>', text, re.S)
    if not m:
        raise SystemExit('missing table row ' + name)
    return m.group(0)


def table(*rows, head=('Field', 'What it does')):
    return ('<table class="fieldtable">\n  <tr><th>%s</th><th>%s</th></tr>\n  ' % head
            + '\n  '.join(rows) + '\n</table>')


def li(name, text=BODY):
    m = re.search(r'<li><b>' + re.escape(name) + r'</b>.*?</li>', text, re.S)
    if not m:
        raise SystemExit('missing list item ' + name)
    return '<ul class="legend">\n  ' + m.group(0) + '\n</ul>'


def img(name, caption=''):
    cls = 'shot shot-narrow' if re.search(r'<img class="shot shot-narrow" src="assets/' + re.escape(name), BODY) else 'shot'
    return f'<img class="{cls}" src="assets/{name}">' + (f'\n<p class="caption">{caption}</p>' if caption else '')


S31 = cut('<h3 class="sub">3.1', '<h3 class="sub">3.2')
S32 = cut('<h3 class="sub">3.2', '<h3 class="sub">3.3')
S33 = cut('<h3 class="sub">3.3', '<h3 class="sub">3.4')
S34 = cut('<h3 class="sub">3.4', '<h2 class="section">4.')
COMPONENTS = cut('<table class="fieldtable">\n  <tr><th>Component</th>', '<p>Click a component', S33)
EDIT_TABLE = cut('<h4 class="subsub">Editing a table</h4>', '<h4 class="subsub">Themes</h4>', S33)
TOOLBAR = cut('<table class="fieldtable">\n  <tr><th>Toolbar button</th>', '</table>', S33) + '\n</table>'
STYLE_TABS = cut('<p>Click a component to edit it.', '<h4 class="subsub">Editing a table</h4>', S33)
WHICH = cut('<p><b>Which chart does a product show?</b>', None, S34)
EDIT_INTRO = cut('<p>Click <b>Add Size Chart</b>, or the title of an existing chart.', '<h3 class="sub">3.1')

# "Section n.n" of the readme -> a link to the page that now holds it
SECTION_LINKS = [
    ('(Section 4.3)', '(see <a href="{{page:sizechart-ps:ai-design-assistant}}">AI design assistant</a>)'),
    ('(Section 4.2)', '(see <a href="{{page:sizechart-ps:create-with-ai}}">Create with AI</a>)'),
    ('(Section 4.1)', '(see <a href="{{page:sizechart-ps:ai-settings}}">AI settings</a>)'),
    ('(Section 4)', '(see <a href="{{page:sizechart-ps:ai-assistant}}">AI assistant</a>)'),
    ('(Section 3.1)', '(see <a href="{{page:sizechart-ps:find-my-size}}">Find my size</a>)'),
    ('(Section 1.1)', '(see <a href="{{page:sizechart-ps:install-and-activate}}">Install and activate</a>)'),
]

# slug, menu title, video number (or None), page text, kids
TREE = [
    ('getting-started', 'Getting started', None,
     '<p>Install the module, activate your licence, find your way in the size chart list and make your first chart.</p>', [
        ('install-and-activate', 'Install and activate', '01',
         after('<h2 class="section">1.', '<h3 class="sub">1.1') + '\n<h2>Activating your licence</h2>\n'
         + after('<h3 class="sub">1.1', '<h2 class="section">2.')),
        ('the-size-chart-list', 'The size chart list', '02', after('<h2 class="section">2.', '<h2 class="section">3.')),
        ('your-first-size-chart', 'Your first size chart', '03', EDIT_INTRO),
    ]),
    ('general', 'General tab', None, after('<h3 class="sub">3.1', '<p>With <b>Show in = Page</b>'), [
        ('show-on-the-page', 'Show the chart on the page', '04',
         table(row('Show in', S31)) + '\n' + cut('<p>With <b>Show in = Page</b>', None, S31)),
        ('status-and-priority', 'Status and priority', '05', table(row('Status', S31), row('Priority', S31)) + '\n' + WHICH),
        ('find-my-size', 'Find my size', '06', table(row('Find my size', S31))
         + '\n' + cut('<p>With <b>Find my size</b> switched on', '<p class="note">The chart shows')),
    ]),
    ('popup-button', 'Popup Button tab', None,
     cut('<p>Designs everything the shopper sees', '<ul class="legend">', S32), [
        ('popup-button-text-and-place', 'Popup button: text and place', '07', li('Button', S32)),
        ('popup-button-font-and-text', 'Popup button: font and text', '08', li('Button', S32)),
        ('popup-button-colours-and-border', 'Popup button: colours and border', '09', li('Button', S32)),
        ('popup-button-icon', 'Popup button: icon', '10', li('Icon', S32)),
        ('popup-window-size-and-position', 'Popup window: size and position', '11',
         li('Popup Window', S32) + '\n' + img('06_popup_window.png', 'The Popup Window section.')),
        ('popup-window-style-and-animation', 'Popup window: style and animation', '12', li('Popup Window', S32)),
        ('close-button', 'Popup window: close button', '13', li('Close Button', S32)),
        ('preview-on-phone-and-tablet', 'Preview on phone and tablet', '14',
         cut('<p>Designs everything the shopper sees', '<img', S32) + '\n'
         + img('07_popup_preview.png', 'Open popup: the chart in the popup, exactly as the shop will show it.')),
    ]),
    ('designer', 'Sizechart Designer', None, cut('<p>The designer builds the chart itself.', '<h4 class="subsub">Components</h4>', S33)
     + '\n<h2>Components</h2>\n' + cut('<p>Click <b>Click to add component</b>', '<h4 class="subsub">Editing a table</h4>', S33), [
        ('rows-and-columns', 'Designer: rows and columns', '15',
         cut('<p>The designer builds the chart itself.', '<table', S33) + '\n'
         + cut('<p>Point at a row or a column', '<h4', S33)),
        ('table-sizes-and-measurements', 'Table: sizes and measurements', '16',
         table(row('Table', COMPONENTS), head=('Component', 'Use it for')) + '\n' + img('10_table_editor.png') + '\n'
         + li('Basic', EDIT_TABLE)),
        ('table-units', 'Table: units', '17',
         li('Units', EDIT_TABLE) + '\n' + img('11_table_units.png', 'The Units tab: CM is the base unit, IN converts with 0.3937.')),
        ('table-style', 'Table: style', '18', li('Table', EDIT_TABLE) + '\n' + STYLE_TABS),
        ('text-editor', 'Text editor', '19', table(row('Text Editor', COMPONENTS), head=('Component', 'Use it for'))),
        ('image', 'Image', '20', table(row('Image', COMPONENTS), head=('Component', 'Use it for'))),
        ('video', 'Video', '21', table(row('Video', COMPONENTS), head=('Component', 'Use it for'))),
        ('tabs', 'Tabs', '22', table(row('Tab', COMPONENTS), head=('Component', 'Use it for'))),
        ('iframe', 'Iframe', '23', table(row('Iframe', COMPONENTS), head=('Component', 'Use it for'))),
        ('themes', 'Themes', '24', re.split(r'</h4>', cut('<h4 class="subsub">Themes</h4>', None, S33), maxsplit=1)[1].strip()),
        ('export-and-import', 'Export and import a design', '25',
         table(row('Export / Import', TOOLBAR), head=('Toolbar button', 'What it does'))),
        ('languages', 'Languages', '26',
         '<p>The language selector at the top of the edit screen switches every text field to another shop language, '
         'so each chart can be written in all your languages.</p>\n'
         + cut('<p class="note">The chart shows in the shopper', '<h2 class="section">6.')),
    ]),
    ('display-rules', 'Display rules', None, cut('<p>Decides which products show the chart.', '<ul class="legend">', S34), [
        ('categories', 'Display rule: categories', '27', li('Categories', S34)),
        ('brands-and-suppliers', 'Display rule: brands and suppliers', '28', li('Brands', S34)),
        ('features', 'Display rule: features', '29', li('Features', S34)),
        ('any-or-all', 'Display rule: Any or All', '30', cut('<p>The <b>Apply Constrain</b> sub-tab', '<p><b>Which chart', S34)),
    ]),
    ('ai-assistant', 'AI assistant', None, after('<h2 class="section">4.', '<h3 class="sub">4.1'), [
        ('ai-settings', 'AI settings', '31', after('<h3 class="sub">4.1', '<h3 class="sub">4.2')),
        ('create-with-ai', 'Create with AI', '32', after('<h3 class="sub">4.2', '<h3 class="sub">4.3')),
        ('ai-design-assistant', 'AI design assistant', '33', after('<h3 class="sub">4.3', '<h2 class="section">5.')),
    ]),
    ('on-the-storefront', 'Seeing it on the storefront', None, after('<h2 class="section">5.', '<h2 class="section">6.'), None),
    ('uninstall-and-delete', 'Uninstall and delete', '34', after('<h2 class="section">6.'), None),
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
        out.append({'t': round(t), 'text': say})
    return out


def videos():
    yt = json.loads((VIDEO / 'out' / 'youtube.json').read_text(encoding='utf-8'))
    res = {}
    for f in sorted((VIDEO / 'clips').glob('[0-9][0-9]-*.cjs')):
        cid = f.stem
        text = f.read_text(encoding='utf-8')
        title = re.search(r"title: '([^']*)'", text).group(1)
        sub = re.search(r"sub: '([^']*)'", text).group(1)
        dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
                                             str(VIDEO / 'out' / f'{cid}-en.mp4')]).decode().strip())
        if cid not in yt['videos']:
            raise SystemExit('not on YouTube yet: ' + cid)
        res[cid[:2]] = {'id': cid, 'yt': yt['videos'][cid], 'title': title, 'sub': sub,
                        'len': f'{int(dur // 60)}:{int(round(dur % 60)):02d}' if round(dur % 60) < 60 else f'{int(dur // 60) + 1}:00'}
    return yt['playlist'], res


def main():
    playlist, vids = videos()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'assets').mkdir(exist_ok=True)
    pictures = set()

    def page(slug, title, num, html, kids):
        p = {'slug': slug, 'title': title}
        if num:
            v = vids[num]
            st = steps(v['id'])
            p.update({'video': {'yt': v['yt'], 'len': v['len'], 'clip': v['id']},
                      'lead': v['sub'], 'intro': st[0]['text'], 'steps': st[1:]})
        if html:
            html = html.replace('<h3 class="sub">', '<h2>').replace('</h3>', '</h2>')
            html = re.sub(r'<h4 class="subsub">(.*?)</h4>', r'<h2>\1</h2>', html)
            for a, b in SECTION_LINKS:
                html = html.replace(a, b)
            if re.search(r'Section \d', html):
                raise SystemExit(f'{slug}: unlinked section reference')
            pictures.update(re.findall(r'src="assets/([^"]+)"', html))
            (OUT / f'{slug}.html').write_text(html.strip() + '\n', encoding='utf-8')
            p['file'] = f'{slug}.html'
        if kids:
            p['pages'] = [page(*k, None) for k in kids]
        return p

    tree = [page(*t) for t in TREE]
    used = {p['video']['clip'] for t in tree for p in [t] + t.get('pages', []) if p.get('video')}
    if len(used) != len(vids):
        raise SystemExit('videos without a page: ' + ' '.join(sorted({v['id'] for v in vids.values()} - used)))
    for name in pictures:
        shutil.copyfile(MOD / 'docs' / 'assets' / name, OUT / 'assets' / name)
    (OUT / 'pages.json').write_text(json.dumps({'playlist': playlist, 'pages': tree}, ensure_ascii=False, indent=1) + '\n',
                                    encoding='utf-8')
    n = sum(1 + len(p.get('pages', [])) for p in tree)
    print(f'{n} pages, {len(used)} videos, {len(pictures)} pictures -> {OUT}')


if __name__ == '__main__':
    main()
