# Meridian — private chauffeur service platform

Website, instant reservations, Stripe payments, live trip tracking and an owner dashboard for a premium
Cadillac Escalade chauffeur service in New York and New Jersey.

| Document | For |
|---|---|
| [docs/LAUNCH-PLAN.md](docs/LAUNCH-PLAN.md) | Positioning, services, authority gates, pricing strategy, capacity plan, timeline |
| [docs/SEO-PLAN.md](docs/SEO-PLAN.md) | Evidence-based local SEO and the analytics / Google tags setup |
| [INTEGRATION-GUIDE.md](INTEGRATION-GUIDE.md) | Runbook: deploy, Stripe, tracking, email, daily operation |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Code map, invariants, how to extend |
| [pricing-proposal.md](pricing-proposal.md) | Current rate proposal for owner approval |

```bash
pip install -r requirements-dev.txt
python3 build.py && uvicorn app.main:app --reload
pytest
```

Edit business content in `data.py`, then `python3 build.py`. Never hand-edit `index.html`.
