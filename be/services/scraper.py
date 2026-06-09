import re
import pdfplumber


def extract_text(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def chunk_document(
    text: str,
    source_meta: dict,
    chunk_size: int = 400,
    overlap: int = 80,
) -> list[dict]:
    """
    Split by Greek article boundaries first, then by word count.
    Article numbers are carried as metadata on each chunk.
    """
    article_pattern = r"(Άρθρο\s+\d+[α-ωΑ-Ω]?\.?)"
    parts = re.split(article_pattern, text)

    chunks = []
    current_article = "Γενικό"

    for part in parts:
        if re.match(article_pattern, part):
            current_article = part.strip()
            continue

        words = part.split()
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i : i + chunk_size]
            if len(chunk_words) < 50:
                continue
            chunks.append(
                {
                    **source_meta,
                    "article": current_article,
                    "content": " ".join(chunk_words),
                }
            )

    return chunks
