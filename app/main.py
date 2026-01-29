from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api import routes
from app.core import config

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    config.setup_directories()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="PDF Split Worker",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(routes.router)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "pdf-split-worker"}
