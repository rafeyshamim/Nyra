import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.config.logging import setup_logging
from app.database.session import init_db
from app.api.routes_health import router as health_router
from app.api.routes_whatsapp import router as whatsapp_router
from app.api.routes_telephony import router as telephony_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    setup_logging()
    logger = logging.getLogger("nyra.main")
    logger.info(f"Starting {settings.nyra_name} AI Call Assistant (Environment: {settings.app_env})...")

    await init_db()
    logger.info(f"{settings.nyra_name} startup completed.")

    yield

    # Shutdown tasks
    logger.info(f"Shutting down {settings.nyra_name}...")


app = FastAPI(
    title=f"{settings.nyra_name} — Personal AI Call Assistant",
    description=f"Local-first personal receptionist AI for {settings.owner_name}.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router)
app.include_router(whatsapp_router)
app.include_router(telephony_router)
