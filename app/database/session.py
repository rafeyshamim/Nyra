import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config.settings import settings
from app.database.models import Base

logger = logging.getLogger("nyra.database")

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db():
    """Create all SQLite database tables if they do not exist."""
    async with engine.begin() as conn:
        logger.info("Initializing SQLite database tables...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")


async def get_db_session() -> AsyncSession:
    """Dependency helper for acquiring async database sessions."""
    async with AsyncSessionLocal() as session:
        yield session
