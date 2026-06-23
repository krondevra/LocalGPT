from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from .auth import router as auth_router
from .api import router as api_router

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="LocalGPT")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/app", include_in_schema=False)
async def serve_app():
    return FileResponse(FRONTEND_DIR / "app.html")

app.include_router(auth_router)
app.include_router(api_router)
