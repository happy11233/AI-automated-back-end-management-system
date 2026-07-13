from langchain_postgres import PGVector

from app.config import settings
from app.llm import embedding_model


COLLECTION_NAME = "company_knowledge"


vector_store = PGVector(
    embeddings=embedding_model,
    collection_name=COLLECTION_NAME,
    connection=settings.vector_database_url,
    use_jsonb=True,
)