"""Resend email service wrapper + HTML templates for alerts/digests."""
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

import resend

log = logging.getLogger(__name__)

resend.api_key = os.environ.get("RESEND_API_KEY", "")
SENDER = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")

SEV_COLOR = {"high": "#ef4444", "medium": "#f59e0b", "low": "#737373"}


async def send_email(to: str, subject: str, html: str) -> dict:
    if not resend.api_key:
        log.warning("RESEND_API_KEY missing — not sending email to %s", to)
        return {"ok": False, "error": "RESEND_API_KEY not set"}
    params = {"from": SENDER, "to": [to], "subject": subject, "html": html}
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        return {"ok": True, "id": result.get("id")}
    except Exception as e:
        log.exception("Resend send failed")
        return {"ok": False, "error": str(e)}


def _shell(title: str, inner: str) -> str:
    return f"""<!doctype html>
<html><body style="margin:0;background:#0a0a0c;font-family:-apple-system,'Segoe UI',sans-serif;color:#fafafa;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0c;padding:24px 0;">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#101013;border:1px solid #1f1f24;">
        <tr><td style="padding:18px 24px;border-bottom:1px solid #1f1f24;">
          <span style="color:#22c55e;font-weight:900;letter-spacing:-0.04em;">MF.TERMINAL</span>
          <span style="color:#737373;font-size:11px;text-transform:uppercase;letter-spacing:0.18em;margin-left:12px;">// {title}</span>
        </td></tr>
        <tr><td style="padding:24px;">{inner}</td></tr>
        <tr><td style="padding:14px 24px;border-top:1px solid #1f1f24;color:#737373;font-size:11px;">
          Sent {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')} · You can disable this in Settings.
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def render_alert_email(alert: dict) -> str:
    color = SEV_COLOR.get(alert.get("severity", "low"), "#737373")
    inner = f"""
      <div style="border-left:3px solid {color};padding:6px 12px;margin-bottom:18px;">
        <div style="color:#737373;font-size:11px;text-transform:uppercase;letter-spacing:0.2em;">
          {alert.get('type','').replace('_',' ')} · {alert.get('severity','').upper()}
        </div>
        <div style="font-size:18px;font-weight:700;margin-top:4px;">{alert.get('title','')}</div>
        <div style="color:#a1a1aa;font-size:13px;margin-top:2px;">{alert.get('fund_name','')}</div>
      </div>
      <div style="font-size:14px;line-height:1.55;color:#e4e4e7;">{alert.get('message','')}</div>
    """
    return _shell("New Alert", inner)


def render_digest_email(alerts: List[dict]) -> str:
    if not alerts:
        rows = '<div style="color:#737373;font-size:13px;">No active alerts.</div>'
    else:
        rows = ""
        for a in alerts:
            color = SEV_COLOR.get(a.get("severity", "low"), "#737373")
            rows += f"""
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:14px;border:1px solid #1f1f24;">
                <tr>
                  <td width="3" style="background:{color};"></td>
                  <td style="padding:10px 14px;">
                    <div style="color:#737373;font-size:10px;text-transform:uppercase;letter-spacing:0.2em;">
                      {a.get('type','').replace('_',' ')}
                    </div>
                    <div style="font-size:15px;font-weight:600;margin-top:3px;">{a.get('title','')}</div>
                    <div style="color:#a1a1aa;font-size:12px;margin-top:2px;">{a.get('fund_name','')}</div>
                    <div style="color:#e4e4e7;font-size:13px;margin-top:6px;line-height:1.5;">{a.get('message','')}</div>
                  </td>
                </tr>
              </table>
            """
    inner = f"""
      <div style="font-size:22px;font-weight:900;letter-spacing:-0.03em;margin-bottom:6px;">Portfolio Watchdog Digest</div>
      <div style="color:#a1a1aa;font-size:13px;margin-bottom:18px;">{len(alerts)} active signal(s) across your schemes.</div>
      {rows}
    """
    return _shell("Daily Digest", inner)
