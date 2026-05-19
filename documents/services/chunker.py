"""Sliding-window chunker tuned for short documents like ID cards or passbooks."""


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if not text or not text.strip():
        return []

    clean = " ".join(text.split())
    if len(clean) <= chunk_size:
        return [clean]

    chunks: list[str] = []
    step = max(1, chunk_size - overlap)
    start = 0
    while start < len(clean):
        end = start + chunk_size
        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(clean):
            break
        start += step
    return chunks
