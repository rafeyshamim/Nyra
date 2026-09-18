import logging
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.llm.client import OllamaLLMProvider
from app.config.settings import settings

logger = logging.getLogger("nyra.api.health")
router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db_session)):
    """Health check endpoint checking DB and Ollama connectivity."""
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"

    ollama_status = "healthy"
    try:
        llm = OllamaLLMProvider()
        res = await llm.generate_response(
            messages=[{"role": "user", "content": "ping"}],
            system_prompt="Reply pong",
        )
        if not res:
            ollama_status = "unhealthy"
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        ollama_status = "unhealthy"

    return {
        "status": "online",
        "nyra_name": settings.nyra_name,
        "owner_name": settings.owner_name,
        "environment": settings.app_env,
        "components": {
            "database": db_status,
            "ollama_llm": ollama_status,
            "model": settings.ollama_model,
        },
    }
