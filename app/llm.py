from collections import OrderedDict
from hashlib import sha256
from threading import Lock
import time

from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config import settings


chat_model = ChatOpenAI(
    model=settings.bailian_chat_model,
    api_key=settings.dashscope_api_key,
    base_url=settings.bailian_base_url,
    temperature=0.2,
    timeout=settings.bailian_request_timeout_seconds,
    max_retries=settings.bailian_max_retries,
)


fast_chat_model = ChatOpenAI(
    model=settings.bailian_fast_chat_model or settings.bailian_chat_model,
    api_key=settings.dashscope_api_key,
    base_url=settings.bailian_base_url,
    temperature=0.2,
    max_tokens=settings.bailian_fast_chat_max_tokens,
    timeout=settings.bailian_request_timeout_seconds,
    max_retries=settings.bailian_max_retries,
)


_remote_embedding_model = OpenAIEmbeddings(
    model=settings.bailian_embedding_model,
    api_key=settings.dashscope_api_key,
    base_url=settings.bailian_base_url,
    dimensions=settings.bailian_embedding_dimensions,
    check_embedding_ctx_length=False,
)


class CachedEmbeddings(Embeddings):
    """Cache query embeddings briefly without retaining the raw query text."""

    def __init__(self, inner):
        self.inner = inner
        self._cache: OrderedDict[str, tuple[float, list[float]]] = OrderedDict()
        self._lock = Lock()

    def embed_query(self, text: str) -> list[float]:
        if settings.rag_embedding_cache_ttl_seconds <= 0 or settings.rag_embedding_cache_max_entries <= 0:
            return self.inner.embed_query(text)
        key = sha256(text.encode("utf-8")).hexdigest()
        now = time.monotonic()
        with self._lock:
            cached = self._cache.get(key)
            if cached and now - cached[0] <= settings.rag_embedding_cache_ttl_seconds:
                self._cache.move_to_end(key)
                return list(cached[1])
            if cached:
                self._cache.pop(key, None)

        vector = self.inner.embed_query(text)
        with self._lock:
            self._cache[key] = (now, list(vector))
            self._cache.move_to_end(key)
            while len(self._cache) > settings.rag_embedding_cache_max_entries:
                self._cache.popitem(last=False)
        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.inner.embed_documents(texts)


embedding_model = CachedEmbeddings(_remote_embedding_model)


def chat(prompt: str) -> str:
    response = chat_model.invoke(prompt)
    return response.content


def chat_fast(prompt: str, *, metrics: dict | None = None) -> str:
    started = time.perf_counter()
    response = fast_chat_model.invoke(prompt)
    if metrics is not None:
        usage = response.usage_metadata or {}
        metrics.update({
            "model": fast_chat_model.model_name,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "timeout_seconds": settings.bailian_request_timeout_seconds,
            "max_retries": settings.bailian_max_retries,
        })
    return response.content


def embed_text(text: str) -> list[float]:
    return embedding_model.embed_query(text)


def embed_texts(texts: list[str]) -> list[list[float]]:
    return embedding_model.embed_documents(texts)
