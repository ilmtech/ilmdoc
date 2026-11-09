#!/usr/bin/env python3
"""Build doc.ilmtech.in: a plain static site (no Joomla, no PHP, no database).

    python3 tools/docsite/build.py OUT_DIR
    rsync -rlc OUT_DIR/ <server>:domains/ilmtech.in/public_html/doc/

Sources:
- Min/Max (PrestaShop): src/minmax-ps/pages.json + one <slug>.html per page. One page per
  YouTube video guide, grouped (Configuration > Minimum Quantity, ...). Edit these files by hand.
- Size Chart (PrestaShop): src/sizechart-ps/pages.json + <slug>.html, one page per YouTube video guide
  (made from the module readme by import_sizechart_pages.py on 2026-11-04; edit these files by hand).
- Size Chart and Min/Max (WooCommerce): src/sizechart-woo, src/minmax-woo = pages.json + <slug>.html, one page per YouTube video
  (made by import_woo_guides.py on 2026-11-06; edit these files by hand).
- Size Chart Pro (WooCommerce): src/sizechart-woo-pro = pages.json + <slug>.html, Pro features only. A video may
  play one part of a clip: "start", "end" (seconds). "note" under a video overrides the guide's video_note.
- Home page: src/home.html. Look: assets/ (css, js, images), copied to /assets/.
- Shopify (Size Chart app): src/sizechart-shopify/pages.json + <slug>.html, taken from the old Joomla
  pages on 2026-10-25 (URLs kept under /size-chart-app/); its pictures stay in frozen/images/shopify.

Pages without a video show their first picture at the top instead.
Links between pages are written {{link:<guide>}}, {{link:<guide>:<chapter number>}} or
{{page:<guide>:<slug>}}; old URLs are 301-redirected in the generated .htaccess.
"""
import hashlib
import datetime
import html
import json
import re
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECTS = HERE.parents[3]  # /home/asha/projects
PS = PROJECTS / 'prestashop' / 'modules'
SITE = 'https://doc.ilmtech.in'
MODIFIED = '@@MODIFIED@@'  # replaced after the build: the date the article text last changed (lastmod.json)
VERSION = '2.11.1'  # css/js cache buster
# the store's AI chat on every docs page (module ilmaichat, "Show the chat on other sites"); '' = off.
# ILM_CHAT_EMBED overrides it for a local test.
CHAT_EMBED = os.environ.get('ILM_CHAT_EMBED', 'https://ilmtech.in/module/ilmaichat/embed')

GUIDES = [
    {
        'key': 'sizechart-ps', 'platform': 'prestashop', 'alias': 'ilm-size-chart',
        'title': 'ILM Size Chart for PrestaShop',
        'menu_title': 'ILM Size Chart',
        'note': 'Size charts, Find my size and the AI designer',
        'pages': HERE / 'src' / 'sizechart-ps',
        'lead': 'Build size charts with tables, tabs, pictures and videos, show them in a popup or on the product page, '
                'let shoppers find their size, and design charts with AI.',
        'facts': [('fa-solid fa-tag', 'Version 5.1.0'), ('fa-solid fa-cart-shopping', 'PrestaShop 1.7.0 to 9.x'),
                  ('fa-brands fa-php', 'PHP 7.4 or newer'), ('fa-solid fa-store', 'Multistore')],
        'actions': [('Buy on ilmtech.in', 'https://ilmtech.in/2-ilm-size-chart.html', ''),
                    ('Live demo', 'https://demo.ilmtech.in/ps_ondru/?module=ilmsizechart', 'ghost'),
                    ('Back office demo', 'https://demo.ilmtech.in/ps_ondru/ilmdemo/login?module=ilmsizechart', 'ghost'),
                    ('Video guides', 'https://www.youtube.com/playlist?list=PLD8_srUnWV3w', 'ghost')],
    },
    {
        'key': 'minmax-ps', 'platform': 'prestashop', 'alias': 'minimum-maximum-multiple-order-quantity-amount',
        'title': 'ILM Minimum, Maximum and Multiple Order Quantity / Amount',
        'menu_title': 'ILM Min/Max/Multiple Order Qty/Amt',
        'note': 'Minimum, maximum and multiple quantities or amounts',
        'pages': HERE / 'src' / 'minmax-ps',
        'lead': 'Set minimum, maximum and multiple quantities or amounts per product, combination, category, brand, '
                'supplier, customer group or customer, limit purchases over time, and stop orders that break a rule.',
        'facts': [('fa-solid fa-tag', 'Version 5.3.0'), ('fa-solid fa-cart-shopping', 'PrestaShop 1.7.0 to 9.x'),
                  ('fa-brands fa-php', 'PHP 7.1 or newer'), ('fa-solid fa-store', 'Multistore')],
        'actions': [('Buy on ilmtech.in', 'https://ilmtech.in/1-ilm-min-max-multiple-order-qty-amt.html', ''),
                    ('Live demo', 'https://demo.ilmtech.in/ps_ondru/?module=ilmminmaxorderqty', 'ghost'),
                    ('Back office demo', 'https://demo.ilmtech.in/ps_ondru/ilmdemo/login?module=ilmminmaxorderqty', 'ghost'),
                    ('Video guides', 'https://www.youtube.com/playlist?list=PLPYTROnNCGQA', 'ghost')],
        'new': '<div class="note"><b>New in version 5.3</b><ul class="legend"><li><b>Licence with your Order ID</b> '
               '&mdash; activate the licence in the bar above the tabs to get updates and support, move it to a new '
               'domain or remove it from a shop (see <a href="{{page:minmax-ps:install-and-activate}}">Install and activate</a>).'
               '</li></ul></div>',
    },
    {
        'key': 'aichat-ps', 'platform': 'prestashop', 'alias': 'ilm-ai-chat',
        'title': 'ILM AI Chat Assistant for PrestaShop',
        'menu_title': 'ILM AI Chat Assistant',
        'note': 'An AI assistant that answers from your shop',
        'src': HERE / 'src' / 'aichat-ps',
        'lead': 'An AI chat for your shop: it answers shoppers from your products and pages, suggests questions for each page, '
                'shows product cards and hands over to your team. ILM Built-in AI or your own AI key.',
        'facts': [('fa-solid fa-tag', 'Version 1.5.0'), ('fa-solid fa-cart-shopping', 'PrestaShop 1.7.0 to 9.x'),
                  ('fa-brands fa-php', 'PHP 7.1 or newer'), ('fa-solid fa-robot', 'Built-in AI or your own key')],
        'actions': [('Buy on ilmtech.in', 'https://ilmtech.in/14-ilm-ai-chat-assistant.html', ''),
                    ('Live demo', 'https://demo.ilmtech.in/ps_ondru/?module=ilmaichat', 'ghost'),
                    ('Back office demo', 'https://demo.ilmtech.in/ps_ondru/ilmdemo/login?module=ilmaichat', 'ghost')],
    },
    {
        'key': 'whatsapp-ps', 'platform': 'prestashop', 'alias': 'ilm-chat-order-for-whatsapp',
        'title': 'ILM Chat & Order for WhatsApp for PrestaShop',
        'menu_title': 'ILM Chat & Order for WhatsApp',
        'note': 'Free: chat button and Order on WhatsApp',
        'src': HERE / 'src' / 'whatsapp-ps',
        'lead': 'A WhatsApp chat button with several agents and business hours, plus Order on WhatsApp buttons on product pages and in the cart. Free, no licence key.',
        'facts': [('fa-solid fa-tag', 'Version 1.0.0'), ('fa-solid fa-cart-shopping', 'PrestaShop 1.7.0 to 9.x'),
                  ('fa-brands fa-php', 'PHP 7.1 or newer'), ('fa-solid fa-unlock', 'Free')],
        'actions': [('Free download', 'https://ilmtech.in/19-ilm-chat-order-for-whatsapp-prestashop.html', ''),
                    ('Live demo', 'https://demo.ilmtech.in/ps_ondru/?module=ilmwhatsapp', 'ghost'),
                    ('Back office demo', 'https://demo.ilmtech.in/ps_ondru/ilmdemo/login?module=ilmwhatsapp', 'ghost')],
    },
    {
        'key': 'captcha-ps', 'platform': 'prestashop', 'alias': 'all-in-one-captcha',
        'title': 'ILM All In One Captcha - Anti-Spam for PrestaShop',
        'menu_title': 'All In One Captcha',
        'note': 'Captcha, spam filters and fake account protection',
        'src': HERE / 'src' / 'captcha-ps',
        'lead': 'Stop spam and fake accounts on every PrestaShop form: a captcha checked on your server (built-in, Turnstile, reCAPTCHA, hCaptcha), hidden checks, e-mail and text filters, IP and country rules, rate limits and e-mail confirmation of new accounts.',
        'facts': [('fa-solid fa-tag', 'Version 2.0.0'), ('fa-solid fa-cart-shopping', 'PrestaShop 1.7.1 to 9.x'),
                  ('fa-brands fa-php', 'PHP 7.1 to 8.5'), ('fa-solid fa-shield-halved', '8 forms + any other form')],
        'actions': [('Live demo', 'https://demo.ilmtech.in/ps_ondru/?module=ilmcaptcha', ''),
                    ('Back office demo', 'https://demo.ilmtech.in/ps_ondru/ilmdemo/login?module=ilmcaptcha', 'ghost')],
    },
    {
        'key': 'sizechart-woo', 'platform': 'wordpress', 'alias': 'ilm-size-chart-for-woocommerce',
        'title': 'ILM Size Chart & Size Guide for WooCommerce',
        'menu_title': 'ILM Size Chart & Size Guide for WooCommerce',
        'note': 'Free plugin: video guides',
        'video_note': 'Filmed on a shop with the Pro add-on installed, so you may also see AI buttons and a Find my size button. The free plugin does not have these.',
        'pages': HERE / 'src' / 'sizechart-woo',  # made by import_woo_guides.py, edit by hand
        'lead': 'A size chart plugin for WooCommerce: build charts with a drag-and-drop builder, show them in a popup '
                'or on the product page, and choose where they appear with every display rule. Unlimited charts, 8 themes, no licence key. '
                'Pro adds an AI builder, Find my size and 5 more themes.',
        'facts': [('fa-solid fa-tag', 'Version 2.0.3'), ('fa-brands fa-wordpress', 'WordPress 6.2 to 7.x'),
                  ('fa-solid fa-bag-shopping', 'WooCommerce 7.0 to 11.x'), ('fa-brands fa-php', 'PHP 7.4 to 8.5'),
                  ('fa-solid fa-unlock', 'Free, GPLv2 or later')],
        'actions': [('Get it on WordPress.org', 'https://wordpress.org/plugins/ilm-size-chart-for-woocommerce/', ''),
                    ('Download zip', 'https://ilmtech.in/11-ilm-size-chart-for-woocommerce-free.html', 'ghost'),
                    ('Live demo', 'https://demo.ilmtech.in/wp/pro/', 'ghost'),
                    ('Video guides', 'https://www.youtube.com/playlist?list=PLC17iYmpEQnM', 'ghost')],
    },
    {
        'key': 'sizechart-woo-pro', 'platform': 'wordpress', 'alias': 'ilm-size-chart-pro',
        'title': 'ILM Size Chart Pro for WooCommerce',
        'menu_title': 'ILM Size Chart Pro',
        'note': 'Add-on: AI builder, Find my size, 13 themes',
        'pages': HERE / 'src' / 'sizechart-woo-pro',
        'lead': 'The Pro add-on for ILM Size Chart & Size Guide for WooCommerce: an AI chart builder, "Find my size" for shoppers, '
                'and five more themes with ready-made blocks (13 in all).',
        'facts': [('fa-solid fa-tag', 'Version 2.0.2'), ('fa-brands fa-wordpress', 'WordPress 6.2 to 7.x'),
                  ('fa-solid fa-bag-shopping', 'WooCommerce 7.0 to 11.x'), ('fa-solid fa-puzzle-piece', 'Needs the free plugin')],
        'actions': [('Buy on ilmtech.in', 'https://ilmtech.in/8-ilm-size-chart-pro-for-woocommerce.html', ''),
                    ('Live demo', 'https://demo.ilmtech.in/wp/pro/', 'ghost'),
                    ('Video guides', 'https://www.youtube.com/playlist?list=PLC17iYmpEQnM', 'ghost')],
    },
    {
        'key': 'minmax-woo', 'platform': 'wordpress', 'alias': 'ilm-min-max-order-qty-amount',
        'title': 'ILM Min/Max/Multiple Order Qty/Amt for WooCommerce',
        'menu_title': 'ILM Min/Max/Multiple Order Qty/Amt',
        'note': 'Minimum, maximum and multiple quantities or amounts',
        'pages': HERE / 'src' / 'minmax-woo',  # made by import_woo_guides.py, edit by hand
        'lead': 'Set minimum, maximum and multiple quantities per product and variation. The Pro add-on adds amounts and rules per category, '
                'brand, tag, user role, customer or the whole shop, limits over time, and an AI assistant.',
        'facts': [('fa-solid fa-tag', 'Version 1.0.0'), ('fa-brands fa-wordpress', 'WordPress 6.2 to 7.x'),
                  ('fa-solid fa-bag-shopping', 'WooCommerce 8.2 to 11.x'), ('fa-brands fa-php', 'PHP 7.4 or newer'),
                  ('fa-solid fa-shield-halved', 'Classic and block checkout')],
        'actions': [('Live demo', 'https://demo.ilmtech.in/wp/pro/', ''),
                    ('Video guides', 'https://www.youtube.com/playlist?list=PLYzWgeOGYn94', 'ghost')],
        'hero': False,  # step pages: every picture belongs to its step
    },
    {
        'key': 'whatsapp-woo', 'platform': 'wordpress', 'alias': 'ilm-chat-order-for-whatsapp',
        'title': 'ILM Chat & Order for WhatsApp for WooCommerce',
        'menu_title': 'ILM Chat & Order for WhatsApp',
        'note': 'Free: chat button and Order on WhatsApp',
        'src': HERE / 'src' / 'whatsapp-woo',
        'lead': 'A WhatsApp chat button with several agents and business hours, plus Order on WhatsApp buttons on product pages and in the cart. Free, no licence key.',
        'facts': [('fa-solid fa-tag', 'Version 1.0.0'), ('fa-brands fa-wordpress', 'WordPress 6.2 to 7.x'),
                  ('fa-solid fa-bag-shopping', 'WooCommerce 7.0 to 11.x'), ('fa-brands fa-php', 'PHP 7.4 or newer'), ('fa-solid fa-unlock', 'Free')],
        'actions': [('Free download', 'https://ilmtech.in/20-ilm-chat-order-for-whatsapp-woocommerce.html', ''),
                    ('Live demo', 'https://demo.ilmtech.in/wp/pro/', 'ghost')],
    },
    {
        'key': 'sizechart-shopify', 'platform': 'shopify', 'alias': 'size-chart-app', 'base': '/size-chart-app/',
        'title': 'ILM Size Chart app for Shopify',
        'menu_title': 'ILM Size Chart app',
        'note': 'Size charts with tables, images and videos',
        'pages': HERE / 'src' / 'sizechart-shopify',
        'lead': 'Install the app, create size charts with tables, images and videos, and show them on your Shopify products.',
        'facts': [('fa-brands fa-shopify', 'Shopify app'), ('fa-solid fa-table', 'Tables, images and videos'),
                  ('fa-solid fa-display', 'Popup or inline display')],
        'actions': [],
        'hero': False,  # step guides: the first picture belongs to step 1
    },
    {
        'key': 'minmax-shopify', 'platform': 'shopify', 'alias': 'ilm-min-max-order-qty-amount',
        'title': 'ILM Min Max Order Qty/Amount app for Shopify',
        'menu_title': 'ILM Min Max Order Qty/Amount',
        'note': 'Minimum, maximum and multiple quantities or amounts',
        'pages': HERE / 'src' / 'minmax-shopify',  # written by shopify/ilm-apps/tools/tutorials/make_docs.py
        'lead': 'Set minimum, maximum and multiple quantities or amounts per product, variant, collection, vendor, product '
                'type, customer tag or the whole store, limit purchases between dates, and stop carts that break a rule at checkout.',
        'facts': [('fa-brands fa-shopify', 'Shopify app'), ('fa-solid fa-layer-group', 'Free, Basic and Pro plans'),
                  ('fa-solid fa-shield-halved', 'Checked again at checkout'), ('fa-solid fa-language', 'Every store language')],
        'actions': [('Live demo', 'https://apps.ilmtech.in/demo/ilm-minmax', 'ghost'),
                    ('Video guides', 'https://www.youtube.com/playlist?list=PLQCercGzuy5M', 'ghost')],
        'hero': False,  # step pages: every picture belongs to its step
    },
    {
        'key': 'whatsapp-shopify', 'platform': 'shopify', 'alias': 'ilm-chat-order-for-whatsapp',
        'title': 'ILM Chat & Order for WhatsApp app for Shopify',
        'menu_title': 'ILM Chat & Order for WhatsApp',
        'note': 'Free: chat button and Order on WhatsApp',
        'src': HERE / 'src' / 'whatsapp-shopify',
        'lead': 'A WhatsApp chat button with several agents and business hours, plus Order on WhatsApp buttons on product pages, the cart and the cart drawer. No Meta account needed.',
        'facts': [('fa-brands fa-shopify', 'Shopify app'), ('fa-solid fa-unlock', 'Free'),
                  ('fa-solid fa-language', 'Every store language')],
        'actions': [],
    },
]

PLATFORMS = {'prestashop': ('PrestaShop', 'fa-solid fa-cart-shopping'), 'wordpress': ('WordPress', 'fa-brands fa-wordpress'),
             'shopify': ('Shopify', 'fa-brands fa-shopify')}
SHOPIFY = '/size-chart-app/'

# Old URLs (Joomla and the first static copy) -> page key ("guide:slug path") or a plain path
OLD_MINMAX = {
    'installation': 'getting-started/install-and-activate',
    'configure-the-six-tabs': 'getting-started/the-six-tabs',
    'quantity-amount-rule': 'rules',
    'duration-rule': 'duration-rules',
    'rule-templates': 'tools/rule-templates',
    'export-import': 'tools/export-and-import',
    'blocked-attempts': 'tools/blocked-attempts',
    'seeing-it-in-action-on-the-storefront': 'messages-and-storefront/on-the-storefront',
    'uninstallation': 'uninstall-and-delete',
}
MM = '/prestashop/minimum-maximum-multiple-order-quantity-amount'
OLD_URLS = {
    '/prestahsop/ilm-size-chart': '/prestashop/ilm-size-chart/',
    '/size-chart-app/ilm-search': SHOPIFY,
    '/prestahsop/ilm-product-tab': '/',
    '/prestahsop/minimum-maximum-multiple-order-quantity-amount': MM + '/',
    '/minimum-maximum-multiple-order-quantity-amount': MM + '/',
    '/minimum-maximum-multiple-order-quantity-amount/introduction': MM + '/getting-started/install-and-activate/',
    '/minimum-maximum-multiple-order-quantity-amount/introduction/getting-started': MM + '/getting-started/install-and-activate/',
    '/minimum-maximum-multiple-order-quantity-amount/introduction/installation': MM + '/getting-started/install-and-activate/',
    '/minimum-maximum-multiple-order-quantity-amount/configuration': MM + '/configuration/',
    '/minimum-maximum-multiple-order-quantity-amount/configuration/backoffice-configuration': MM + '/configuration/',
    '/minimum-maximum-multiple-order-quantity-amount/configuration/enable-disable-section-rules': MM + '/configuration/rule-priority-order/',
    '/minimum-maximum-multiple-order-quantity-amount/configuration/frontoffice-configuration': MM + '/messages-and-storefront/',
    '/minimum-maximum-multiple-order-quantity-amount/duration': MM + '/duration-rules/',
    '/minimum-maximum-multiple-order-quantity-amount/duration/what-is-duration': MM + '/duration-rules/',
    '/minimum-maximum-multiple-order-quantity-amount/duration/each-order': MM + '/duration-rules/per-order-no-time-limit/',
    '/minimum-maximum-multiple-order-quantity-amount/duration/one-time': MM + '/duration-rules/lifetime-total/',
    '/minimum-maximum-multiple-order-quantity-amount/duration/specific-duration': MM + '/duration-rules/custom-start-and-length/',
    '/minimum-maximum-multiple-order-quantity-amount/duration/order-status': MM + '/duration-rules/which-order-statuses-count/',
    '/minimum-maximum-multiple-order-quantity-amount/rule-configuration': MM + '/rules/',
    '/minimum-maximum-multiple-order-quantity-amount/rule-configuration/quantity-amount-rule': MM + '/rules/',
    '/minimum-maximum-multiple-order-quantity-amount/rule-configuration/product-set-quantity-amount-rule': MM + '/rules/product-rules-and-combinations/',
    '/minimum-maximum-multiple-order-quantity-amount/rule-configuration/category-set-quantity-amount-rule': MM + '/rules/category-rule/',
    '/minimum-maximum-multiple-order-quantity-amount/rule-configuration/supplier-set-quantity-amount-rule': MM + '/rules/supplier-rule/',
    '/minimum-maximum-multiple-order-quantity-amount/rule-configuration/brand-set-quantity-amount-rule': MM + '/rules/brand-rule/',
    '/minimum-maximum-multiple-order-quantity-amount/rule-configuration/customer-group-set-quantity-amount-rule': MM + '/rules/customer-group-rule/',
}
OLD_URLS.update({f'{MM}/{a}': f'{MM}/{b}/' for a, b in OLD_MINMAX.items()})
WSC = '/wordpress/ilm-size-chart-for-woocommerce'
OLD_URLS.update({f'{WSC}/{a}': f'{WSC}/{b}/' for a, b in {  # chapters before the video pages (2026-11-06)
    'installation': 'getting-started/install-and-activate', 'the-size-chart-list': 'getting-started/the-size-chart-list',
    'creating-a-size-chart': 'getting-started/your-first-size-chart', 'data-and-uninstall': 'uninstall-and-delete'}.items()})
WSCP = '/wordpress/ilm-size-chart-pro'
OLD_URLS.update({f'{WSC}/{a}': f'{WSCP}/{b}/' for a, b in {  # Pro videos moved to the Pro guide (2026-11-06)
    'general/find-my-size': 'find-my-size', 'ai-assistant/ai-settings': 'ai-settings', 'ai-assistant/create-with-ai': 'create-with-ai',
    'ai-assistant/ai-design-assistant': 'ai-design-assistant', 'ai-assistant': 'create-with-ai'}.items()})
OLD_URLS[f'{WSCP}/ai-chart-builder'] = f'{WSCP}/create-with-ai/'
# Size Chart (PrestaShop) readme chapters -> the video pages (2026-11-04)
SC = '/prestashop/ilm-size-chart'
CAP = '/prestashop/all-in-one-captcha'
OLD_URLS.update({f'{CAP}/{a}': f'{CAP}/{b}/' for a, b in {  # 1.x guide chapters (2026-11-09, version 2.0.0)
    'captcha-types': 'captcha', 'protect': 'access-limits'}.items()})
OLD_URLS.update({f'{SC}/{a}': f'{SC}/{b}/' for a, b in {
    'installation-and-licence': 'getting-started/install-and-activate',
    'the-size-chart-list': 'getting-started/the-size-chart-list',
    'creating-a-size-chart-the-four-tabs': 'getting-started/your-first-size-chart',
    'seeing-it-in-action-on-the-storefront': 'on-the-storefront',
    'uninstallation': 'uninstall-and-delete',
}.items()})

HTACCESS = """# Generated by tools/docsite/build.py - static docs, no PHP.
Options -Indexes -ExecCGI
DirectoryIndex index.html
ErrorDocument 404 /404.html

<IfModule mod_php.c>
    php_flag engine off
</IfModule>
RemoveHandler .php .php5 .php7 .php8 .phtml .phar .pht .phtm .shtml .txt
RemoveType .php .php5 .php7 .php8 .phtml .phar .pht .phtm .shtml .txt
<FilesMatch "\\.(php\\d?|phtml?|phar|pht|shtml|cgi|pl|py|sh|htaccess)$">
    Require all denied
</FilesMatch>

<IfModule mod_headers.c>
    Header always set Strict-Transport-Security "max-age=2592000"
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
    <FilesMatch "\\.(css|js|png|jpe?g|gif|svg|webp|ico|woff2?)$">
        Header set Cache-Control "public, max-age=2592000"
    </FilesMatch>
</IfModule>

# The static copy lived in /html until 2026-10-25
RedirectMatch 301 ^/html/?(.*)$ /$1
# Joomla URLs
RedirectMatch 301 ^/index\\.php/?(.*)$ /$1

# Old URLs
{redirects}
"""


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', html.unescape(text).lower()).strip('-')


def plain(fragment):
    return html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', fragment))).strip()


def esc(text):
    return html.escape(str(text), quote=True)


def summary(body, limit=150):
    """First sentence(s) of the first real paragraph, for the cards and the meta description."""
    for p in re.findall(r'<p(?: class="(?!caption)[^"]*")?>(.*?)</p>', body, re.S):
        text = plain(p)
        if len(text) > 30 and not text.lower().startswith('step'):
            return text if len(text) <= limit else text[:limit].rsplit(' ', 1)[0] + '…'
    return ''


def link_sections(body, key):
    """'Section 3.1' -> a link to chapter 3, anchor s3-1; numbered h3 get that anchor as id."""
    def ref(m):
        n, sub = m.group(1), m.group(2)
        anchor = f'#s{n}-{sub}' if sub else ''
        return f'<a href="{{{{link:{key}:{n}}}}}{anchor}">{m.group(0)}</a>'
    body = re.sub(r'(?<![\w>])Section (\d+)(?:\.(\d+))?', ref, body)
    return re.sub(r'<h3 class="sub">(\d+)\.(\d+) ', lambda m: f'<h3 class="sub" id="s{m.group(1)}-{m.group(2)}">{m.group(1)}.{m.group(2)} ', body)


def extra_section(path, g, images):
    """A section added to a readme chapter; its pictures are written src="extra:<folder in src>/<file>"."""
    def img(m):
        folder, name = m.group(1), m.group(2)
        images[f'docs/{g["key"]}/{name}'] = str(HERE / 'src' / folder / name)
        return f'src="/images/docs/{g["key"]}/{name}" loading="lazy"'
    return re.sub(r'src="extra:([^/"]+)/([^"]+)"', img, path.read_text(encoding='utf-8'))


def assets_to_images(text, folder, key, images):
    """src="assets/x.png" -> /images/docs/<key>/x.png (the picture is copied there)."""
    def img(m):
        name = m.group(1)
        images[f'docs/{key}/{name}'] = str(folder / 'assets' / name)
        return f'src="/images/docs/{key}/{name}"'
    text = re.sub(r'src="assets/([^"]+)"', img, text)
    text = re.sub(r'<img (?![^>]*\balt=)', '<img alt="" ', text)
    return re.sub(r'<img (?![^>]*\bloading=)', '<img loading="lazy" ', text)


def from_readme(g, images):
    src = g['readme'].read_text(encoding='utf-8')
    body = re.search(r'<body[^>]*>(.*)</body>', src, re.S).group(1)
    body = re.sub(r'<h1 class="doctitle">.*?</h1>', '', body, flags=re.S)
    body = re.sub(r'<div class="toc">.*?</div>\s*', '', body, flags=re.S)
    body = re.sub(r'<footer class="pagefoot">.*?</footer>', '', body, flags=re.S)
    body = re.sub(r'<div class="pagebreak"></div>', '', body)
    body = re.sub(r'\s*class="pagebreak"', '', body)
    body = assets_to_images(body, g['readme'].parent, g['key'], images)
    for a, b in g.get('replace', []):
        if a not in body:
            sys.exit(f'{g["key"]}: text to replace not found in the readme: {a[:60]}')
        body = body.replace(a, b)
    parts = re.split(r'<h2 class="section">(.*?)</h2>', body)
    intro, chapters = parts[0], []
    for i in range(1, len(parts), 2):
        title = re.sub(r'^\d+\.\s*', '', html.unescape(plain(parts[i]))).replace(' — ', ': ')
        number = len(chapters) + 1
        text = parts[i + 1].strip()
        extra = g.get('append', {}).get(number)
        if extra:
            text += '\n' + extra_section(HERE / 'src' / extra, g, images)
        chapters.append({'title': title, 'slug': slug(title), 'html': link_sections(text, g['key'])})
    return g.get('new', '') + link_sections(intro.strip(), g['key']), chapters


def from_src(g, images):
    chapters = []
    for f in sorted(g['src'].glob('[0-9][0-9]-*.html')):
        text = f.read_text(encoding='utf-8').strip()
        m = re.match(r'<h1>(.*?)</h1>\s*', text, re.S)
        text = assets_to_images(text[m.end():], g['src'], g['key'], images)
        chapters.append({'title': plain(m.group(1)), 'slug': f.stem[3:], 'html': link_sections(text, g['key'])})
    intro_file = g['src'] / 'intro.html'
    intro = intro_file.read_text(encoding='utf-8') if intro_file.exists() else ''
    return link_sections(intro, g['key']), chapters


# ---------------------------------------------------------------- page tree

class Page(dict):
    """A page compares by identity: pages link to their parent and kids, so == on plain dicts can recurse forever."""
    __eq__ = object.__eq__
    __ne__ = object.__ne__
    __hash__ = object.__hash__


def page(**kw):
    p = Page({'kids': [], 'parent': None, 'html': '', 'lead': '', 'video': None, 'steps': [], 'intro': ''})
    p.update(kw)
    for k in p['kids']:
        k['parent'] = p
    return p


def load_guide(g, images):
    base = g.get('base') or f'/{g["platform"]}/{g["alias"]}/'
    if 'pages' in g:
        data = json.loads((g['pages'] / 'pages.json').read_text(encoding='utf-8'))

        def make(d, url):
            u = f'{url}{d["slug"]}/'
            text = (g['pages'] / d['file']).read_text(encoding='utf-8') if d.get('file') else ''
            return page(url=u, slug=d['slug'], title=d['title'], kind='group' if d.get('pages') else 'page',
                        html=assets_to_images(text, g['pages'], g['key'], images), lead=d.get('lead', ''),
                        video=d.get('video'), steps=d.get('steps', []), intro=d.get('intro', ''),
                        kids=[make(k, u) for k in d.get('pages', [])])
        kids = [make(d, base) for d in data['pages']]
        intro, playlist = g.get('new', ''), data.get('playlist')
    else:
        intro, chapters = from_readme(g, images) if 'readme' in g else from_src(g, images)
        kids = [page(url=f'{base}{c["slug"]}/', slug=c['slug'], title=c['title'], kind='page', html=c['html'], number=i + 1)
                for i, c in enumerate(chapters)]
        playlist = None
    images[f'docs/logos/{g["key"]}.jpg'] = str(HERE / 'logos' / f'{g["key"]}.jpg')
    return page(url=base, slug='', title=g['title'], menu=g['menu_title'], kind='overview', guide=g, intro=intro,
                lead=g['lead'], kids=kids, playlist=playlist)


def walk(p):
    yield p
    for k in p['kids']:
        yield from walk(k)


def guide_of(p):
    while p['parent']:
        p = p['parent']
    return p


HERO = re.compile(r'<img\b[^>]*>(?:\s*<p class="caption">.*?</p>)?', re.S)


def first_image(text):
    m = re.search(r'<img\b[^>]*\bsrc="([^"]+)"', text)
    return m.group(1) if m else ''


def thumb(p):
    if p['video']:
        return f'https://i.ytimg.com/vi/{p["video"]["yt"]}/mqdefault.jpg'
    return first_image(p['html']) or (first_image(''.join(k['html'] for k in p['kids'])) if p['kids'] else '')


def describe(p):
    return p['lead'] or summary(p['html']) or (p['parent'] and p['parent']['lead']) or ''


def mmss(t):
    return f'{int(t) // 60}:{int(t) % 60:02d}'


# ---------------------------------------------------------------- html pieces

def tiles(pages):
    out = []
    for p in pages:
        img, v = thumb(p), p['video']
        media = (f'<img src="{esc(img)}" alt="" loading="lazy">' if img else '<i class="fa-regular fa-file-lines" aria-hidden="true"></i>')
        if v:
            media += (f'<span class="ilmd-tile__play" aria-hidden="true"><i class="fa-solid fa-play"></i></span>'
                      f'<span class="ilmd-tile__len">{esc(v["len"])}</span>')
        elif p['kids']:
            media += f'<span class="ilmd-tile__len">{len(p["kids"])} pages</span>'
        out.append(f'<a class="ilmd-tile" href="{p["url"]}"><span class="ilmd-tile__img">{media}</span>'
                   f'<span class="ilmd-tile__body"><strong>{esc(p["title"])}</strong><span>{esc(describe(p))}</span></span></a>')
    return '<div class="ilmd-tiles">' + ''.join(out) + '</div>'


def watch(p):
    v = p['video']
    steps = ''.join(f'<li><button type="button" data-t="{s["t"]}"><span class="ilmd-steps__t">{mmss(s["t"])}</span>'
                    f'<span>{esc(s["text"])}</span></button></li>'
                    for s in ([{'t': v.get('start', 0), 'text': p['intro']}] if p['intro'] else []) + p['steps'])
    g = guide_of(p)
    playlist = f' <a href="{esc(g["playlist"])}" target="_blank" rel="noopener">All videos</a>' if g.get('playlist') else ''
    return (f'<div class="ilmd-watch"><div class="ilmd-player" data-yt="{v["yt"]}" data-start="{v.get("start", 0)}" data-end="{v.get("end", "")}" data-title="{esc(p["title"])}">'
            f'<button type="button" class="ilmd-player__start" aria-label="Play the video: {esc(p["title"])}">'
            f'<img src="https://i.ytimg.com/vi/{v["yt"]}/maxresdefault.jpg" alt="" width="1280" height="720" '
            f'onerror="this.onerror=null;this.src=\'https://i.ytimg.com/vi/{v["yt"]}/hqdefault.jpg\'">'
            f'<span class="ilmd-player__btn" aria-hidden="true"><i class="fa-solid fa-play"></i></span>'
            f'<span class="ilmd-player__len">{esc(v["len"])}</span></button></div>'
            f'<div class="ilmd-steps"><div class="ilmd-steps__head"><strong>In this video</strong>'
            f'<span>Click a step to jump to it</span></div><ol>{steps}</ol>'
            f'<div class="ilmd-steps__foot"><a href="https://www.youtube.com/watch?v={v["yt"]}" target="_blank" rel="noopener">'
            f'<i class="fa-brands fa-youtube" aria-hidden="true"></i> Watch on YouTube</a>{playlist}</div></div></div>')


def overview_body(p):
    g = p['guide']
    facts = ''.join(f'<li><i class="{i}" aria-hidden="true"></i>{esc(t)}</li>' for i, t in g['facts'])
    actions = ''.join(f'<a class="ilmd-btn{" ilmd-btn--ghost" if kind else ""}" href="{esc(u)}" target="_blank" rel="noopener">{esc(t)}</a>'
                      for t, u, kind in g['actions'])
    out = f'<ul class="ilmd-facts">{facts}</ul>\n' + (f'<div class="ilmd-actions">{actions}</div>\n' if actions else '')
    groups = [k for k in p['kids'] if k['kids']]
    if groups:
        loose = []
        for k in p['kids']:
            if k['kids']:
                out += (f'<section class="ilmd-group"><div class="ilmd-group__head"><h2><a href="{k["url"]}">{esc(k["title"])}</a></h2>'
                        f'<a class="ilmd-group__all" href="{k["url"]}">Overview <i class="fa-solid fa-arrow-right" aria-hidden="true"></i></a></div>'
                        f'{tiles(k["kids"])}</section>\n')
            else:
                loose.append(k)
        if loose:
            out += f'<section class="ilmd-group"><div class="ilmd-group__head"><h2>More</h2></div>{tiles(loose)}</section>\n'
    else:
        out += f'<h2>Chapters</h2>\n{tiles(p["kids"])}\n'
    if p['intro'].strip():
        out += f'<h2>What is new</h2>\n{p["intro"]}\n'
    return out


def page_body(p):
    if p['kind'] == 'overview':
        return overview_body(p)
    if p['kind'] == 'group':
        return tiles(p['kids']) + '\n<div class="ilmd-prose">' + p['html'] + '</div>'
    if p['video']:
        out = watch(p)
        note = p['video'].get('note', guide_of(p)['guide'].get('video_note', ''))
        if note:
            out += f'\n<div class="ilmd-prose"><p class="note">{esc(note)}</p></div>'
        if p['html'].strip():
            out += '\n<h2>Details</h2>\n<div class="ilmd-prose">' + p['html'] + '</div>'
        return out
    m = HERO.search(p['html']) if guide_of(p)['guide'].get('hero', True) else None
    if not m:
        return '<div class="ilmd-prose">' + p['html'] + '</div>'
    hero = m.group(0).replace('class="shot shot-narrow"', 'class="shot"')
    rest = p['html'][:m.start()] + p['html'][m.end():]
    return f'<figure class="ilmd-hero-img">{hero}</figure>\n<div class="ilmd-prose">{rest}</div>'


def side(cur):
    g = guide_of(cur)

    def a(p, cls=''):
        icon = ('fa-solid fa-circle-play' if p['video'] else 'fa-regular fa-file-lines')
        act = ' is-active" aria-current="page' if p is cur else ''
        return f'<a class="{cls}{act}" href="{p["url"]}"><i class="{icon}" aria-hidden="true"></i><span>{esc(p["title"])}</span></a>'
    items = ''
    for k in g['kids']:
        if k['kids']:
            opened = cur is k or cur in k['kids']
            act = ' is-active" aria-current="page' if k is cur else ''
            kids = ''.join(f'<li>{a(x)}</li>' for x in k['kids'])
            items += (f'<li class="ilmd-tree__group"><details{" open" if opened else ""}><summary>'
                      f'<a class="ilmd-tree__grp{act}" href="{k["url"]}">{esc(k["title"])}</a>'
                      f'<i class="fa-solid fa-chevron-down" aria-hidden="true"></i></summary><ul>{kids}</ul></details></li>')
        else:
            items += f'<li>{a(k)}</li>'
    return (f'<p class="ilmd-side__platform">{PLATFORMS[g["guide"]["platform"]][0]}</p>'
            f'<a class="ilmd-side__guide{" is-active" if cur is g else ""}" href="{g["url"]}">{esc(g["menu"])}</a>'
            f'<div class="ilmd-gsearch" data-prefix="{g["url"]}"><i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>'
            f'<input type="search" placeholder="Search this guide" aria-label="Search the {esc(g["menu"])} guide" autocomplete="off"></div>'
            f'<ul class="ilmd-tree">{items}</ul>')


def crumbs(p):
    g = guide_of(p)
    parts = ['<a href="/">Docs</a>', f'<span>{PLATFORMS[g["guide"]["platform"]][0]}</span>']
    chain, q = [], p
    while q['parent']:
        chain.insert(0, q['parent'])
        q = q['parent']
    for c in chain:
        parts.append(f'<a href="{c["url"]}">{esc(c.get("menu") or c["title"])}</a>')
    sep = '<i class="fa-solid fa-chevron-right" aria-hidden="true"></i>'
    return '<nav class="ilmd-crumbs" aria-label="Breadcrumb">' + sep.join(parts) + '</nav>'


def pager(p):
    order = list(walk(guide_of(p)))
    i = order.index(p)
    prev = order[i - 1] if i > 0 else None
    nxt = order[i + 1] if i + 1 < len(order) else None
    out = '<nav class="ilmd-pager" aria-label="Previous and next page">'
    out += (f'<a class="ilmd-pager__prev" href="{prev["url"]}"><span>Previous</span><strong><i class="fa-solid fa-arrow-left" aria-hidden="true"></i> '
            f'{esc(prev.get("menu") or prev["title"])}</strong></a>') if prev else '<span></span>'
    if nxt:
        out += (f'<a class="ilmd-pager__next" href="{nxt["url"]}"><span>Next</span><strong>{esc(nxt["title"])} '
                f'<i class="fa-solid fa-arrow-right" aria-hidden="true"></i></strong></a>')
    return out + '</nav>'


def header(guides, active_platform=''):
    items = ''
    for plat, (name, icon) in PLATFORMS.items():
        links = ''.join(f'<a href="{g["url"]}"><strong>{esc(g["menu"])}</strong><span>{esc(g["guide"]["note"])}</span></a>'
                        for g in guides if g['guide']['platform'] == plat)
        items += (f'<div class="ilmd-nav__item has-kids{" is-active" if plat == active_platform else ""}">'
                  f'<button class="ilmd-nav__top" type="button" aria-expanded="false"><i class="{icon}" aria-hidden="true"></i>{name}'
                  f'<i class="fa-solid fa-chevron-down ilmd-nav__caret" aria-hidden="true"></i></button><div class="ilmd-nav__drop">{links}</div></div>')
    return f'''<a class="ilmd-skip" href="#ilmd-main">Skip to content</a>
<header class="ilmd-top">
	<div class="ilmd-top__in">
		<a class="ilmd-logo" href="/" aria-label="ILM Tech documentation home"><img src="/assets/images/logo.png" alt="ILM Tech" width="900" height="135"><span class="ilmd-logo__tag">Docs</span></a>
		<button class="ilmd-burger" type="button" aria-expanded="false" aria-controls="ilmd-nav" aria-label="Menu"><i class="fa-solid fa-bars" aria-hidden="true"></i></button>
		<nav class="ilmd-nav" id="ilmd-nav" aria-label="Main">{items}</nav>
		<div class="ilmd-top__actions">
			<a class="ilmd-btn ilmd-btn--ghost" href="https://ilmtech.in/contact-us">Support</a>
			<a class="ilmd-btn" href="https://ilmtech.in/">ilmtech.in <i class="fa-solid fa-arrow-up-right-from-square" aria-hidden="true"></i></a>
		</div>
	</div>
</header>'''


FOOTER = '''<footer class="ilmd-foot">
	<div class="ilmd-foot__in">
		<div class="ilmd-foot__brand">
			<img src="/assets/images/logo.png" alt="ILM Tech" width="900" height="135" loading="lazy">
			<p>Guides for ILM Tech modules and plugins for PrestaShop, WooCommerce and Shopify.</p>
		</div>
		<div class="ilmd-foot__links">
			<a href="https://ilmtech.in/">Store</a>
			<a href="https://ilmtech.in/content/8-faq">FAQ</a>
			<a href="https://ilmtech.in/content/10-changelog">Changelog</a>
			<a href="https://ilmtech.in/contact-us">Contact</a>
			<a href="https://ilmtech.in/content/6-privacy-policy">Privacy</a>
			<a href="#cookie-settings" data-ilm-consent-open>Cookie settings</a>
		</div>
		<p class="ilmd-foot__copy">&copy; {year} ILM Tech. All rights reserved.</p>
	</div>
</footer>'''

HELP = '''<div class="ilmd-help">
				<div>
					<p class="ilmd-help__title">Need a hand?</p>
					<p class="ilmd-help__sub">Write to us and we reply by e-mail, usually within 2 working days.</p>
				</div>
				<div class="ilmd-help__actions">
					<a class="ilmd-btn ilmd-btn--light" href="mailto:sales@ilmtech.in"><i class="fa-regular fa-envelope" aria-hidden="true"></i> sales@ilmtech.in</a>
					<a class="ilmd-btn ilmd-btn--white" href="https://ilmtech.in/contact-us">Contact us <i class="fa-solid fa-arrow-right" aria-hidden="true"></i></a>
				</div>
			</div>'''


ROBOTS = '''User-agent: *
Content-Signal: search=yes,ai-train=no,use=reference
Allow: /

User-agent: Google-Extended
Allow: /

# AI training and data crawlers stay out; search results are not affected
User-agent: Amazonbot
User-agent: Applebot-Extended
User-agent: Bytespider
User-agent: CCBot
User-agent: ClaudeBot
User-agent: Diffbot
User-agent: GPTBot
User-agent: omgili
User-agent: anthropic-ai
User-agent: Claude-Web
User-agent: cohere-ai
User-agent: MistralAI-Training
User-agent: meta-externalagent
User-agent: GoogleOther
User-agent: Baiduspider
User-agent: PetalBot
User-agent: AwarioSmartBot
User-agent: AwarioRssBot
User-agent: Google-CloudVertexBot
User-agent: QualifiedBot
User-agent: Cotoyogi
User-agent: ICC-Crawler
User-agent: atlassian-bot
User-agent: FishBot
User-agent: BorderxBot
User-agent: NavuBot
User-agent: SemrushBot-SWA
User-agent: WARDBot
User-agent: magpie-crawler
User-agent: KimiBot
User-agent: CitibotSiteCrawler
Disallow: /

Sitemap: {site}/sitemap.xml
'''

# Cookie choice, same file as the store: Google Analytics loads only after Accept
ANALYTICS = f'''
	<script src="/assets/js/ilm-consent.js?v={VERSION}" defer></script>'''


def document(title, description, url, body, body_class, image='', extra_head=''):
    CHAT_SCRIPT = f'\n\t<script src="{esc(CHAT_EMBED)}" defer></script>' if CHAT_EMBED else ''
    image = image or f'{SITE}/assets/images/logo.png'
    return f'''<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<meta name="theme-color" content="#0f172a">
	<title>{esc(title)}</title>
	<meta name="description" content="{esc(description)}">
	<link rel="canonical" href="{SITE}{url}">
	<meta property="og:type" content="article">
	<meta property="og:site_name" content="ILM Tech Docs">
	<meta property="og:title" content="{esc(title)}">
	<meta property="og:description" content="{esc(description)}">
	<meta property="og:url" content="{SITE}{url}">
	<meta property="og:image" content="{esc(image)}">
	<meta name="twitter:card" content="summary_large_image">
	<link rel="icon" href="/favicon.ico">
	<link rel="icon" type="image/png" href="/assets/images/favicon.png">
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
	<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&amp;display=swap" rel="stylesheet">
	<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.6.0/css/all.min.css" rel="stylesheet">
	<link href="/assets/css/ilmdocs.css?v={VERSION}" rel="stylesheet">
	<script src="/assets/js/ilmdocs.js?v={VERSION}" defer></script>{CHAT_SCRIPT}{ANALYTICS}{extra_head}
</head>
<body class="ilmd {body_class}">
{body}
</body>
</html>
'''


def seo_name(g):
    """The guide's short name with its platform: the same page exists for several platforms."""
    label = {'wordpress': 'WooCommerce'}.get(g['guide']['platform'], PLATFORMS[g['guide']['platform']][0])
    return g['menu'] if label in g['menu'] else f'{g["menu"]} for {label}'


def render(p, guides):
    g = guide_of(p)
    title = p.get('menu') or p['title']
    full = f'{title} - {seo_name(g)}' if p is not g else g['title']
    lead = f'<p class="ilmd-lead">{esc(p["lead"])}</p>' if p['lead'] else ''
    h1 = esc(g['title'] if p is g else p['title'])
    main = f'''<div class="ilmd-shell">
		<aside class="ilmd-side" aria-label="Guide">{side(p)}</aside>
		<main id="ilmd-main" class="ilmd-main">
			{crumbs(p) if p is not g else ''}
			<article class="ilmd-article ilmd-article--{p["kind"]}{" ilmd-article--video" if p["video"] else ""}">
				<h1>{h1}</h1>
				{lead}
				{page_body(p)}
			</article>
			{pager(p)}
			{HELP}
		</main>
	</div>'''
    main = name_pictures(main, title)
    head = ''
    if p['video']:
        v = p['video']
        ld = {'@context': 'https://schema.org', '@type': 'VideoObject', 'name': p['title'],
              'description': p['lead'] or p['title'], 'thumbnailUrl': f'https://i.ytimg.com/vi/{v["yt"]}/maxresdefault.jpg',
              'uploadDate': '2026-10-25', 'duration': 'PT{}M{}S'.format(*v['len'].split(':')),
              'embedUrl': f'https://www.youtube-nocookie.com/embed/{v["yt"]}', 'contentUrl': f'https://www.youtube.com/watch?v={v["yt"]}',
              'publisher': {'@type': 'Organization', 'name': 'ILM Tech', 'url': 'https://ilmtech.in/'}}
        head = '\n\t<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace('</', '<\\/') + '</script>'
    head += article_ld(p, g, full)
    image = f'https://i.ytimg.com/vi/{p["video"]["yt"]}/maxresdefault.jpg' if p['video'] else ''
    if not image and thumb(p).startswith('/'):
        image = SITE + thumb(p)
    body = header(guides, g['guide']['platform']) + '\n' + main + '\n' + FOOTER.format(year=datetime.date.today().year)
    title_tag = f'{full} | ILM Tech Docs' if len(full) <= 44 else full
    return document(title_tag, meta_description(describe(p) or g['lead'], g, p), p['url'], body, 'ilmd--page', image, head)


def meta_description(text, g, p):
    """70-160 characters and unique: page + guide name first, then the text cut at a word."""
    text = text.strip()
    if p is g:
        start = ''
    elif text.startswith(g['lead']) or g['lead'].startswith(text):
        start = f'{p.get("menu") or p["title"]} in {seo_name(g)}: '  # the page has no text of its own
    else:
        start = f'{seo_name(g)}: '
    if len(start + text) < 70 and g['lead'] not in text:
        text = f'{text.rstrip(".")}. {g["lead"]}' if text else g['lead']
    text = start + text
    return text if len(text) <= 160 else text[:157].rsplit(' ', 1)[0].rstrip(',;:') + '…'


def name_pictures(main, title):
    """Screenshots in the article get a text: their caption, else the page title (search engines and screen readers)."""
    count = [0]

    def caption_of(rest):
        m = re.match(r'\s*(?:</a>\s*)?<p class="caption">(.*?)</p>', rest, re.S)
        return plain(m.group(1)) if m else ''

    def fix(m):
        tag = m.group(0)
        if 'ilmd-logo' in tag or 'alt="ILM Tech"' in tag:
            return tag
        count[0] += 1
        text = caption_of(main[m.end():]) or (f'{title} – screenshot {count[0]}' if count[0] > 1 else f'{title} – screenshot')
        return tag.replace('alt=""', f'alt="{esc(text[:120])}"', 1)
    return re.sub(r'<img\b[^>]*\balt=""[^>]*>', fix, main)


def home_ld(guides):
    """WebSite + the list of guides for the docs home page."""
    org = {'@type': 'Organization', 'name': 'ILM Tech', 'url': 'https://ilmtech.in/', '@id': 'https://ilmtech.in/#organization'}
    ld = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'WebSite', 'name': 'ILM Tech Docs', 'url': f'{SITE}/', 'inLanguage': 'en', 'publisher': org},
        {'@type': 'ItemList', 'name': 'ILM Tech guides', 'itemListElement': [
            {'@type': 'ListItem', 'position': i + 1, 'name': g['title'], 'url': SITE + g['url']} for i, g in enumerate(guides)]}]}
    return '\n\t<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace('</', '<\\/') + '</script>'


def article_ld(p, g, full):
    """TechArticle + BreadcrumbList for every guide page."""
    chain, q = [p], p
    while q['parent']:
        q = q['parent']
        chain.insert(0, q)
    crumbs = [{'@type': 'ListItem', 'position': 1, 'name': 'Docs', 'item': f'{SITE}/'}]
    for c in chain:
        crumbs.append({'@type': 'ListItem', 'position': len(crumbs) + 1,
                       'name': g['title'] if c is g else (c.get('menu') or c['title']), 'item': SITE + c['url']})
    org = {'@type': 'Organization', 'name': 'ILM Tech', 'url': 'https://ilmtech.in/', '@id': 'https://ilmtech.in/#organization'}
    ld = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'TechArticle', 'headline': (g['title'] if p is g else p['title'])[:110], 'name': full,
         'description': meta_description(describe(p) or g['lead'], g, p), 'url': SITE + p['url'], 'inLanguage': 'en',
         'about': {'@type': 'SoftwareApplication', 'name': g['title'], 'applicationCategory': 'BusinessApplication',
                   'operatingSystem': PLATFORMS[g['guide']['platform']][0]},
         'isPartOf': {'@type': 'WebSite', 'name': 'ILM Tech Docs', 'url': f'{SITE}/'},
         'author': org, 'publisher': org, 'dateModified': MODIFIED},
        {'@type': 'BreadcrumbList', 'itemListElement': crumbs}]}
    return '\n\t<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace('</', '<\\/') + '</script>'


def resolve(text, guides):
    """{{link:key}}, {{link:key:n}}, {{page:key:slug}}, {{itemid:309}} -> URLs."""
    by_key = {g['guide']['key']: g for g in guides}

    def link(m):
        g = by_key[m.group(1)]
        if not m.group(2):
            return g['url']
        n = int(m.group(2))
        for p in walk(g):
            if p.get('number') == n:
                return p['url']
        sys.exit(f'no chapter {n} in {m.group(1)}')

    def pg(m):
        for p in walk(by_key[m.group(1)]):
            if p['slug'] == m.group(2):
                return p['url']
        sys.exit(f'no page {m.group(2)} in {m.group(1)}')
    text = re.sub(r'\{\{link:([\w-]+)(?::(\d+))?\}\}', link, text)
    text = re.sub(r'\{\{page:([\w-]+):([\w-]+)\}\}', pg, text)
    return text.replace('{{itemid:309}}', SHOPIFY)


def write(out, url, text):
    f = out / url.strip('/') / 'index.html' if url.strip('/') else out / 'index.html'
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding='utf-8')


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = Path(sys.argv[1])
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(HERE / 'frozen' / 'images', out / 'images')
    shutil.copytree(HERE / 'assets', out / 'assets')
    shutil.copy(HERE.parent.parent / 'themes' / 'child_hummingbird' / 'assets' / 'js' / 'ilm-consent.js', out / 'assets' / 'js' / 'ilm-consent.js')
    shutil.copyfile(HERE / 'assets' / 'images' / 'favicon.ico', out / 'favicon.ico')
    images = {}
    guides = [load_guide(g, images) for g in GUIDES]
    pages = [p for g in guides for p in walk(g)]
    for p in pages:
        write(out, p['url'], resolve(render(p, guides), guides))

    # home: src/home.html + the page list for its search box
    index = []
    for g in guides:
        for p in walk(g):
            par = p['parent']
            index.append({'t': p['title'] if p is not g else g['menu'],
                          'g': f'{g["menu"]} guide' if p is g else (par.get('menu') or par['title']),
                          'k': describe(p), 'u': p['url']})
    home = resolve((HERE / 'src' / 'home.html').read_text(encoding='utf-8'), guides).replace('src="images/', 'src="/images/')
    script = ('\n<script type="application/json" id="ilmd-index">'
              + json.dumps(index, ensure_ascii=False).replace('</', '<\\/') + '</script>')
    body = (header(guides) + f'\n<main id="ilmd-main" class="ilmd-home">\n{home}\n</main>\n'
            + FOOTER.format(year=datetime.date.today().year) + script)
    (out / 'index.html').write_text(document('ILM Tech Docs: guides for every ILM Tech module', 'Step-by-step guides and videos for '
                                    'ILM Tech PrestaShop modules, WooCommerce plugins and the Shopify app.', '/', body, 'ilmd--home', '', home_ld(guides)), encoding='utf-8')
    body = (header(guides) + '\n<main id="ilmd-main" class="ilmd-error"><p class="ilmd-error__code">404</p><h1>Page not found</h1>'
            '<p>This page has moved or no longer exists. Pick a guide from the menu, or start on the home page.</p>'
            '<p><a class="ilmd-btn" href="/">Documentation home</a></p></main>\n' + FOOTER.format(year=datetime.date.today().year))
    (out / '404.html').write_text(document('Page not found | ILM Tech Docs', 'Page not found', '/404.html', body, 'ilmd--page'), encoding='utf-8')

    # pictures
    missing = [s for s in images.values() if not Path(s).is_file()]
    if missing:
        sys.exit('missing images:\n' + '\n'.join(missing))
    for dest, src in images.items():
        target = out / 'images' / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)

    # search (the search box of each guide reads search-index.json) + sitemap
    found = []
    today = datetime.date.today().isoformat()
    known_file = HERE / 'lastmod.json'  # url -> article hash + the date that hash first appeared
    known = json.loads(known_file.read_text(encoding='utf-8')) if known_file.is_file() else {}
    dates = {}
    for f in sorted(out.rglob('index.html')):
        rel = f.parent.relative_to(out).as_posix()
        url = '/' if rel == '.' else f'/{rel}/'
        text = f.read_text(encoding='utf-8')
        m = re.search(r'<article\b.*?</article>', text, re.S) or re.search(r'<main\b.*?</main>', text, re.S) or re.search(r'<body\b.*</body>', text, re.S)
        t = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.S) or re.search(r'<title>(.*?)</title>', text, re.S)
        sha = hashlib.sha1(m.group(0).encode('utf-8')).hexdigest()
        old = known.get(url)
        dates[url] = {'h': sha, 'd': old['d'] if old and old['h'] == sha else today}
        if MODIFIED in text:
            f.write_text(text.replace(MODIFIED, dates[url]['d']), encoding='utf-8')
        found.append({'u': url, 't': plain(t.group(1)), 'x': plain(re.sub(r'<(script|style|nav|aside|h1)\b.*?</\1>', ' ', m.group(0), flags=re.S))[:6000]})
    (out / 'search-index.json').write_text(json.dumps(found, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    known_file.write_text(json.dumps(dates, indent=0, sort_keys=True) + '\n', encoding='utf-8')
    (out / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                     + ''.join(f'<url><loc>{SITE}{x["u"]}</loc><lastmod>{dates[x["u"]]["d"]}</lastmod></url>\n' for x in found)
                                     + '</urlset>\n', encoding='utf-8')
    shutil.copy(HERE / 'BingSiteAuth.xml', out / 'BingSiteAuth.xml')  # Bing Webmaster ownership of doc.ilmtech.in
    key = (HERE.parent / 'seo' / 'indexnow.key').read_text().strip()
    (out / f'{key}.txt').write_text(key, encoding='utf-8')  # IndexNow ownership, see tools/seo/indexnow.py
    # Own list since 2026-11-06, replaces Cloudflare's managed block (which cannot leave out one bot): Google-Extended is allowed by owner decision
    (out / 'robots.txt').write_text(ROBOTS.format(site=SITE), encoding='utf-8')
    # llms.txt: the guide map for AI assistants (https://llmstxt.org)
    lines = ['# ILM Tech Docs', '',
             '> Step-by-step guides and videos for the ILM Tech PrestaShop modules, WooCommerce plugins and the Shopify app. '
             'Store, prices and licences: https://ilmtech.in/ (product list: https://ilmtech.in/llms.txt). Support: sales@ilmtech.in', '']
    for g in guides:
        lines += [f'## {g["title"]} ({PLATFORMS[g["guide"]["platform"]][0]})', '', f'{g["lead"]}', '',
                  f'- [{g["title"]} – guide home]({SITE}{g["url"]})']
        for p in walk(g):
            if p is not g:
                d = describe(p)
                lines.append(f'- [{p["title"]}]({SITE}{p["url"]})' + (f': {d}' if d else ''))
        lines.append('')
    (out / 'llms.txt').write_text('\n'.join(lines), encoding='utf-8')
    rules = '\n'.join(f'RedirectMatch 301 ^{re.escape(a)}/?$ {b}' for a, b in OLD_URLS.items())
    (out / '.htaccess').write_text(HTACCESS.replace('{redirects}', rules), encoding='utf-8')

    # every internal link must lead to a page or a file
    broken = set()
    targets = {x['u'] for x in found} | {'/'}
    for f in out.rglob('*.html'):
        for href in re.findall(r'(?:href|src)="(/[^"#?]*)', f.read_text(encoding='utf-8')):
            if href.startswith(('/cdn-cgi/', '//')):
                continue
            path = out / href.lstrip('/')
            if not (path.is_file() or (path / 'index.html').is_file() or href.rstrip('/') + '/' in targets):
                broken.add(f'{f.relative_to(out)} -> {href}')
    for g in guides:
        print(f'{g["guide"]["key"]}: {sum(1 for _ in walk(g)) - 1} pages')
    print(f'{out}: {len(found)} pages in the sitemap, {len(images)} pictures, {len(OLD_URLS)} old URLs redirected')
    if broken:
        print(f'{len(broken)} broken links:\n  ' + '\n  '.join(sorted(broken)[:40]))


if __name__ == '__main__':
    main()
