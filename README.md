# ILM Tech Docs (doc.ilmtech.in)

Source of the documentation site https://doc.ilmtech.in — guides for the ILM Tech
PrestaShop modules, WooCommerce plugins and Shopify apps.

| Folder / file | What it is |
|---|---|
| `src/<guide>/` | Guide pages: `pages.json` (order, titles, videos) + one `<slug>.html` per page. Edit these by hand. |
| `src/home.html` | Home page |
| `assets/` | CSS, JS, images, fonts of the site |
| `template/` | Page template |
| `frozen/images/` | Pictures kept from the old site (Shopify Size Chart guide) |
| `logos/` | Module logos |
| `build.py` | Builds the whole static site, sitemap, search index, llms.txt, .htaccess |
| `lastmod.json` | Last-changed date per page (written by the build) |
| `store_doc_links.php` | Sets the Documentation / Demo / Video buttons on ilmtech.in products |
| `import_*.py`, `add_minmax_ai_pages.py` | One-off importers already run; do not run again |

Guides: Size Chart (PrestaShop, WooCommerce Free + Pro, Shopify), Min/Max/Multiple Order Qty/Amt
(PrestaShop, WooCommerce, Shopify), Chat & Order for WhatsApp (PrestaShop, WooCommerce, Shopify),
All In One Captcha (PrestaShop), AI Chat (PrestaShop).

## Build

The working copy lives in the store repo (`tools/docsite`); this repo is a copy of it.
`build.py` also reads two files from the store repo (`themes/child_hummingbird/assets/js/ilm-consent.js`
and `tools/seo/indexnow.key`), so build from the store repo:

```
python3 tools/docsite/build.py OUT
```
