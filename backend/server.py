"""MF Intelligence — Backend API."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import uuid
import logging
import secrets
import urllib.parse
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

import bcrypt
import jwt
import feedparser
from bson import ObjectId
from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends, Query, UploadFile, File
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field

from mock_data import (
    FUNDS, HOLDINGS, PERFORMANCE, ASSET_ALLOCATION, ALERTS, fund_by_id,
)
from amfi import refresh_nav_cache, get_live_nav, get_live_nav_map, SCHEME_CODE_MAP
from email_service import send_email, render_alert_email, render_digest_email
from factsheet_extractor import extract_factsheet, diff_factsheet

# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

JWT_ALGORITHM = "HS256"
JWT_SECRET = os.environ["JWT_SECRET"]
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@mfintel.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@12345")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.users.create_index("email", unique=True)
    await db.portfolio.create_index([("user_id", 1)])
    await db.portfolio.create_index([("portfolio_id", 1)])
    await db.portfolios.create_index([("user_id", 1)])
    await db.transactions.create_index([("user_id", 1), ("portfolio_id", 1)])

    existing = await db.users.find_one({"email": ADMIN_EMAIL.lower()})
    if existing is None:
        await db.users.insert_one({
            "email": ADMIN_EMAIL.lower(),
            "name": "Admin",
            "password_hash": hash_password(ADMIN_PASSWORD),
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        log.info("Seeded admin %s", ADMIN_EMAIL)
    elif not verify_password(ADMIN_PASSWORD, existing["password_hash"]):
        await db.users.update_one(
            {"email": ADMIN_EMAIL.lower()},
            {"$set": {"password_hash": hash_password(ADMIN_PASSWORD)}},
        )

    # Migrate: ensure every user has a default portfolio + backfill legacy holdings
    async for u in db.users.find({}, {"_id": 1}):
        uid = str(u["_id"])
        default = await db.portfolios.find_one({"user_id": uid, "is_default": True})
        if not default:
            default = {
                "id": str(uuid.uuid4()),
                "user_id": uid,
                "name": "Main Portfolio",
                "is_default": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.portfolios.insert_one(default.copy())
        await db.portfolio.update_many(
            {"user_id": uid, "portfolio_id": {"$exists": False}},
            {"$set": {"portfolio_id": default["id"]}},
        )
        await db.portfolio.update_many(
            {"user_id": uid, "purchase_date": {"$exists": False}},
            [{"$set": {"purchase_date": "$added_at"}}],
        )

    # Seed admin's portfolio with 4 funds if empty
    admin = await db.users.find_one({"email": ADMIN_EMAIL.lower()})
    if admin:
        admin_id = str(admin["_id"])
        admin_pf = await db.portfolios.find_one({"user_id": admin_id, "is_default": True})
        if await db.portfolio.count_documents({"user_id": admin_id}) == 0:
            seed = [
                ("axis-bluechip", 200, 45.20, 540),
                ("parag-flexi", 150, 62.40, 720),
                ("kotak-emerg", 80, 95.10, 200),
                ("hdfc-balanced", 50, 360.20, 90),
            ]
            for fid, u_, c, days_ago in seed:
                pdate = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
                await db.portfolio.insert_one({
                    "id": str(uuid.uuid4()),
                    "user_id": admin_id,
                    "portfolio_id": admin_pf["id"],
                    "fund_id": fid, "units": u_, "avg_cost": c,
                    "purchase_date": pdate,
                    "added_at": pdate,
                })

    # Fetch live AMFI NAVs in the background (non-blocking)
    import asyncio as _asyncio
    _asyncio.create_task(refresh_nav_cache(db))

    yield
    client.close()


app = FastAPI(title="MF Intelligence", lifespan=lifespan)
api = APIRouter(prefix="/api")

# ------------------------------------------------------------------
# Auth helpers
# ------------------------------------------------------------------
def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(p: str, hashed: str) -> bool:
    return bcrypt.checkpw(p.encode("utf-8"), hashed.encode("utf-8"))

def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "type": "access",
               "exp": datetime.now(timezone.utc) + timedelta(minutes=60)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id, "type": "refresh",
               "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def set_auth_cookies(resp: Response, access: str, refresh: str):
    resp.set_cookie("access_token", access, httponly=True, secure=False,
                    samesite="lax", max_age=3600, path="/")
    resp.set_cookie("refresh_token", refresh, httponly=True, secure=False,
                    samesite="lax", max_age=604800, path="/")

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(401, "Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(401, "User not found")
        user["id"] = str(user["_id"])
        user.pop("_id", None)
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class PortfolioAddIn(BaseModel):
    fund_id: str
    units: float = Field(gt=0)
    avg_cost: float = Field(gt=0)
    portfolio_id: Optional[str] = None
    purchase_date: Optional[str] = None  # ISO date

class PortfolioCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)

class TransactionIn(BaseModel):
    portfolio_id: Optional[str] = None
    fund_id: str
    type: str = Field(pattern="^(BUY|SELL)$")
    units: float = Field(gt=0)
    price: float = Field(gt=0)
    date: Optional[str] = None

class SipPlanIn(BaseModel):
    monthly: float = Field(gt=0)
    years: int = Field(ge=1, le=60)
    expected_return: float = Field(ge=0, le=50)  # %
    step_up: float = Field(default=0.0, ge=0, le=50)  # annual % step-up

class NotifSettingsIn(BaseModel):
    notify_realtime: bool = False
    notify_digest: bool = True
    notification_email: Optional[EmailStr] = None

# ------------------------------------------------------------------
# Auth endpoints
# ------------------------------------------------------------------
@api.post("/auth/register")
async def register(body: RegisterIn, response: Response):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    doc = {
        "email": email, "name": body.name,
        "password_hash": hash_password(body.password),
        "role": "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    res = await db.users.insert_one(doc)
    uid = str(res.inserted_id)
    set_auth_cookies(response,
                     create_access_token(uid, email),
                     create_refresh_token(uid))
    return {"id": uid, "email": email, "name": body.name, "role": "user"}

@api.post("/auth/login")
async def login(body: LoginIn, response: Response):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    uid = str(user["_id"])
    set_auth_cookies(response,
                     create_access_token(uid, email),
                     create_refresh_token(uid))
    return {"id": uid, "email": email, "name": user.get("name", ""),
            "role": user.get("role", "user")}

@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}

@api.get("/auth/me")
async def me(current=Depends(get_current_user)):
    return current

@api.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    rt = request.cookies.get("refresh_token")
    if not rt:
        raise HTTPException(401, "No refresh token")
    try:
        payload = jwt.decode(rt, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(401, "Invalid token type")
        uid = payload["sub"]
        user = await db.users.find_one({"_id": ObjectId(uid)})
        if not user:
            raise HTTPException(401, "User not found")
        access = create_access_token(uid, user["email"])
        response.set_cookie("access_token", access, httponly=True, secure=False,
                            samesite="lax", max_age=3600, path="/")
        return {"ok": True}
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid refresh token")

# ------------------------------------------------------------------
# Funds catalog
# ------------------------------------------------------------------
@api.get("/funds")
async def list_funds(current=Depends(get_current_user)):
    return [
        {"id": f["id"], "name": f["name"], "amc": f["amc"],
         "category": f["category"], "benchmark": f["benchmark"],
         "nav": f["nav"], "aum_cr": f["aum_cr"],
         "expense_ratio": f["expense_ratio"], "manager": f["manager"]}
        for f in FUNDS
    ]

@api.get("/funds/{fund_id}")
async def fund_detail(fund_id: str, current=Depends(get_current_user)):
    f = fund_by_id(fund_id)
    if not f:
        raise HTTPException(404, "Fund not found")
    return f

# ------------------------------------------------------------------
# Portfolio
# ------------------------------------------------------------------
@api.get("/portfolio")
async def get_portfolio(
    portfolio_id: Optional[str] = Query(None),
    current=Depends(get_current_user),
):
    q: Dict[str, Any] = {"user_id": current["id"]}
    if portfolio_id:
        q["portfolio_id"] = portfolio_id
    items = await db.portfolio.find(q, {"_id": 0}).to_list(500)
    live = await get_live_nav_map(db)
    enriched = []
    total_invested = 0.0
    total_current = 0.0
    for it in items:
        f = fund_by_id(it["fund_id"])
        if not f:
            continue
        nav = live.get(f["id"], f["nav"])  # prefer live AMFI
        invested = it["units"] * it["avg_cost"]
        current_val = it["units"] * nav
        gain = current_val - invested
        pct = (gain / invested * 100) if invested else 0.0
        total_invested += invested
        total_current += current_val
        enriched.append({**it, "fund": {
            "id": f["id"], "name": f["name"], "amc": f["amc"],
            "category": f["category"], "nav": nav,
            "manager": f["manager"], "benchmark": f["benchmark"],
            "live_nav": f["id"] in live,
        }, "invested": round(invested, 2),
           "current_value": round(current_val, 2),
           "gain": round(gain, 2), "gain_pct": round(pct, 2)})
    return {
        "holdings": enriched,
        "summary": {
            "invested": round(total_invested, 2),
            "current_value": round(total_current, 2),
            "gain": round(total_current - total_invested, 2),
            "gain_pct": round(((total_current - total_invested) / total_invested * 100) if total_invested else 0.0, 2),
            "fund_count": len(enriched),
            "live_nav_count": sum(1 for h in enriched if h["fund"]["live_nav"]),
        }
    }

@api.post("/portfolio")
async def add_to_portfolio(body: PortfolioAddIn, current=Depends(get_current_user)):
    if not fund_by_id(body.fund_id):
        raise HTTPException(404, "Fund not found")
    pf_id = body.portfolio_id
    if pf_id:
        owns = await db.portfolios.find_one({"id": pf_id, "user_id": current["id"]})
        if not owns:
            raise HTTPException(404, "Portfolio not found")
    else:
        default = await db.portfolios.find_one({"user_id": current["id"], "is_default": True})
        if not default:
            default = {"id": str(uuid.uuid4()), "user_id": current["id"],
                       "name": "Main Portfolio", "is_default": True,
                       "created_at": datetime.now(timezone.utc).isoformat()}
            await db.portfolios.insert_one(default.copy())
        pf_id = default["id"]
    pdate = body.purchase_date or datetime.now(timezone.utc).isoformat()
    item = {
        "id": str(uuid.uuid4()),
        "user_id": current["id"],
        "portfolio_id": pf_id,
        "fund_id": body.fund_id,
        "units": body.units,
        "avg_cost": body.avg_cost,
        "purchase_date": pdate,
        "added_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.portfolio.insert_one(item.copy())
    return {"ok": True, "id": item["id"]}

@api.delete("/portfolio/{item_id}")
async def remove_from_portfolio(item_id: str, current=Depends(get_current_user)):
    res = await db.portfolio.delete_one({"id": item_id, "user_id": current["id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Item not found")
    return {"ok": True}

# ------------------------------------------------------------------
# Holdings & sector diff
# ------------------------------------------------------------------
def _diff_holdings(curr: List[dict], prev: List[dict]):
    pmap = {p["stock"]: p for p in prev}
    cmap = {c["stock"]: c for c in curr}
    new_buys, exits, increased, decreased = [], [], [], []
    for stock, c in cmap.items():
        if stock not in pmap:
            new_buys.append({**c, "delta": c["weight"]})
        else:
            d = round(c["weight"] - pmap[stock]["weight"], 2)
            if d > 0:
                increased.append({**c, "previous_weight": pmap[stock]["weight"], "delta": d})
            elif d < 0:
                decreased.append({**c, "previous_weight": pmap[stock]["weight"], "delta": d})
    for stock, p in pmap.items():
        if stock not in cmap:
            exits.append({**p, "delta": -p["weight"]})
    return {
        "new_buys": sorted(new_buys, key=lambda x: -x["weight"]),
        "exits": sorted(exits, key=lambda x: x["delta"]),
        "increased": sorted(increased, key=lambda x: -x["delta"]),
        "decreased": sorted(decreased, key=lambda x: x["delta"]),
    }

@api.get("/funds/{fund_id}/holdings-diff")
async def holdings_diff(fund_id: str, current=Depends(get_current_user)):
    h = HOLDINGS.get(fund_id)
    if not h:
        raise HTTPException(404, "Holdings not available")
    return {
        "current": h["current"],
        "previous": h["previous"],
        "diff": _diff_holdings(h["current"], h["previous"]),
    }

def _aggregate_sectors(holdings: List[dict]):
    out: Dict[str, float] = {}
    for h in holdings:
        out[h["sector"]] = round(out.get(h["sector"], 0.0) + h["weight"], 2)
    return out

@api.get("/funds/{fund_id}/sector-diff")
async def sector_diff(fund_id: str, current=Depends(get_current_user)):
    h = HOLDINGS.get(fund_id)
    if not h:
        raise HTTPException(404, "Sectors not available")
    cur = _aggregate_sectors(h["current"])
    prev = _aggregate_sectors(h["previous"])
    sectors = sorted(set(list(cur.keys()) + list(prev.keys())))
    rows = []
    for s in sectors:
        c = cur.get(s, 0.0)
        p = prev.get(s, 0.0)
        delta = round(c - p, 2)
        rows.append({"sector": s, "current": c, "previous": p,
                     "delta": delta, "flag": abs(delta) >= 2.0})
    rows.sort(key=lambda r: -abs(r["delta"]))
    return {"rows": rows}

# ------------------------------------------------------------------
# Performance
# ------------------------------------------------------------------
@api.get("/funds/{fund_id}/performance")
async def fund_performance(fund_id: str, current=Depends(get_current_user)):
    p = PERFORMANCE.get(fund_id)
    if not p:
        raise HTTPException(404, "Performance not available")
    return p

@api.get("/funds/{fund_id}/asset-allocation")
async def asset_allocation(fund_id: str, current=Depends(get_current_user)):
    a = ASSET_ALLOCATION.get(fund_id)
    if not a:
        raise HTTPException(404, "Asset allocation not available")
    return a

# ------------------------------------------------------------------
# Alerts
# ------------------------------------------------------------------
@api.get("/alerts")
async def list_alerts(current=Depends(get_current_user)):
    portfolio_items = await db.portfolio.find(
        {"user_id": current["id"]}, {"_id": 0, "fund_id": 1}
    ).to_list(200)
    fund_ids = {it["fund_id"] for it in portfolio_items}
    static_alerts = [a for a in ALERTS if a["fund_id"] in fund_ids] if fund_ids else ALERTS
    db_alerts = await db.alerts.find({}, {"_id": 0}).to_list(500)
    db_alerts = [a for a in db_alerts if not fund_ids or a["fund_id"] in fund_ids]
    fmap = {f["id"]: f for f in FUNDS}
    enriched = []
    for a in list(static_alerts) + db_alerts:
        f = fmap.get(a["fund_id"])
        enriched.append({**a, "fund_name": f["name"] if f else a["fund_id"]})
    enriched.sort(key=lambda x: x["created_at"], reverse=True)
    return enriched

# ------------------------------------------------------------------
# News (RSS via Google News)
# ------------------------------------------------------------------
@api.get("/funds/{fund_id}/news")
async def fund_news(fund_id: str, current=Depends(get_current_user)):
    f = fund_by_id(fund_id)
    if not f:
        raise HTTPException(404, "Fund not found")
    # Build a Google News RSS query around AMC + scheme keywords
    query = f"{f['amc']} mutual fund"
    url = ("https://news.google.com/rss/search?q="
           + urllib.parse.quote(query)
           + "&hl=en-IN&gl=IN&ceid=IN:en")
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:20]:
            items.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": entry.get("source", {}).get("title", "") if isinstance(entry.get("source"), dict) else "",
                "summary": entry.get("summary", "")[:300],
            })
        return {"fund_id": fund_id, "query": query, "items": items}
    except Exception as e:
        log.exception("news fetch failed")
        return {"fund_id": fund_id, "query": query, "items": [], "error": str(e)}

# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------
@api.get("/")
async def root():
    return {"service": "MF Intelligence", "ok": True}

# ------------------------------------------------------------------
# Portfolios (multi-portfolio support)
# ------------------------------------------------------------------
async def _ensure_default_portfolio(user_id: str) -> dict:
    pf = await db.portfolios.find_one({"user_id": user_id, "is_default": True}, {"_id": 0})
    if pf:
        return pf
    pf = {"id": str(uuid.uuid4()), "user_id": user_id,
          "name": "Main Portfolio", "is_default": True,
          "created_at": datetime.now(timezone.utc).isoformat()}
    await db.portfolios.insert_one(pf.copy())
    return pf


@api.get("/portfolios")
async def list_portfolios(current=Depends(get_current_user)):
    await _ensure_default_portfolio(current["id"])
    items = await db.portfolios.find(
        {"user_id": current["id"]}, {"_id": 0}
    ).sort("created_at", 1).to_list(50)
    out = []
    for p in items:
        cnt = await db.portfolio.count_documents(
            {"user_id": current["id"], "portfolio_id": p["id"]}
        )
        out.append({**p, "fund_count": cnt})
    return out


@api.post("/portfolios")
async def create_portfolio(body: PortfolioCreateIn, current=Depends(get_current_user)):
    pf = {"id": str(uuid.uuid4()), "user_id": current["id"],
          "name": body.name.strip(), "is_default": False,
          "created_at": datetime.now(timezone.utc).isoformat()}
    await db.portfolios.insert_one(pf.copy())
    return pf


@api.delete("/portfolios/{pid}")
async def delete_portfolio(pid: str, current=Depends(get_current_user)):
    pf = await db.portfolios.find_one({"id": pid, "user_id": current["id"]})
    if not pf:
        raise HTTPException(404, "Not found")
    if pf.get("is_default"):
        raise HTTPException(400, "Cannot delete default portfolio")
    await db.portfolio.delete_many({"user_id": current["id"], "portfolio_id": pid})
    await db.transactions.delete_many({"user_id": current["id"], "portfolio_id": pid})
    await db.portfolios.delete_one({"id": pid, "user_id": current["id"]})
    return {"ok": True}


# ------------------------------------------------------------------
# XIRR (Newton-Raphson on cashflows)
# ------------------------------------------------------------------
def _xirr(cashflows: List[tuple]) -> Optional[float]:
    """cashflows: list of (date, amount). Negative for outflow, positive for inflow."""
    if len(cashflows) < 2:
        return None
    has_neg = any(cf < 0 for _, cf in cashflows)
    has_pos = any(cf > 0 for _, cf in cashflows)
    if not (has_neg and has_pos):
        return None
    d0 = cashflows[0][0]
    rate = 0.1
    for _ in range(200):
        f, df = 0.0, 0.0
        for d, cf in cashflows:
            t = (d - d0).days / 365.0
            base = (1.0 + rate)
            if base <= 0:
                return None
            f += cf / base ** t
            df += -t * cf / base ** (t + 1)
        if abs(df) < 1e-12:
            break
        new_rate = rate - f / df
        if abs(new_rate - rate) < 1e-8:
            return new_rate
        rate = max(new_rate, -0.999)
    return rate


def _parse_iso(s: str) -> datetime:
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


@api.get("/portfolios/{pid}/xirr")
async def portfolio_xirr(pid: str, current=Depends(get_current_user)):
    pf = await db.portfolios.find_one({"id": pid, "user_id": current["id"]})
    if not pf:
        raise HTTPException(404, "Portfolio not found")
    items = await db.portfolio.find(
        {"user_id": current["id"], "portfolio_id": pid}, {"_id": 0}
    ).to_list(500)
    txns = await db.transactions.find(
        {"user_id": current["id"], "portfolio_id": pid}, {"_id": 0}
    ).to_list(500)
    today = datetime.now(timezone.utc)
    cashflows: List[tuple] = []
    total_curr = 0.0
    for it in items:
        f = fund_by_id(it["fund_id"])
        if not f:
            continue
        d = _parse_iso(it.get("purchase_date") or it.get("added_at"))
        cashflows.append((d, -(it["units"] * it["avg_cost"])))
        total_curr += it["units"] * f["nav"]
    for t in txns:
        d = _parse_iso(t.get("date") or t.get("added_at", today.isoformat()))
        amt = t["units"] * t["price"]
        cashflows.append((d, -amt if t["type"] == "BUY" else amt))
    cashflows.append((today, total_curr))
    cashflows.sort(key=lambda x: x[0])
    rate = _xirr(cashflows)
    return {
        "xirr_pct": round(rate * 100, 2) if rate is not None else None,
        "cashflow_count": len(cashflows),
        "current_value": round(total_curr, 2),
    }


# ------------------------------------------------------------------
# Tax report (Indian equity rules: STCG ≤1Y @15%, LTCG >1Y @10% above 1L)
# ------------------------------------------------------------------
@api.get("/portfolios/{pid}/tax-report")
async def portfolio_tax(pid: str, current=Depends(get_current_user)):
    pf = await db.portfolios.find_one({"id": pid, "user_id": current["id"]})
    if not pf:
        raise HTTPException(404, "Portfolio not found")
    items = await db.portfolio.find(
        {"user_id": current["id"], "portfolio_id": pid}, {"_id": 0}
    ).to_list(500)
    today = datetime.now(timezone.utc)
    LTCG_EXEMPT = 100000.0
    rows = []
    st_gain = 0.0
    lt_gain = 0.0
    for it in items:
        f = fund_by_id(it["fund_id"])
        if not f:
            continue
        d = _parse_iso(it.get("purchase_date") or it.get("added_at"))
        days = (today - d).days
        invested = it["units"] * it["avg_cost"]
        current_val = it["units"] * f["nav"]
        gain = current_val - invested
        is_long = days >= 365
        if is_long:
            lt_gain += gain
        else:
            st_gain += gain
        rows.append({
            "id": it["id"], "fund_id": f["id"], "fund_name": f["name"],
            "category": f["category"],
            "purchase_date": d.date().isoformat(),
            "days_held": days,
            "term": "LTCG" if is_long else "STCG",
            "invested": round(invested, 2),
            "current_value": round(current_val, 2),
            "gain": round(gain, 2),
        })
    lt_taxable = max(0.0, lt_gain - LTCG_EXEMPT)
    st_tax = max(0.0, st_gain) * 0.15
    lt_tax = lt_taxable * 0.10
    return {
        "rows": rows,
        "summary": {
            "stcg_gain": round(st_gain, 2),
            "ltcg_gain": round(lt_gain, 2),
            "ltcg_exemption": LTCG_EXEMPT,
            "ltcg_taxable": round(lt_taxable, 2),
            "stcg_tax": round(st_tax, 2),
            "ltcg_tax": round(lt_tax, 2),
            "total_estimated_tax": round(st_tax + lt_tax, 2),
        },
        "disclaimer": "Estimate assumes equity-oriented MFs (>65% equity). Indexation not applied.",
    }


# ------------------------------------------------------------------
# SIP planner (pure calculation, no DB)
# ------------------------------------------------------------------
@api.post("/sip-planner")
async def sip_planner(body: SipPlanIn, current=Depends(get_current_user)):
    monthly_rate = (body.expected_return / 100.0) / 12.0
    months = body.years * 12
    schedule = []
    fv = 0.0
    invested = 0.0
    sip_amount = body.monthly
    for m in range(1, months + 1):
        # Monthly compounding + step-up at each year-end
        fv = (fv + sip_amount) * (1 + monthly_rate)
        invested += sip_amount
        if m % 12 == 0:
            schedule.append({
                "year": m // 12,
                "invested": round(invested, 2),
                "value": round(fv, 2),
                "wealth_gain": round(fv - invested, 2),
            })
            sip_amount = sip_amount * (1 + body.step_up / 100.0)
    return {
        "summary": {
            "total_invested": round(invested, 2),
            "future_value": round(fv, 2),
            "wealth_gain": round(fv - invested, 2),
            "multiple": round(fv / invested, 2) if invested else 0,
        },
        "schedule": schedule,
    }


# ------------------------------------------------------------------
# AMFI Live NAV
# ------------------------------------------------------------------
@api.get("/nav/status")
async def nav_status(current=Depends(get_current_user)):
    docs = await db.nav_cache.find({}, {"_id": 0}).to_list(50)
    return {"navs": docs, "count": len(docs)}


@api.post("/nav/refresh")
async def nav_refresh(current=Depends(get_current_user)):
    if current.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    return await refresh_nav_cache(db)


# ------------------------------------------------------------------
# Notification settings + email
# ------------------------------------------------------------------
@api.get("/settings/notifications")
async def get_notif_settings(current=Depends(get_current_user)):
    user = await db.users.find_one({"_id": ObjectId(current["id"])}, {"_id": 0})
    return {
        "email": user.get("email"),
        "notification_email": user.get("notification_email") or user.get("email"),
        "notify_realtime": bool(user.get("notify_realtime", False)),
        "notify_digest": bool(user.get("notify_digest", True)),
    }


@api.put("/settings/notifications")
async def update_notif_settings(body: NotifSettingsIn, current=Depends(get_current_user)):
    update = {
        "notify_realtime": body.notify_realtime,
        "notify_digest": body.notify_digest,
    }
    if body.notification_email:
        update["notification_email"] = body.notification_email.lower()
    await db.users.update_one({"_id": ObjectId(current["id"])}, {"$set": update})
    return {"ok": True, **update}


async def _user_notif_email(user_id: str, fallback: str) -> str:
    u = await db.users.find_one({"_id": ObjectId(user_id)}, {"_id": 0, "notification_email": 1})
    return (u.get("notification_email") if u else None) or fallback


@api.post("/notifications/test")
async def notifications_test(current=Depends(get_current_user)):
    to = await _user_notif_email(current["id"], current["email"])
    html = render_alert_email({
        "type": "test", "severity": "low",
        "title": "Test email from MF.TERMINAL",
        "fund_name": "—",
        "message": "If you received this, your real-time alert pipeline is working.",
    })
    res = await send_email(to, "MF.TERMINAL · Test email", html)
    if not res.get("ok"):
        raise HTTPException(500, res.get("error", "Send failed"))
    return {**res, "sent_to": to}


@api.post("/notifications/digest")
async def notifications_digest(current=Depends(get_current_user)):
    portfolio_items = await db.portfolio.find(
        {"user_id": current["id"]}, {"_id": 0, "fund_id": 1}
    ).to_list(200)
    fund_ids = {it["fund_id"] for it in portfolio_items}
    static_alerts = [a for a in ALERTS if a["fund_id"] in fund_ids] if fund_ids else []
    db_alerts = await db.alerts.find({}, {"_id": 0}).to_list(500)
    db_alerts = [a for a in db_alerts if not fund_ids or a["fund_id"] in fund_ids]
    fmap = {f["id"]: f for f in FUNDS}
    items = []
    for a in list(static_alerts) + db_alerts:
        f = fmap.get(a["fund_id"])
        items.append({**a, "fund_name": f["name"] if f else a["fund_id"]})
    items.sort(key=lambda x: x["created_at"], reverse=True)
    html = render_digest_email(items)
    to = await _user_notif_email(current["id"], current["email"])
    res = await send_email(to, f"MF.TERMINAL · Digest ({len(items)} signals)", html)
    if not res.get("ok"):
        raise HTTPException(500, res.get("error", "Send failed"))
    return {**res, "alert_count": len(items), "sent_to": to}


# ------------------------------------------------------------------
# Factsheet PDF upload + Gemini extraction
# ------------------------------------------------------------------
@api.post("/funds/{fund_id}/factsheet")
async def upload_factsheet(
    fund_id: str,
    file: UploadFile = File(...),
    current=Depends(get_current_user),
):
    if not fund_by_id(fund_id):
        raise HTTPException(404, "Fund not found")
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "PDF only")
    body = await file.read()
    if len(body) > 15 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 15MB)")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        tf.write(body)
        path = tf.name
    try:
        extracted = await extract_factsheet(path, fund_id)
    except Exception as e:
        log.exception("factsheet extraction failed")
        raise HTTPException(500, f"Extraction failed: {e}")
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

    # Compare vs latest snapshot of same fund (any user) for change detection
    prev = await db.factsheet_snapshots.find_one(
        {"fund_id": fund_id}, sort=[("created_at", -1)], projection={"_id": 0}
    )
    snapshot = {
        "id": str(uuid.uuid4()),
        "fund_id": fund_id,
        "user_id": current["id"],
        "filename": file.filename,
        "extracted": extracted,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.factsheet_snapshots.insert_one(snapshot.copy())

    changes = diff_factsheet(prev.get("extracted") if prev else None, extracted)
    new_alerts = []
    for ch in changes:
        a = {
            "id": f"alrt-{uuid.uuid4().hex[:8]}",
            "fund_id": fund_id,
            "type": ch["type"],
            "severity": ch["severity"],
            "title": ch["title"],
            "message": ch["message"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "factsheet_upload",
        }
        await db.alerts.insert_one(a.copy())
        new_alerts.append(a)

    # Real-time email push to users who opted in & hold this fund
    if new_alerts:
        holders = await db.portfolio.distinct("user_id", {"fund_id": fund_id})
        async for u in db.users.find(
            {"_id": {"$in": [ObjectId(h) for h in holders]},
             "notify_realtime": True},
            {"email": 1},
        ):
            for a in new_alerts:
                payload = {**a, "fund_name": fund_by_id(fund_id)["name"]}
                await send_email(u["email"],
                                 f"MF.TERMINAL · {a['title']}",
                                 render_alert_email(payload))

    return {
        "ok": True,
        "snapshot_id": snapshot["id"],
        "extracted": extracted,
        "alerts_generated": new_alerts,
        "had_previous_snapshot": prev is not None,
    }


@api.get("/funds/{fund_id}/factsheets")
async def list_factsheets(fund_id: str, current=Depends(get_current_user)):
    docs = await db.factsheet_snapshots.find(
        {"fund_id": fund_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(20)
    return docs


# ------------------------------------------------------------------
# Mount
# ------------------------------------------------------------------
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
