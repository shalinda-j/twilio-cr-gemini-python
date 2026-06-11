# main.py - FastAPI dashboard: auth, REST API, live WebSocket, and serves the frontend.
import datetime
import os
from contextlib import asynccontextmanager

from fastapi import (
    Depends,
    FastAPI,
    Form,
    Header,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from .auth import (
    create_access_token,
    decode_token,
    get_current_user,
    verify_password,
)
from .database import get_db, init_db
from .events import hub
from .models import (
    Call,
    Company,
    KnowledgeEntry,
    Message,
    PhoneNumber,
    Provider,
    Setting,
    User,
)
from .seed import seed_initial_data

INGEST_TOKEN = os.getenv("INGEST_TOKEN", "CHANGE_ME_ingest_token")
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_initial_data()
    yield


app = FastAPI(title="Voice Assistant Dashboard", lifespan=lifespan)


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------
class LoginBody(BaseModel):
    email: str
    password: str


class IngestEvent(BaseModel):
    type: str  # call_started | message | call_ended
    call_uuid: str
    caller: str | None = None
    direction: str | None = "inbound"
    language: str | None = None
    did: str | None = None        # number the call came in on (for tenant routing)
    role: str | None = None       # for message events
    text: str | None = None       # for message events
    status: str | None = None     # for call_ended
    duration_seconds: int | None = None


class CompanyBody(BaseModel):
    name: str
    system_prompt: str | None = None


class NumberBody(BaseModel):
    number: str
    label: str | None = None
    provider: str | None = None
    company_id: int | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    system_prompt: str | None = None


class ProviderBody(BaseModel):
    name: str
    kind: str | None = "sip"
    host: str | None = None
    username: str | None = None
    password: str | None = None
    notes: str | None = None


class SettingBody(BaseModel):
    key: str
    value: str | None = None


class KnowledgeBody(BaseModel):
    title: str
    content: str


def require_admin(user: User):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


def _resolve_company_for_did(db: Session, did: str | None) -> int | None:
    """Map an inbound DID to the owning company; fall back to the first company."""
    if did:
        pn = db.query(PhoneNumber).filter(PhoneNumber.number == did).first()
        if pn:
            return pn.company_id
    first = db.query(Company).order_by(Company.id).first()
    return first.id if first else None


# -----------------------------------------------------------------------------
# Auth
# -----------------------------------------------------------------------------
@app.post("/api/auth/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower().strip()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong email or password")
    return {"access_token": create_access_token(user), "token_type": "bearer"}


@app.get("/api/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == user.company_id).first()
    return {
        "email": user.email,
        "role": user.role,
        "company": {"id": company.id, "name": company.name, "system_prompt": company.system_prompt},
    }


# -----------------------------------------------------------------------------
# Data API (always scoped to the caller's company)
# -----------------------------------------------------------------------------
@app.get("/api/stats")
def stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = user.company_id
    today = datetime.datetime.now(datetime.timezone.utc).date()
    base = db.query(Call).filter(Call.company_id == cid)

    total = base.count()
    active = base.filter(Call.status == "in_progress").count()
    today_calls = base.filter(func.date(Call.started_at) == today).count()
    total_seconds = (
        db.query(func.coalesce(func.sum(Call.duration_seconds), 0))
        .filter(Call.company_id == cid)
        .scalar()
        or 0
    )

    # last 7 days counts for the chart
    series = []
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        count = base.filter(func.date(Call.started_at) == day).count()
        series.append({"date": day.isoformat(), "count": count})

    return {
        "total_calls": total,
        "active_calls": active,
        "today_calls": today_calls,
        "total_minutes": round(total_seconds / 60, 1),
        "series": series,
    }


@app.get("/api/calls")
def list_calls(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = (
        db.query(Call)
        .filter(Call.company_id == user.company_id)
        .order_by(Call.started_at.desc())
    )
    rows = q.offset(offset).limit(min(limit, 200)).all()
    return [
        {
            "id": c.id,
            "call_uuid": c.call_uuid,
            "caller": c.caller,
            "direction": c.direction,
            "language": c.language,
            "status": c.status,
            "started_at": c.started_at.isoformat() if c.started_at else None,
            "duration_seconds": c.duration_seconds,
            "turns": c.turns,
        }
        for c in rows
    ]


@app.get("/api/calls/{call_id}")
def call_detail(
    call_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = (
        db.query(Call)
        .filter(Call.id == call_id, Call.company_id == user.company_id)
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Call not found")
    return {
        "id": c.id,
        "caller": c.caller,
        "status": c.status,
        "language": c.language,
        "started_at": c.started_at.isoformat() if c.started_at else None,
        "duration_seconds": c.duration_seconds,
        "messages": [
            {"role": m.role, "text": m.text, "language": m.language} for m in c.messages
        ],
    }


@app.get("/api/numbers")
def list_numbers(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(PhoneNumber).filter(PhoneNumber.company_id == user.company_id).all()
    )
    return [
        {
            "id": n.id,
            "number": n.number,
            "label": n.label,
            "provider": n.provider,
            "active": n.active,
        }
        for n in rows
    ]


# -----------------------------------------------------------------------------
# Admin: manage companies and phone numbers (multi-tenant setup)
# -----------------------------------------------------------------------------
@app.post("/api/companies")
def create_company(
    body: CompanyBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(user)
    company = Company(name=body.name, system_prompt=body.system_prompt)
    db.add(company)
    db.commit()
    db.refresh(company)
    return {"id": company.id, "name": company.name}


@app.get("/api/companies")
def list_companies(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(user)
    return [{"id": c.id, "name": c.name} for c in db.query(Company).all()]


@app.post("/api/numbers")
def create_number(
    body: NumberBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(user)
    company_id = body.company_id or user.company_id
    n = PhoneNumber(
        company_id=company_id,
        number=body.number.strip(),
        label=body.label,
        provider=body.provider,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return {"id": n.id, "number": n.number, "company_id": n.company_id}


@app.delete("/api/numbers/{number_id}")
def delete_number(number_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(user)
    n = db.query(PhoneNumber).filter(
        PhoneNumber.id == number_id, PhoneNumber.company_id == user.company_id
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(n)
    db.commit()
    return {"ok": True}


@app.patch("/api/company")
def update_company(body: CompanyUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(user)
    company = db.query(Company).filter(Company.id == user.company_id).first()
    if body.name is not None:
        company.name = body.name
    if body.system_prompt is not None:
        company.system_prompt = body.system_prompt
    db.commit()
    return {"id": company.id, "name": company.name, "system_prompt": company.system_prompt}


# ---- SIP providers ----------------------------------------------------------
@app.get("/api/providers")
def list_providers(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Provider).filter(Provider.company_id == user.company_id).all()
    return [
        {"id": p.id, "name": p.name, "kind": p.kind, "host": p.host,
         "username": p.username, "notes": p.notes, "active": p.active}
        for p in rows
    ]


@app.post("/api/providers")
def create_provider(body: ProviderBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(user)
    p = Provider(company_id=user.company_id, name=body.name, kind=body.kind or "sip",
                 host=body.host, username=body.username, password=body.password, notes=body.notes)
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "name": p.name}


@app.delete("/api/providers/{provider_id}")
def delete_provider(provider_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(user)
    p = db.query(Provider).filter(Provider.id == provider_id, Provider.company_id == user.company_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(p)
    db.commit()
    return {"ok": True}


# ---- Settings (TTS, API keys, webhooks) -------------------------------------
@app.get("/api/settings")
def get_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Setting).filter(Setting.company_id == user.company_id).all()
    return {s.key: s.value for s in rows}


@app.put("/api/settings")
def put_setting(body: SettingBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(user)
    s = db.query(Setting).filter(
        Setting.company_id == user.company_id, Setting.key == body.key
    ).first()
    if s:
        s.value = body.value
    else:
        s = Setting(company_id=user.company_id, key=body.key, value=body.value)
        db.add(s)
    db.commit()
    return {"key": body.key, "value": body.value}


# ---- Knowledge base (dataset) ----------------------------------------------
@app.get("/api/knowledge")
def list_knowledge(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(KnowledgeEntry).filter(KnowledgeEntry.company_id == user.company_id).all()
    return [{"id": k.id, "title": k.title, "content": k.content} for k in rows]


@app.post("/api/knowledge")
def create_knowledge(body: KnowledgeBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(user)
    k = KnowledgeEntry(company_id=user.company_id, title=body.title, content=body.content)
    db.add(k)
    db.commit()
    db.refresh(k)
    return {"id": k.id, "title": k.title}


@app.delete("/api/knowledge/{entry_id}")
def delete_knowledge(entry_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(user)
    k = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.id == entry_id, KnowledgeEntry.company_id == user.company_id
    ).first()
    if not k:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(k)
    db.commit()
    return {"ok": True}


# -----------------------------------------------------------------------------
# Internal: voice/telephony servers post here (server-to-server, token-protected).
# -----------------------------------------------------------------------------
@app.post("/api/internal/route")
async def route_call(
    call_uuid: str = Form(...),
    did: str = Form(default=""),
    caller: str = Form(default=""),
    token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    """Asterisk registers a call->DID mapping at answer time so we can attribute
    the call to the right company before the voice server starts reporting."""
    if token != INGEST_TOKEN:
        raise HTTPException(status_code=403, detail="Bad ingest token")
    cid = _resolve_company_for_did(db, did or None)
    if cid is None:
        raise HTTPException(status_code=400, detail="No company configured")
    call = db.query(Call).filter(Call.call_uuid == call_uuid).first()
    if not call:
        call = Call(
            company_id=cid,
            call_uuid=call_uuid,
            caller=caller or None,
            direction="inbound",
            status="in_progress",
        )
        db.add(call)
        db.commit()
        db.refresh(call)
    await hub.broadcast(cid, {"event": "call_started", "call": _call_brief(call)})
    return {"ok": True, "company_id": cid}


@app.post("/api/internal/ingest")
async def ingest(
    event: IngestEvent,
    x_ingest_token: str = Header(default=""),
    db: Session = Depends(get_db),
):
    if x_ingest_token != INGEST_TOKEN:
        raise HTTPException(status_code=403, detail="Bad ingest token")

    # A call may already exist (pre-routed by Asterisk to the right company).
    call = db.query(Call).filter(Call.call_uuid == event.call_uuid).first()
    cid = call.company_id if call else _resolve_company_for_did(db, event.did)
    if cid is None:
        raise HTTPException(status_code=400, detail="No company configured")

    if event.type == "call_started":
        if not call:
            call = Call(
                company_id=cid,
                call_uuid=event.call_uuid,
                caller=event.caller,
                direction=event.direction or "inbound",
                status="in_progress",
            )
            db.add(call)
            db.commit()
            db.refresh(call)
        await hub.broadcast(cid, {"event": "call_started", "call": _call_brief(call)})

    elif event.type == "message":
        if call:
            db.add(
                Message(
                    call_id=call.id,
                    role=event.role or "user",
                    text=event.text or "",
                    language=event.language,
                )
            )
            call.turns = (call.turns or 0) + 1
            if event.language:
                call.language = event.language
            db.commit()
            await hub.broadcast(
                cid,
                {
                    "event": "message",
                    "call_id": call.id,
                    "role": event.role,
                    "text": event.text,
                    "language": event.language,
                },
            )

    elif event.type == "call_ended":
        if call:
            call.status = event.status or "completed"
            call.ended_at = datetime.datetime.now(datetime.timezone.utc)
            if event.duration_seconds is not None:
                call.duration_seconds = event.duration_seconds
            db.commit()
            await hub.broadcast(cid, {"event": "call_ended", "call": _call_brief(call)})

    return {"ok": True}


def _call_brief(c: Call) -> dict:
    return {
        "id": c.id,
        "call_uuid": c.call_uuid,
        "caller": c.caller,
        "status": c.status,
        "language": c.language,
        "started_at": c.started_at.isoformat() if c.started_at else None,
        "duration_seconds": c.duration_seconds,
        "turns": c.turns,
    }


# -----------------------------------------------------------------------------
# Live updates WebSocket (token passed as query param)
# -----------------------------------------------------------------------------
@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket, token: str = ""):
    try:
        payload = decode_token(token)
        company_id = int(payload["company_id"])
    except Exception:
        await websocket.close(code=4401)
        return

    await hub.connect(company_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keepalive / ignore
    except WebSocketDisconnect:
        await hub.disconnect(company_id, websocket)
    except Exception:
        await hub.disconnect(company_id, websocket)


@app.get("/health")
def health():
    return {"ok": True}


# -----------------------------------------------------------------------------
# Serve the frontend (mounted last so /api/* wins)
# -----------------------------------------------------------------------------
@app.get("/")
def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
