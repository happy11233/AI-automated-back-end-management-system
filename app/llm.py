from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config import settings


chat_model = ChatOpenAI(
    model=settings.bailian_chat_model,
    api_key=settings.dashscope_api_key,
    base_url=settings.bailian_base_url,
    temperature=0.2,
)


embedding_model = OpenAIEmbeddings(
    model=settings.bailian_embedding_model,
    api_key=settings.dashscope_api_key,
    base_url=settings.bailian_base_url,
    dimensions=settings.bailian_embedding_dimensions,
    check_embedding_ctx_length=False,
)


def chat(prompt: str) -> str:
    response = chat_model.invoke(prompt)
    return response.content


def embed_text(text: str) -> list[float]:
    return embedding_model.embed_query(text)


def embed_texts(texts: list[str]) -> list[list[float]]:
    return embedding_model.embed_documents(texts)