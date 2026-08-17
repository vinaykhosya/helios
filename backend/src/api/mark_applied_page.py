"""
backend/src/api/mark_applied_page.py

GET /mark-applied/{token}

This endpoint is embedded in the Google Sheet __helios_mark_applied_url column.
When clicked, it renders an HTML confirmation page.
It NEVER mutates application state (Invariant #7).

Flow:
  1. Validate signed token (signature + expiry)
  2. Fetch application for display (read-only)
  3. Return HTML confirmation page containing a POST form

The POST form submits to POST /api/applications/{id}/mark-applied.
"""
from __future__ import annotations
from typing import AsyncGenerator
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.core.di import DIContainer
from backend.src.repositories.application import SQLAlchemyApplicationRepository
from backend.src.services.action_token_service import ActionTokenService, TokenValidationError

router = APIRouter(tags=["Mark Applied"])


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with DIContainer.session() as session:
        yield session


@router.get("/mark-applied/{token}", response_class=HTMLResponse)
async def mark_applied_page(token: str, session: AsyncSession = Depends(get_db)):
    """Render confirmation page. Zero state mutations."""
    svc = ActionTokenService()
    try:
        decoded = svc.validate(token)
    except TokenValidationError:
        return HTMLResponse(_error_html("Invalid or expired action token."), status_code=400)

    repo = SQLAlchemyApplicationRepository(session)
    app = await repo.get_by_id(decoded.application_id)
    if not app:
        return HTMLResponse(_error_html("Application not found."), status_code=404)

    if app.status in ("submitted_manual", "applied"):
        return HTMLResponse(_already_applied_html())

    return HTMLResponse(_confirmation_html(app, token))


def _confirmation_html(app, token: str) -> str:
    label = f"Application #{app.id[:8]}"
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Confirm Application — Helios</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f1117;color:#e2e8f0;
min-height:100vh;display:flex;align-items:center;justify-content:center;padding:2rem}}
.card{{background:#1a1f2e;border:1px solid #2d3748;border-radius:16px;padding:2.5rem;max-width:480px;width:100%;
box-shadow:0 20px 60px rgba(0,0,0,.5)}}
.badge{{font-size:12px;font-weight:700;letter-spacing:.15em;color:#7c3aed;text-transform:uppercase;margin-bottom:1rem}}
h1{{font-size:1.5rem;font-weight:700;margin-bottom:.5rem}}
.sub{{color:#94a3b8;font-size:.9rem;margin-bottom:1.5rem}}
.info{{background:#0f1117;border:1px solid #2d3748;border-radius:10px;padding:1rem 1.25rem;margin-bottom:1.5rem}}
.lbl{{color:#64748b;font-size:.8rem;text-transform:uppercase;letter-spacing:.05em}}
.val{{color:#e2e8f0;font-size:1rem;font-weight:600;margin-top:2px}}
.warn{{background:#1a1000;border:1px solid #92400e;border-radius:8px;padding:.75rem 1rem;
font-size:.85rem;color:#fbbf24;margin-bottom:1.5rem}}
.btn{{display:block;width:100%;padding:.875rem;border:none;border-radius:10px;font-size:1rem;
font-weight:600;cursor:pointer;transition:all .2s}}
.btn-ok{{background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;margin-bottom:.75rem}}
.btn-ok:hover{{background:linear-gradient(135deg,#6d28d9,#5b21b6)}}
.btn-cancel{{background:transparent;border:1px solid #374151;color:#94a3b8}}
.btn-cancel:hover{{background:#1f2937}}
</style></head><body>
<div class="card">
<div class="badge">⚡ Helios</div>
<h1>Confirm Application</h1>
<p class="sub">Tell Helios you've submitted this application manually.</p>
<div class="info"><div class="lbl">Application</div><div class="val">{label}</div></div>
<div class="warn">⚠️ Only confirm if you actually submitted on the ATS portal.
This starts Gmail outcome tracking.</div>
<form method="POST" action="/api/applications/{app.id}/mark-applied">
<input type="hidden" name="token" value="{token}">
<button type="submit" class="btn btn-ok">✅ Yes, I Applied — Record It</button>
</form>
<button class="btn btn-cancel" onclick="window.close()">Cancel</button>
</div></body></html>"""


def _already_applied_html() -> str:
    return """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>Already Recorded — Helios</title>
<style>body{font-family:-apple-system,sans-serif;background:#0f1117;color:#e2e8f0;
min-height:100vh;display:flex;align-items:center;justify-content:center}
.c{text-align:center;background:#1a1f2e;border:1px solid #2d3748;border-radius:16px;padding:2.5rem;max-width:400px}
.ic{font-size:3rem;margin-bottom:1rem}h1{font-size:1.25rem;font-weight:700}
p{color:#94a3b8;margin-top:.5rem}</style></head>
<body><div class="c"><div class="ic">✅</div><h1>Already Recorded</h1>
<p>Application already marked as applied.<br>Helios is tracking responses via Gmail.</p>
</div></body></html>"""


def _error_html(reason: str = "") -> str:
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>Link Expired — Helios</title>
<style>body{{font-family:-apple-system,sans-serif;background:#0f1117;color:#e2e8f0;
min-height:100vh;display:flex;align-items:center;justify-content:center}}
.c{{text-align:center;background:#1a1f2e;border:1px solid #ef4444;border-radius:16px;padding:2.5rem;max-width:400px}}
.ic{{font-size:3rem;margin-bottom:1rem}}h1{{font-size:1.25rem;font-weight:700}}
p{{color:#94a3b8;margin-top:.5rem;font-size:.9rem}}</style></head>
<body><div class="c"><div class="ic">🔗</div><h1>Link Invalid or Expired</h1>
<p>{reason or "This Mark Applied link is no longer valid.<br>Use the Helios Web UI instead."}</p>
</div></body></html>"""
