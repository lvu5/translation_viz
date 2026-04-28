"""
Last Translation Benchmark — FastAPI backend
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .db import db_state
from .routers import router

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

app.include_router(router)


@app.on_event("startup")
def _print_magic_links() -> None:
    print("\n=== Magic login links ===")
    host_public = os.getenv("HOST_PUBLIC")
    for user in db_state["users"]:
        print(
            f"  {user['username']:12s}  {host_public}/?user={user['username']}&token={user['magic_token']}"
        )
    print("=========================\n")


# ---------------------------------------------------------------------------
# Static frontend — must be mounted last
# ---------------------------------------------------------------------------

app.mount(
    "/",
    StaticFiles(
        directory=os.path.dirname(os.path.abspath(__file__)) + "/static", html=True
    ),
    name="static",
)
