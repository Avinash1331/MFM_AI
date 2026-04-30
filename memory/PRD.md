# MF Intelligence — Product Requirements

## Original Problem Statement
Build a Mutual Fund Portfolio Intelligence & Monitoring App for an informed Indian investor.
Beyond NAV tracking, the app should function as an active portfolio watchdog — flagging holdings changes,
sector shifts, manager changes, category reclassifications, asset-allocation drifts, and per-fund news.

## User Persona
- Indian retail investor with a multi-fund equity/balanced portfolio.
- Wants Bloomberg-terminal style density, not a consumer-friendly fluff dashboard.

## Architecture
- **Backend**: FastAPI + MongoDB + JWT (httpOnly cookies, bcrypt). RSS via `feedparser` (Google News).
- **Frontend**: React 19 + Tailwind + Recharts + Phosphor Icons. Bloomberg-terminal aesthetic
  (Chivo headings, IBM Plex Mono for data, sharp corners, green/red data encoding).
- **Data**: Mock realistic data for 6 funds (Axis Bluechip, Parag Flexi, Mirae L&M, Kotak Emerging,
  SBI Smallcap, HDFC Balanced Advantage) — current vs previous month holdings, sectors,
  performance, asset allocation, and 7 sample alerts.

## What's Implemented (2026-02)
- JWT auth (register / login / logout / me / refresh) with httpOnly cookies.
- Admin seeding (`admin@mfintel.com` / `Admin@12345`) + auto-seeded 4-fund demo portfolio.
- Portfolio CRUD with units & avg-cost, P&L computed against live mock NAV.
- Per-fund: holdings diff (new buys / exits / increased / decreased), sector diff
  (with ±2% flag), performance vs category vs benchmark (1Y/3Y/5Y/inception + rolling 3Y),
  benchmark beating history (5/10/15Y pass-fail with differential), asset allocation Δ.
- Alerts feed (7 mock alerts: manager change, category reclassification, objective amend,
  name change, asset-allocation shift) filtered to user's portfolio.
- Per-fund Google News RSS feed via `feedparser`.
- Pages: Login / Register / Overview / Portfolio / Fund Detail (5 tabs) / Alerts / News.

## Tested
- 25/25 backend pytest cases pass.
- E2E playwright flow validated (login, dashboard tiles, portfolio add/remove, all 5 fund tabs,
  alerts filter, logout). Phase 2: portfolio CRUD, XIRR, tax-report, SIP planner all verified.

## What's Implemented (2026-02 — Phase 2)
- **Multi-portfolio support**: users can create/delete named portfolios; default "Main Portfolio"
  auto-created on signup. Header switcher persists across pages via localStorage. Holdings filtered by
  active portfolio.
- **XIRR**: per-portfolio annualised return via Newton-Raphson over cashflows (purchase lots + current
  value). Rendered as 5th KPI tile on Overview.
- **Tax Report** (`/tax`): Indian equity-MF rules — STCG ≤1Y @15%, LTCG >1Y @10% above ₹1L exemption.
  Lot-level table + summary tiles + disclaimer.
- **SIP Planner** (`/sip`): pure calculator with monthly amount, years, expected return, optional
  annual step-up. Stacked bar chart of invested vs wealth-gain per year.
- **FastAPI lifespan** migration replacing deprecated `@app.on_event` decorators. Includes one-shot
  migration backfilling `portfolio_id` and `purchase_date` on legacy holdings.

## Backlog (P1)
- Email push alerts (Resend / SendGrid).
- Real factsheet ingestion (PDF upload + LLM parsing).
- AMFI NAV API integration for live prices.
- News result caching to avoid Google News rate limits.

## Backlog (P2)
- Transaction-level (BUY/SELL) ledger with FIFO redemption matching for true realized gains.
- AI watchdog summary (weekly LLM digest).
- Multi-currency / international funds.
- One-shot migration flag (skip per-startup walk).
