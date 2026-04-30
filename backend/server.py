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
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

import bcrypt
import jwt
import feedparser
from bson import ObjectId
from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field

from mock_data import (
    FUNDS, HOLDINGS, PERFORMANCE, ASSET_ALLOCATION, ALERTS, fund_by_id,
)

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

app = FastAPI(title="MF Intelligence")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

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
async def get_portfolio(current=Depends(get_current_user)):
    items = await db.portfolio.find(
        {"user_id": current["id"]}, {"_id": 0}
    ).to_list(200)
    enriched = []
    total_invested = 0.0
    total_current = 0.0
    for it in items:
        f = fund_by_id(it["fund_id"])
        if not f:
            continue
        invested = it["units"] * it["avg_cost"]
        current_val = it["units"] * f["nav"]
        gain = current_val - invested
        pct = (gain / invested * 100) if invested else 0.0
        total_invested += invested
        total_current += current_val
        enriched.append({**it, "fund": {
            "id": f["id"], "name": f["name"], "amc": f["amc"],
            "category": f["category"], "nav": f["nav"],
            "manager": f["manager"], "benchmark": f["benchmark"],
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
        }
    }

@api.post("/portfolio")
async def add_to_portfolio(body: PortfolioAddIn, current=Depends(get_current_user)):
    if not fund_by_id(body.fund_id):
        raise HTTPException(404, "Fund not found")
    item = {
        "id": str(uuid.uuid4()),
        "user_id": current["id"],
        "fund_id": body.fund_id,
        "units": body.units,
        "avg_cost": body.avg_cost,
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
    user_alerts = [a for a in ALERTS if a["fund_id"] in fund_ids] if fund_ids else ALERTS
    fmap = {f["id"]: f for f in FUNDS}
    enriched = []
    for a in user_alerts:
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
# Startup
# ------------------------------------------------------------------
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.portfolio.create_index([("user_id", 1)])
    # Seed admin
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
            {"$set": {"password_hash": hash_password(ADMIN_PASSWORD)}}
        )
        log.info("Updated admin password")

    # Seed admin's portfolio with 4 funds if empty (so demo lights up immediately)
    admin = await db.users.find_one({"email": ADMIN_EMAIL.lower()})
    admin_id = str(admin["_id"])
    if await db.portfolio.count_documents({"user_id": admin_id}) == 0:
        seed = [
            ("axis-bluechip", 200, 45.20),
            ("parag-flexi", 150, 62.40),
            ("kotak-emerg", 80, 95.10),
            ("hdfc-balanced", 50, 360.20),
        ]
        for fid, u, c in seed:
            await db.portfolio.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": admin_id,
                "fund_id": fid, "units": u, "avg_cost": c,
                "added_at": datetime.now(timezone.utc).isoformat(),
            })

@app.on_event("shutdown")
async def shutdown():
    client.close()

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
