from fastapi import FastAPI
from .auth import router as auth_router
from .api import router as api_router

app = FastAPI(title="LocalGPT")

@app.get("/")
async def root():
    return {"message": "LocalGPT is running!"}

app.include_router(auth_router)
app.include_router(api_router)
