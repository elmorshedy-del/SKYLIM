# Meridian Black Car — NJ → NYC flat-rate SUV site

A complete, deployable static site. Open `index.html` in a browser, or deploy the
whole folder to any static host.

## What's here

| File | What it is |
|---|---|
| `index.html` | The entire site. Self-contained — no build step needed to serve it. |
| `pricing.md` | Machine-readable rate card so AI agents can quote your real prices. |
| `robots.txt` | Allows the AI citation crawlers (GPTBot, PerplexityBot, ClaudeBot…). |
| `sitemap.xml` | For Search Console / Bing Webmaster Tools. |
| `INTEGRATION-GUIDE.md` | **Read this first.** How to go live: payments, SMS, GPS, bookings. |
| `data.py` | Single source of truth: brand, 21 county rates, vehicles, FAQ, reviews. |
| `build.py` / `build_css.py` / `build_js.py` | The generator. |

## Changing rates or branding

Edit `data.py`, then:

```bash
python3 build.py
```

That one command regenerates the rate table, all 42 structured-data price offers,
the per-county FAQ answers, and `pricing.md` **together** — so they can't drift apart.
Never hand-edit `index.html`; it is generated and your changes will be overwritten.

## Before you launch

`INTEGRATION-GUIDE.md §0` lists every placeholder that must be replaced —
company name, phone, address, licence number, and the rating/review counts.
Do not ship the invented review numbers; fake `AggregateRating` markup can earn
a Google manual action.

## Deploy

```bash
npx vercel deploy --prod
# or: netlify deploy --prod --dir=.
# or drop the folder on Cloudflare Pages / S3 + CloudFront
```
