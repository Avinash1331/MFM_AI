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
- 16/16 backend pytest cases pass.
- E2E playwright flow validated (login, dashboard tiles, portfolio add/remove, all 5 fund tabs,
  alerts filter, logout).

## Backlog (P1)
- Email push alerts (Resend / SendGrid).
- Real factsheet ingestion (PDF upload + LLM parsing).
- AMFI NAV API integration for live prices.
- News result caching to avoid Google News rate limits.

## Backlog (P2)
- XIRR / SIP planner.
- Tax / capital-gain reports.
- Multi-portfolio support per user.
- Lifespan context migration (deprecation cleanup).
