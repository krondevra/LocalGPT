from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .auth import router as auth_router
from .api import router as api_router

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(
    title="LocalGPT",
    description="LocalGPT is a local AI chat web application with authentication, chat history, admin tools, responsive UI and SEO basics.",
    version="1.0.0",
)

# Serve static frontend files from the same FastAPI app.
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add simple security headers that are easy to explain in a student project."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/app", include_in_schema=False)
async def serve_app():
    return FileResponse(FRONTEND_DIR / "app.html")


@app.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    return FileResponse(FRONTEND_DIR / "robots.txt", media_type="text/plain")


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml():
    return FileResponse(FRONTEND_DIR / "sitemap.xml", media_type="application/xml")


@app.get("/health")
def health_check():
    """Small endpoint for demonstration and testing."""
    return {"status": "ok", "service": "LocalGPT"}


app.include_router(auth_router)
app.include_router(api_router)
