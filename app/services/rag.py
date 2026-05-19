from groq import Groq

from app.storage.chroma_store import RetrievedChunk


class RAGEngine:
    def __init__(
        self,
        backend: str,
        groq_api_key: str | None,
        groq_model: str,
        max_context_chunks: int,
    ) -> None:
        self._backend = backend.lower().strip()
        self._groq_model = groq_model
        self._max_context_chunks = max_context_chunks
        self._groq = Groq(api_key=groq_api_key) if groq_api_key else None

    def answer_question(self, question: str, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "I could not find relevant information in the indexed documents."

        selected = chunks[: self._max_context_chunks]
        context = "\n\n".join(
            f"[Source: {c.source} | Chunk: {c.chunk_index}]\n{c.text}" for c in selected
        )

        if self._backend == "groq" and self._groq is not None:
            return self._generate_groq_answer(question, context)

        return self._generate_extractive_answer(question, selected)

    def _generate_groq_answer(self, question: str, context: str) -> str:
        system = (
            "You are a precise document assistant. "
            "Answer only from the given context. "
            "If data is missing, say so clearly."
        )
        user = f"Question:\n{question}\n\nContext:\n{context}"

        completion = self._groq.chat.completions.create(
            model=self._groq_model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

        content = completion.choices[0].message.content
        return content.strip() if content else "No answer was generated."

    def _generate_extractive_answer(self, question: str, chunks: list[RetrievedChunk]) -> str:
        del question
        top = chunks[0]
        return (
            "Answer (extractive fallback):\n"
            f"{top.text[:900]}\n\n"
            "Switch GENERATION_BACKEND=groq and set GROQ_API_KEY for generative answers."
        )
