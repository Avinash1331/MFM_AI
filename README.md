# MF.TERMINAL — Mutual Fund Portfolio Intelligence

A Bloomberg-terminal-style mutual fund watchdog: tracks holdings drift, sector shifts, fund-manager
changes, benchmark-beating history, computes XIRR + tax estimates, runs SIP projections, and ingests
factsheet PDFs with Gemini for change detection + email alerts.

![stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20React%20%2B%20MongoDB-22c55e?style=flat-square)

---

## Features
- **Portfolio dashboard** with live AMFI NAV (auto-refreshed at startup).
- **Holdings change tracker**: new buys / exits / weight ± deltas vs previous month.
- **Sector weight tracker** with ±2% threshold flags.
- **Performance**: 1Y / 3Y / 5Y / inception vs category & benchmark, rolling 3Y chart.
- **Benchmark-beating history**: 5Y / 10Y / 15Y pass-fail with differentials.
- **Alerts center** (manager / category / objective / name / asset-allocation changes).
- **Fund-specific Google News** RSS feed.
- **Multi-portfolio** support, **XIRR**, Indian **STCG/LTCG tax** estimator, **SIP planner** with step-up.
- **Factsheet PDF upload** → Gemini 3 Pro extracts holdings/sectors → auto-diff → alerts → email.
- **Resend email**: real-time per-alert + on-demand digest.

## Stack
- **Backend**: FastAPI + Motor (async MongoDB) + JWT auth (httpOnly cookies, bcrypt) + `feedparser` + `resend` + `emergentintegrations` (Gemini)
- **Frontend**: React 19 + Tailwind + Recharts + Phosphor Icons + IBM Plex Mono / Chivo
- **DB**: MongoDB

---

## 🚀 Quick start

### Option A: Docker (one command)
```bash
git clone <your-repo-url>
cd <repo>
docker compose up --build
```
Visit **http://localhost:3000** — login with `admin@mfintel.com` / `Admin@12345`.

To enable email/PDF ingestion, set keys in your shell first:
```bash
export RESEND_API_KEY=re_xxx
export EMERGENT_LLM_KEY=sk-emergent-xxx
docker compose up --build
```

### Option B: Local (no Docker)

**Prereqs**: Python 3.11, Node 20+, Yarn, MongoDB 7+

```bash
git clone <your-repo-url>
cd <repo>

# macOS / Linux / WSL
./setup.sh

# Windows
setup.bat
```

The script:
1. Copies `.env.example` → `.env` in both `backend/` and `frontend/`
2. Generates a random `JWT_SECRET`
3. Creates a Python venv and installs deps (incl. `emergentintegrations`)
4. Runs `yarn install` for the frontend

Then start each service in its own terminal:

```bash
# Terminal 1 — MongoDB (skip if already running)
docker run -d -p 27017:27017 --name mongo mongo:7

# Terminal 2 — Backend
cd backend
source .venv/bin/activate            # Windows: .venv\Scripts\activate
uvicorn server:app --reload --port 8001

# Terminal 3 — Frontend
cd frontend
yarn start
```

Visit **http://localhost:3000** — admin auto-seeded with a demo 4-fund portfolio.

### Option C: VS Code (one click)

After running `setup.sh` once:
1. Open the repo folder in VS Code
2. Install recommended extensions (popup will appear)
3. Press **F5** → choose **"Run full stack"** — backend + frontend launch with a single shortcut

---

## 🔑 Environment variables

Copy `.env.example` → `.env` in each folder.

### `backend/.env`
| Var | Required | Notes |
|---|---|---|
| `MONGO_URL` | ✅ | `mongodb://localhost:27017` for local |
| `DB_NAME` | ✅ | e.g. `mf_intel` |
| `JWT_SECRET` | ✅ | 64-char hex (`python -c "import secrets;print(secrets.token_hex(32))"`) |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | ✅ | Auto-seeded admin |
| `CORS_ORIGINS` | ✅ | `http://localhost:3000` for local |
| `RESEND_API_KEY` | optional | Required for email features. Get one at [resend.com](https://resend.com) |
| `SENDER_EMAIL` | optional | Default `onboarding@resend.dev` (no domain verification needed) |
| `EMERGENT_LLM_KEY` | optional | Required for `/factsheet` upload feature (Gemini extraction) |

> **Resend free tier**: without a verified domain you can ONLY send to your account's verified
> email. Add the recipient as your "Notification Email" in **Settings** to receive alerts.

### `frontend/.env`
| Var | Required | Notes |
|---|---|---|
| `REACT_APP_BACKEND_URL` | ✅ | `http://localhost:8001` for local |

---

## 📂 Project layout

```
.
├── backend/                FastAPI + Motor (MongoDB)
│   ├── server.py           All routes (~900 lines)
│   ├── mock_data.py        6 sample funds + holdings + alerts
│   ├── amfi.py             AMFI NAVAll.txt parser + cache
│   ├── email_service.py    Resend wrapper + HTML templates
│   ├── factsheet_extractor.py   Gemini 3 Pro PDF → JSON + diff
│   ├── tests/              pytest suite (39 tests)
│   ├── .env.example
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               React 19 + Tailwind
│   ├── src/
│   │   ├── pages/          OverviewPage, PortfolioPage, FundDetailPage,
│   │   │                   AlertsPage, NewsPage, SipPlannerPage,
│   │   │                   TaxReportPage, FactsheetPage, SettingsPage,
│   │   │                   LoginPage
│   │   ├── components/     AppLayout (sidebar + portfolio switcher)
│   │   └── lib/            api.js, auth.jsx, portfolio.jsx
│   ├── .env.example
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml      Mongo + backend + frontend
├── setup.sh / setup.bat    One-shot local installer
└── .vscode/                launch.json (F5), settings, extensions
```

---

## 🧪 Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

All 39 tests should pass (covers auth, portfolios, XIRR, tax, SIP, AMFI, email, factsheet).

---

## 🛠️ Common issues

| Problem | Fix |
|---|---|
| `mongo` not running | `docker run -d -p 27017:27017 --name mongo mongo:7` |
| `pip install emergentintegrations` fails | Add the index URL: `pip install --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ emergentintegrations` |
| Frontend can't reach backend | Confirm `REACT_APP_BACKEND_URL=http://localhost:8001` in `frontend/.env` and restart `yarn start` |
| `/api/notifications/test` says only verified email | Resend free tier — use the email you signed up with at resend.com OR verify a domain |
| AMFI fetch fails | Network blocked — portfolio falls back to mock NAVs automatically |

---

## 📄 License
MIT
