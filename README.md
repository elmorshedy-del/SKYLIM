# Celeste Luxury Limo — private chauffeur service platform

Website, instant reservations, Stripe payments, live trip tracking and an owner dashboard for a premium
Cadillac Escalade chauffeur service in New York and New Jersey.

| Document | For |
|---|---|
| [docs/LAUNCH-PLAN.md](docs/LAUNCH-PLAN.md) | Positioning, services, authority gates, pricing strategy, capacity plan, timeline |
| [docs/SEO-PLAN.md](docs/SEO-PLAN.md) | Google's rules applied, keyword-to-page map, indexing at launch, analytics / Google tags |
| [INTEGRATION-GUIDE.md](INTEGRATION-GUIDE.md) | Runbook: deploy, Stripe, tracking, email, daily operation |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Code map, invariants, how to extend |
| [pricing-proposal.md](pricing-proposal.md) | Current rate proposal for owner approval |

```bash
pip install -r requirements-dev.txt
python3 build.py && uvicorn app.main:app --reload
pytest
```

Edit business facts in `data.py` and landing-page copy in `landing_pages.py`, then `python3 build.py`.
The logo lives in `static/brand/` and `marketing/brand.py` (see docs/ARCHITECTURE.md).
Never hand-edit `index.html` or `pages/`.
