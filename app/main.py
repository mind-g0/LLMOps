import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.gateway import router as gateway_router

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        domain.strip()
        for domain in os.getenv("CORS_ALLOW_ORIGINS", "").split(",")
        if domain.strip()
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

app.include_router(gateway_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
