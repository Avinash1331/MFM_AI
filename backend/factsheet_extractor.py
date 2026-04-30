"""Factsheet PDF extraction via Gemini (file attachments only supported on Gemini)."""
import json
import logging
import os
import re
from typing import Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType

log = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a mutual fund factsheet parser. Read the attached factsheet PDF and return ONLY a JSON object (no markdown fences) with this exact shape:

{
  "fund_name": "string",
  "amc": "string",
  "category": "string",
  "manager": "string",
  "nav": number,
  "aum_cr": number,
  "expense_ratio": number,
  "objective": "string (one paragraph)",
  "as_of_date": "string (YYYY-MM-DD or month-year)",
  "top_holdings": [
    {"stock": "Company name", "sector": "Sector name", "weight": number_in_percent}
  ],
  "sector_allocation": [
    {"sector": "Sector name", "weight": number_in_percent}
  ],
  "asset_allocation": {"equity": number, "debt": number, "cash": number}
}

Rules:
- Extract the TOP 10 stock holdings.
- Weights must be numbers in percent (e.g. 8.4 — not "8.4%" and not 0.084).
- If a field is unavailable, use null. Never invent data.
- Respond with ONLY the JSON object."""


def _extract_json(text: str) -> dict:
    """Strip markdown fences and parse JSON. Robust to ```json blocks."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        # take from first { to last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]
    return json.loads(text)


async def extract_factsheet(pdf_path: str, fund_id: str) -> dict:
    """Send PDF to Gemini 3 Pro and return parsed JSON."""
    api_key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY not configured")
    chat = LlmChat(
        api_key=api_key,
        session_id=f"factsheet-{fund_id}",
        system_message="You extract structured data from mutual fund factsheets. Reply with JSON only.",
    ).with_model("gemini", "gemini-3.1-pro-preview")
    pdf = FileContentWithMimeType(file_path=pdf_path, mime_type="application/pdf")
    msg = UserMessage(text=EXTRACTION_PROMPT, file_contents=[pdf])
    response = await chat.send_message(msg)
    text = response if isinstance(response, str) else str(response)
    try:
        data = _extract_json(text)
    except Exception as e:
        log.error("JSON parse failed. Raw: %s", text[:500])
        raise RuntimeError(f"Could not parse extraction JSON: {e}")
    return data


def diff_factsheet(old: Optional[dict], new: dict) -> list:
    """Compare an old factsheet snapshot vs new and yield change descriptors."""
    if not old:
        return []
    changes = []
    for field, label in [
        ("manager", "Fund Manager Change"),
        ("category", "SEBI Category Reclassified"),
        ("objective", "Investment Objective Amended"),
        ("fund_name", "Fund Name Changed"),
    ]:
        ov = (old.get(field) or "").strip() if isinstance(old.get(field), str) else old.get(field)
        nv = (new.get(field) or "").strip() if isinstance(new.get(field), str) else new.get(field)
        if ov and nv and ov != nv:
            changes.append({
                "type": {
                    "manager": "manager_change",
                    "category": "category_reclassification",
                    "objective": "objective_change",
                    "fund_name": "name_change",
                }[field],
                "title": label,
                "message": f"From '{ov}' to '{nv}'",
                "severity": "high" if field in ("manager", "category") else "medium",
            })
    # Asset-allocation drift
    oa = old.get("asset_allocation") or {}
    na = new.get("asset_allocation") or {}
    for k in ("equity", "debt", "cash"):
        ov, nv = oa.get(k), na.get(k)
        if ov is not None and nv is not None and abs((nv or 0) - (ov or 0)) >= 3.0:
            changes.append({
                "type": "asset_allocation",
                "title": "Asset Allocation Shift",
                "message": f"{k.capitalize()} moved from {ov:.1f}% to {nv:.1f}% ({(nv-ov):+.1f}%)",
                "severity": "high",
            })
            break
    return changes
