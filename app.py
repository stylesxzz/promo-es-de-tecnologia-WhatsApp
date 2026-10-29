import os
import sqlite3
import secrets
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Optional

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl

DB_PATH = os.getenv("DATABASE_PATH", "/data/promos.db")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change-me")
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "15"))
SEARCH_TERMS = [x.strip() for x in os.getenv("SEARCH_TERMS", "smartphone,f smartphone,notebook,ssd,memoria ram,monitor,gpu,teclado mecanico,mouse gamer,fone bluetooth,roteador").split(",") if x.strip()]
SEARCH_INTERVAL_MINUTES = max(30, int(os.getenv("SEARCH_INTERVAL_MINUTES", "180")))
scheduler = AsyncIOScheduler(timezone=os.getenv("TZ", "America/Sao_Paulo"))
app = FastAPI(title="Promo Tech WhatsApp", version="1.0.0")

@contextmanager
def db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            price REAL,
            currency TEXT,
            permalink TEXT NOT NULL,
            image TEXT,
            affiliate_url TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            published_at TEXT
        )""")

def admin(token: Optional[str]):
    if not token or not secrets.compare_digest(token, ADMIN_TOKEN):
        raise HTTPException(status_code=401, detail="Token administrativo inválido")

async def search_marketplace():
    added = 0
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "PromoTechBot/1.0"}) as client:
        for term in SEARCH_TERMS:
            try:
                response = await client.get("https://api.mercadolibre.com/sites/MLB/search", params={"q": term, "limit": 25, "sort": "price_asc"})
                response.raise_for_status()
                for item in response.json().get("results", []):
                    item_id = str(item.get("id", ""))
                    title = item.get("title")
                    permalink = item.get("permalink")
                    price = item.get("price")
                    if not item_id or not title or not permalink or not isinstance(price, (int, float)):
                        continue
                    with db() as conn:
                        cur = conn.execute("""INSERT OR IGNORE INTO offers
                            (item_id,title,price,currency,permalink,image,created_at)
                            VALUES (?,?,?,?,?,?,?)""",
                            (item_id, title, price, item.get("currency_id", "BRL"), permalink,
                             item.get("thumbnail"), datetime.now(timezone.utc).isoformat()))
                        added += cur.rowcount
            except (httpx.HTTPError, ValueError):
                continue
    return added

@app.on_event("startup")
async def startup():
    init_db()
    if os.getenv("ENABLE_SCHEDULER", "true").lower() == "true":
        scheduler.add_job(search_marketplace, "interval", minutes=SEARCH_INTERVAL_MINUTES, id="market-scan", replace_existing=True, max_instances=1)
        scheduler.start()

@app.on_event("shutdown")
async def shutdown():
    if scheduler.running:
        scheduler.shutdown()

@app.get("/api/health")
def health():
    return {"ok": True, "service": "promo-tech-whatsapp", "publishing": "manual_channel_review"}

@app.get("/", response_class=HTMLResponse)
def home():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()

@app.get("/api/offers")
def offers(x_admin_token: Optional[str] = Header(default=None)):
    admin(x_admin_token)
    with db() as conn:
        rows = conn.execute("SELECT * FROM offers ORDER BY created_at DESC LIMIT 200").fetchall()
        return [dict(r) for r in rows]

@app.post("/api/scan")
async def scan(x_admin_token: Optional[str] = Header(default=None)):
    admin(x_admin_token)
    count = await search_marketplace()
    return {"added": count, "daily_limit": DAILY_LIMIT}

class AffiliateLink(BaseModel):
    url: HttpUrl

@app.post("/api/offers/{offer_id}/affiliate-link")
def affiliate_link(offer_id: int, body: AffiliateLink, x_admin_token: Optional[str] = Header(default=None)):
    admin(x_admin_token)
    url = str(body.url)
    if "mercadolivre.com" not in url and "meli.la" not in url:
        raise HTTPException(status_code=400, detail="Use um link gerado pelo Portal de Afiliados do Mercado Livre")
    with db() as conn:
        cur = conn.execute("UPDATE offers SET affiliate_url=? WHERE id=?", (url, offer_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Oferta não encontrada")
    return {"ok": True}

class StatusUpdate(BaseModel):
    status: str

@app.post("/api/offers/{offer_id}/status")
def update_status(offer_id: int, body: StatusUpdate, x_admin_token: Optional[str] = Header(default=None)):
    admin(x_admin_token)
    if body.status not in {"pending", "approved", "published", "rejected"}:
        raise HTTPException(status_code=400, detail="Status inválido")
    with db() as conn:
        cur = conn.execute("UPDATE offers SET status=?, published_at=? WHERE id=?",
                           (body.status, datetime.now(timezone.utc).isoformat() if body.status == "published" else None, offer_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Oferta não encontrada")
    return {"ok": True, "status": body.status}

@app.get("/api/stats")
def stats(x_admin_token: Optional[str] = Header(default=None)):
    admin(x_admin_token)
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM offers WHERE status='pending'").fetchone()[0]
        published = conn.execute("SELECT COUNT(*) FROM offers WHERE status='published' AND date(published_at)=date('now')").fetchone()[0]
    return {"total": total, "pending": pending, "published_today": published, "daily_target": DAILY_LIMIT}
