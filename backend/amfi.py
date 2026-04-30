"""AMFI live NAV fetcher — parses NAVAll.txt feed."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

import requests

log = logging.getLogger(__name__)

AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"

# Map our internal fund IDs to AMFI scheme codes (regular/direct growth schemes)
SCHEME_CODE_MAP: Dict[str, str] = {
    "axis-bluechip": "120465",       # Axis Bluechip Fund - Direct Plan - Growth
    "parag-flexi": "122639",         # Parag Parikh Flexi Cap Fund - Direct - Growth
    "mirae-largemid": "118528",      # Mirae Asset Large & Midcap Fund - Direct - Growth
    "kotak-emerg": "112277",         # Kotak Emerging Equity Fund - Direct - Growth
    "sbi-smallcap": "125497",        # SBI Small Cap Fund - Direct Plan - Growth
    "hdfc-balanced": "118955",       # HDFC Balanced Advantage Fund - Direct - Growth
}


def _parse(raw: str) -> Dict[str, dict]:
    """Parse AMFI NAVAll.txt into {scheme_code: {nav, date, name}}."""
    out: Dict[str, dict] = {}
    for line in raw.splitlines():
        if not line or ";" not in line:
            continue
        parts = line.split(";")
        if len(parts) < 6:
            continue
        code = parts[0].strip()
        if not code.isdigit():
            continue
        name = parts[3].strip()
        nav_str = parts[4].strip()
        date = parts[5].strip()
        try:
            nav = float(nav_str)
        except ValueError:
            continue
        out[code] = {"nav": nav, "name": name, "date": date}
    return out


async def fetch_amfi_navs(timeout: int = 20) -> Dict[str, dict]:
    """Fetch & parse AMFI NAV feed. Returns dict of scheme_code -> data."""
    def _fetch():
        r = requests.get(AMFI_URL, timeout=timeout, headers={"User-Agent": "MF-Intel/0.3"})
        r.raise_for_status()
        return r.text
    try:
        raw = await asyncio.to_thread(_fetch)
        parsed = _parse(raw)
        log.info("AMFI parsed %d schemes", len(parsed))
        return parsed
    except Exception as e:
        log.warning("AMFI fetch failed: %s", e)
        return {}


async def refresh_nav_cache(db) -> dict:
    """Fetch AMFI feed and store in MongoDB nav_cache collection."""
    parsed = await fetch_amfi_navs()
    if not parsed:
        return {"updated": 0, "error": "fetch failed"}
    now = datetime.now(timezone.utc).isoformat()
    updated = 0
    for fund_id, code in SCHEME_CODE_MAP.items():
        data = parsed.get(code)
        if not data:
            continue
        await db.nav_cache.update_one(
            {"fund_id": fund_id},
            {"$set": {
                "fund_id": fund_id,
                "scheme_code": code,
                "nav": data["nav"],
                "amfi_name": data["name"],
                "as_of_date": data["date"],
                "fetched_at": now,
            }},
            upsert=True,
        )
        updated += 1
    return {"updated": updated, "fetched_at": now, "total_schemes_in_feed": len(parsed)}


async def get_live_nav(db, fund_id: str) -> Optional[dict]:
    """Return cached live NAV doc or None."""
    return await db.nav_cache.find_one({"fund_id": fund_id}, {"_id": 0})


async def get_live_nav_map(db) -> Dict[str, float]:
    """Return {fund_id: nav} for all cached funds."""
    out: Dict[str, float] = {}
    async for doc in db.nav_cache.find({}, {"_id": 0, "fund_id": 1, "nav": 1}):
        out[doc["fund_id"]] = doc["nav"]
    return out
