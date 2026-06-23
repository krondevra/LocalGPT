from fastapi import FastAPI

app = FastAPI(title="LocalGPT")

@app.get("/")
async def root():
    return {"message": "LocalGPT is running!"}
