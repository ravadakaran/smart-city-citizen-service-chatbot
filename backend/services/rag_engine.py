import os
from google import genai
from google.genai import types
from qdrant_client import QdrantClient

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "municipal_bylaws"
EMBED_MODEL = "text-embedding-004"
GEN_MODEL = "gemini-2.5-flash"

qdrant = QdrantClient(url=QDRANT_URL)


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY is not configured in .env. Please add a valid Gemini API key.")
    return genai.Client(api_key=api_key)


def answer_policy_query(query: str, score_threshold: float = 0.68) -> dict:
    try:
        gemini = get_gemini_client()
        emb = gemini.models.embed_content(
            model=EMBED_MODEL,
            contents=query,
        ).embeddings[0].values

        hits = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=emb,
            limit=4,
            score_threshold=score_threshold,
        ).points
    except Exception as exc:
        return {
            "answer": f"Policy knowledge base is temporarily unavailable ({exc}). Please ensure Qdrant and ingest_policies.py have been initialized.",
            "citations": [],
            "grounded": False,
        }

    if not hits:
        return {
            "answer": (
                "I could not find an authoritative municipal bylaw or service charter clause matching your question. "
                "To avoid providing unverified regulatory information, I have abstained from guessing. "
                "Please rephrase with the specific municipal department (Property Tax, Trade License, Water Supply, Roads, or Waste) or contact the 311 Civic Helpline."
            ),
            "citations": [],
            "grounded": False,
        }

    context_blocks = []
    citations = []
    for idx, hit in enumerate(hits, start=1):
        meta = hit.payload or {}
        cite_label = f"[{idx}] {meta.get('doc_title', 'Municipal Charter')}, {meta.get('section', 'General')} (p. {meta.get('page', 1)})"
        citations.append(cite_label)
        context_blocks.append(f"{cite_label}:\n{meta.get('text', '')}")

    system_prompt = (
        "You are an official Smart City Citizen Service Assistant. "
        "Answer the citizen's question strictly using ONLY the verified municipal policy excerpts provided below. "
        "Every factual claim, fee, deadline, or rule MUST include an inline bracketed citation like [1] or [2]. "
        "Never invent rules or extrapolate beyond the provided text."
    )

    user_prompt = f"VERIFIED POLICY EXCERPTS:\n\n{chr(10).join(context_blocks)}\n\nCITIZEN QUESTION: {query}"

    response = gemini.models.generate_content(
        model=GEN_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.1,
        ),
    )

    return {
        "answer": response.text,
        "citations": citations,
        "grounded": True,
    }
