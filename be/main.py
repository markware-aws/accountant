from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routers import chat, ingest, auth, history, mydata

app = FastAPI(title="accountantAI API", version="0.1.0")

import os

ALLOWED_ORIGINS = (
    ["*"]
    if os.getenv("ENVIRONMENT", "dev") == "dev"
    else [
        "https://yourdomain.com",
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(history.router, prefix="/history", tags=["history"])
app.include_router(mydata.router, prefix="/mydata", tags=["mydata"])


@app.get("/health")
async def health():
    return {"status": "ok"}
