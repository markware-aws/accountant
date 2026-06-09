from openai import AsyncOpenAI

client = AsyncOpenAI()

# text-embedding-3-small max is 8192 tokens.
# Greek tokenizes ~4 chars/token, so 25000 chars ≈ 6250 tokens — safely under the limit.
_MAX_CHARS = 25_000


async def embed(text: str) -> list[float]:
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:_MAX_CHARS],
    )
    return response.data[0].embedding
