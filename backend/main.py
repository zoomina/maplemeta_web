from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.home import router as home_router
from api.job import router as job_router
from api.meta import router as meta_router
from api.version import router as version_router

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Maplemeta API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(home_router, prefix="/api/home")
app.include_router(meta_router, prefix="/api/meta")
app.include_router(job_router, prefix="/api/job")
app.include_router(version_router, prefix="/api/version")


@app.get("/api/health", response_model=None)
async def health():
    return {"status": "ok"}


# Static files
_static_dir = Path(__file__).parent / "static"
if _static_dir.exists():
    _assets_dir = _static_dir / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")


@app.get("/{full_path:path}", response_model=None)
async def catch_all(full_path: str):
    if full_path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    index_html = _static_dir / "index.html"
    if index_html.exists():
        return FileResponse(str(index_html))
    return {"detail": "Frontend not built yet"}
