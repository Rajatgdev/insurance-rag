from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://motor:motor_dev@localhost:5432/motor"
    DATABASE_URL_SYNC: str = "postgresql://motor:motor_dev@localhost:5432/motor"

    OPENAI_API_KEY: str = ""
    EMBED_MODEL: str = "text-embedding-3-small"
    EMBED_DIMS: int = 1536
    LLM_MODEL: str = "gpt-4.1"            # grounded reasoning / citations
    LLM_MODEL_FAST: str = "gpt-4o-mini"   # query expansion / persona wrap / cheap steps

    # Retrieval
    BM25_INDEX_PATH: str = "data/motor/bm25s_index"
    DENSE_INDEX_PATH: str = "data/motor/dense_index"
    RETRIEVAL_TOP_K: int = 40             # wide net; rerank shrinks it
    RERANK_TOP_K: int = 8
    EXCLUSION_TOP_K: int = 6              # separate exclusion-retrieval pass
    EMBED_CACHE_SIZE: int = 2048

    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # CORS: comma-separated exact origins; regex for previews
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    CORS_ORIGIN_REGEX: str = r"https://motor.*\.vercel\.app"

    # Abstention: below this top rerank score we tell the user we're not sure
    MIN_CONFIDENCE_SCORE: float = 0.15

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
