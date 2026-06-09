from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from services.embeddings import embed

# Applied to the vector component only — FTS results can push below-threshold
# chunks into the final set via RRF, which is the desired behaviour.
SIMILARITY_THRESHOLD = 0.40

# RRF constant — standard value, controls influence of rank position
_RRF_K = 60


async def retrieve(query: str, db: AsyncSession, top_k: int = 8) -> list[dict]:
    query_embedding = await embed(query)
    embedding_literal = "[" + ",".join(str(v) for v in query_embedding) + "]"

    # Hybrid search: vector similarity + PostgreSQL full-text, combined via RRF.
    # FTS uses 'simple' dictionary (no stemming) which works well for Greek —
    # it matches exact word forms including inflected legal terms.
    result = await db.execute(text("""
        WITH vector_search AS (
            SELECT
                id,
                1 - (embedding <=> CAST(:emb AS vector)) AS vec_score,
                ROW_NUMBER() OVER (ORDER BY embedding <=> CAST(:emb AS vector)) AS vec_rank
            FROM documents
            ORDER BY embedding <=> CAST(:emb AS vector)
            LIMIT :pool
        ),
        text_search AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    ORDER BY ts_rank(
                        to_tsvector('simple', content),
                        plainto_tsquery('simple', :query)
                    ) DESC
                ) AS text_rank
            FROM documents
            WHERE to_tsvector('simple', content) @@ plainto_tsquery('simple', :query)
            LIMIT :pool
        ),
        fused AS (
            SELECT
                v.id,
                v.vec_score,
                (1.0 / (:rrf_k + v.vec_rank))
                    + COALESCE(1.0 / (:rrf_k + t.text_rank), 0) AS rrf_score
            FROM vector_search v
            LEFT JOIN text_search t ON v.id = t.id
            ORDER BY rrf_score DESC
            LIMIT :top_k
        )
        SELECT
            d.source, d.category, d.law_number, d.article, d.content,
            f.vec_score,
            f.rrf_score
        FROM fused f
        JOIN documents d ON d.id = f.id
        ORDER BY f.rrf_score DESC
    """), {
        "emb":   embedding_literal,
        "query": query,
        "pool":  top_k * 5,   # cast a wider net before fusing
        "top_k": top_k,
        "rrf_k": _RRF_K,
    })

    return [
        {
            "source":     r.source,
            "category":   r.category,
            "law_number": r.law_number or "",
            "article":    r.article or "",
            "content":    r.content,
            "similarity": r.vec_score,   # shown in debug; threshold applied below
            "rrf_score":  r.rrf_score,
        }
        for r in result.fetchall()
        if r.vec_score >= SIMILARITY_THRESHOLD
    ]
