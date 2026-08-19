from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    for name, loader in (
        ("BM25", lambda: __import__("retrieval.bm25_index", fromlist=["load_bm25"]).load_bm25()),
        ("Dense", lambda: __import__("retrieval.dense_index", fromlist=["load_dense"]).load_dense()),
    ):
        try:
            loader()
            logger.info(f"{name} index loaded")
        except Exception as e:
            logger.warning(f"{name} index not loaded: {e}")
    yield


app = FastAPI(title="Motor Insurance Co-Pilot", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.chat import router as chat_router      # noqa: E402
from api.health import router as health_router  # noqa: E402
app.include_router(chat_router)
app.include_router(health_router)
