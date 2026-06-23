from fastapi import FastAPI
from .auth import router as auth_router

app = FastAPI(title="LocalGPT")

@app.get("/")
async def root():
    return {"message": "LocalGPT is running!"}

app.include_router(auth_router)
