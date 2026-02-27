"""
Last Translation Benchmark — FastAPI backend
"""

import asyncio
import hashlib
import os
import re
import secrets
import sqlite3
from datetime import date
from typing import Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DAILY_QUOTA = int(os.getenv("DAILY_QUOTA", "10"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
_HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_HERE, "data", "db.sqlite")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = _get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL DEFAULT 'annotator',
            quota_used    INTEGER DEFAULT 0,
            quota_date    TEXT    DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS suggestions (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id              INTEGER NOT NULL,
            username             TEXT NOT NULL,
            source_text          TEXT NOT NULL,
            translation          TEXT NOT NULL,
            source_lang          TEXT DEFAULT 'en',
            target_lang          TEXT DEFAULT 'de',
            verification_type    TEXT NOT NULL,
            verification_content TEXT NOT NULL,
            points               INTEGER DEFAULT -1,
            created_at           TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS tokens (
            token   TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL
        );
        """
    )
    conn.commit()

    # Migration: add verification_polarity if missing
    try:
        conn.execute(
            "ALTER TABLE suggestions ADD COLUMN verification_polarity TEXT DEFAULT 'positive'"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists

    # Seed default users only on first run
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        default_users = [
            ("senior1",     "senior123", "senior"),
            ("annotator1",  "ann123",    "annotator"),
            ("annotator2",  "ann456",    "annotator"),
        ]
        for username, password, role in default_users:
            phash = hashlib.sha256(password.encode()).hexdigest()
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, phash, role),
            )
        conn.commit()
    conn.close()


_init_db()

# ---------------------------------------------------------------------------
# App + middleware
# ---------------------------------------------------------------------------

app = FastAPI(title="Last Translation Benchmark")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

def _auth(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization[7:]
    conn = _get_db()
    row = conn.execute(
        "SELECT u.* FROM tokens t JOIN users u ON t.user_id = u.id WHERE t.token = ?",
        (token,),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid token")
    return dict(row)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class LoginReq(BaseModel):
    username: str
    password: str


class TranslateReq(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str = "de"


class VerifyReq(BaseModel):
    translation: str
    verification_type: str
    verification_content: str
    verification_polarity: str = 'positive'


class SuggestionReq(BaseModel):
    source_text: str
    translation: str
    source_lang: str = "en"
    target_lang: str = "de"
    verification_type: str
    verification_content: str
    verification_polarity: str = 'positive'


class ScoreReq(BaseModel):
    points: int


# ---------------------------------------------------------------------------
# Routes — auth
# ---------------------------------------------------------------------------

@app.post("/api/login")
async def login(req: LoginReq):
    conn = _get_db()
    phash = hashlib.sha256(req.password.encode()).hexdigest()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? AND password_hash = ?",
        (req.username, phash),
    ).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_hex(32)
    conn.execute("INSERT INTO tokens (token, user_id) VALUES (?, ?)", (token, user["id"]))
    conn.commit()
    conn.close()
    return {"token": token, "role": user["role"], "username": user["username"]}


@app.post("/api/logout")
async def logout(user=Depends(_auth), authorization: Optional[str] = Header(None)):
    conn = _get_db()
    conn.execute("DELETE FROM tokens WHERE token = ?", (authorization[7:],))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/me")
async def me(user=Depends(_auth)):
    today = date.today().isoformat()
    quota_used = user["quota_used"] if user["quota_date"] == today else 0
    conn = _get_db()
    total_points = conn.execute(
        "SELECT COALESCE(SUM(points), 0) FROM suggestions WHERE user_id = ? AND points >= 0",
        (user["id"],),
    ).fetchone()[0]
    conn.close()
    return {
        "username": user["username"],
        "role": user["role"],
        "quota_used": quota_used,
        "quota_remaining": max(0, DAILY_QUOTA - quota_used),
        "daily_quota": DAILY_QUOTA,
        "total_points": int(total_points),
    }


# ---------------------------------------------------------------------------
# Routes — translation + verification
# ---------------------------------------------------------------------------

async def _call_mymemory(
    client: httpx.AsyncClient, text: str, src: str, tgt: str
) -> dict:
    try:
        resp = await client.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": f"{src}|{tgt}"},
            timeout=10,
        )
        data = resp.json()
        if data.get("responseStatus") == 200:
            return {"api": "MyMemory", "translation": data["responseData"]["translatedText"], "error": None}
        return {"api": "MyMemory", "translation": None, "error": "API returned an error"}
    except Exception as exc:
        return {"api": "MyMemory", "translation": None, "error": str(exc)}


async def _call_libretranslate(
    client: httpx.AsyncClient, text: str, src: str, tgt: str
) -> dict:
    try:
        resp = await client.post(
            "https://translate.argosopentech.com/translate",
            json={"q": text, "source": src, "target": tgt, "format": "text"},
            timeout=10,
        )
        data = resp.json()
        if "translatedText" in data:
            return {"api": "LibreTranslate", "translation": data["translatedText"], "error": None}
        return {"api": "LibreTranslate", "translation": None, "error": data.get("error", "API error")}
    except Exception as exc:
        return {"api": "LibreTranslate", "translation": None, "error": str(exc)}


@app.post("/api/translate")
async def translate(req: TranslateReq, user=Depends(_auth)):
    if user["role"] != "annotator":
        raise HTTPException(status_code=403, detail="Only annotators can use translation quota")

    today = date.today().isoformat()
    conn = _get_db()
    row = conn.execute(
        "SELECT quota_used, quota_date FROM users WHERE id = ?", (user["id"],)
    ).fetchone()
    quota_used = row["quota_used"] if row["quota_date"] == today else 0

    if quota_used >= DAILY_QUOTA:
        conn.close()
        raise HTTPException(status_code=429, detail="Daily quota exceeded")

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            _call_mymemory(client, req.text, req.source_lang, req.target_lang),
            _call_libretranslate(client, req.text, req.source_lang, req.target_lang),
        )

    conn.execute(
        "UPDATE users SET quota_used = ?, quota_date = ? WHERE id = ?",
        (quota_used + 1, today, user["id"]),
    )
    conn.commit()
    conn.close()
    return {"results": list(results), "quota_remaining": DAILY_QUOTA - quota_used - 1}


@app.post("/api/verify")
async def verify(req: VerifyReq, user=Depends(_auth)):
    if req.verification_type == "regex":
        try:
            matched = bool(re.search(req.verification_content, req.translation, re.IGNORECASE))
        except re.error as exc:
            raise HTTPException(status_code=400, detail=f"Invalid regex: {exc}") from exc
        if req.verification_polarity == "negative":
            verified = not matched
            detail = "not matched (passes)" if verified else "matched (fails)"
        else:
            verified = matched
            detail = "matched" if verified else "no match"
        return {"verified": verified, "detail": detail}

    if req.verification_type == "llm":
        if not OPENAI_API_KEY:
            return {"verified": True, "detail": "LLM verification skipped (no API key configured)"}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You verify if a translation satisfies a criterion. Reply only YES or NO.",
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"Criterion: {req.verification_content}\n\n"
                                    f"Translation to verify: {req.translation}"
                                ),
                            },
                        ],
                        "max_tokens": 5,
                    },
                    timeout=15,
                )
            answer = resp.json()["choices"][0]["message"]["content"].strip().upper()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"LLM API error: {exc}") from exc
        return {"verified": "YES" in answer, "detail": f"LLM: {answer}"}

    raise HTTPException(status_code=400, detail="verification_type must be 'regex' or 'llm'")


# ---------------------------------------------------------------------------
# Routes — suggestions
# ---------------------------------------------------------------------------

@app.post("/api/suggestions")
async def create_suggestion(req: SuggestionReq, user=Depends(_auth)):
    if user["role"] != "annotator":
        raise HTTPException(status_code=403, detail="Only annotators can submit suggestions")
    conn = _get_db()
    conn.execute(
        """INSERT INTO suggestions
           (user_id, username, source_text, translation, source_lang, target_lang,
            verification_type, verification_content, verification_polarity)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user["id"], user["username"],
            req.source_text, req.translation,
            req.source_lang, req.target_lang,
            req.verification_type, req.verification_content,
            req.verification_polarity,
        ),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/suggestions")
async def get_suggestions(user=Depends(_auth)):
    conn = _get_db()
    if user["role"] == "senior":
        rows = conn.execute(
            "SELECT * FROM suggestions ORDER BY points ASC, created_at DESC"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM suggestions WHERE user_id = ? ORDER BY created_at DESC",
            (user["id"],),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/suggestions/{sid}/score")
async def score_suggestion(sid: int, req: ScoreReq, user=Depends(_auth)):
    if user["role"] != "senior":
        raise HTTPException(status_code=403, detail="Only senior users can score suggestions")
    if req.points not in (0, 1, 2, 3):
        raise HTTPException(status_code=400, detail="Points must be 0, 1, 2, or 3")
    conn = _get_db()
    result = conn.execute(
        "UPDATE suggestions SET points = ? WHERE id = ?", (req.points, sid)
    )
    if result.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Suggestion not found")
    conn.commit()
    conn.close()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Static frontend — must be mounted last
# ---------------------------------------------------------------------------

app.mount(
    "/",
    StaticFiles(directory=os.path.join(_HERE, "static"), html=True),
    name="static",
)
