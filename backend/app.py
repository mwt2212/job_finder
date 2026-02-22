from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.api.router import api_router
from backend.db import init_db


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    print(f"Backend loaded from {__file__}", flush=True)
    init_db()
    yield


app = FastAPI(title="Job Finder Dashboard", lifespan=_lifespan)
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    print(f"{request.method} {request.url.path} -> {response.status_code}", flush=True)
    return response
