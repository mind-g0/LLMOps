import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import engine
from app.gateway import router as gateway_router
from app.models import Base
from app.reviews import router as reviews_router

load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        domain.strip()
        for domain in os.environ["CORS_ALLOW_ORIGINS"].split(",")
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

app.include_router(gateway_router)
app.include_router(reviews_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
