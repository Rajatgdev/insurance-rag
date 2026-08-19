from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from contextlib import asynccontextmanager
from config import settings
import ssl as ssl_lib

db_url = settings.DATABASE_URL
connect_args: dict = {}

# Neon on Railway (port 5432 open) needs SSL
if "neon.tech" in db_url:
    ssl_ctx = ssl_lib.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl_lib.CERT_NONE
    connect_args["ssl"] = ssl_ctx
    # strip ?ssl=require — asyncpg uses the ssl object instead
    for param in ["?ssl=require", "&ssl=require", "?sslmode=require", "&sslmode=require"]:
        db_url = db_url.replace(param, "")

engine = create_async_engine(
    db_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def async_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise