import json
import os
import uuid
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "municipal_bylaws"
EMBED_MODEL = "text-embedding-004"


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY is not configured in .env. Please set a valid Gemini API key.")
    return genai.Client(api_key=api_key)


qdrant = QdrantClient(url=QDRANT_URL)


def embed_text(text: str) -> list[float]:
    gemini = get_gemini_client()
    res = gemini.models.embed_content(model=EMBED_MODEL, contents=text)
    return res.embeddings[0].values


def load_json_corpus(json_path: Path) -> list[dict]:
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def chunk_pdf_files(data_dir: Path, chunk_size: int = 1200, overlap: int = 150) -> list[dict]:
    records = []
    for pdf_file in data_dir.glob("*.pdf"):
        reader = PdfReader(str(pdf_file))
        for page_num, page in enumerate(reader.pages, start=1):
            raw_text = (page.extract_text() or "").strip()
            if not raw_text:
                continue
            start = 0
            chunk_idx = 1
            while start < len(raw_text):
                snippet = raw_text[start : start + chunk_size]
                records.append(
                    {
                        "doc_title": pdf_file.stem.replace("_", " ").title(),
                        "department": "GENERAL",
                        "section": f"Page {page_num} - Excerpt {chunk_idx}",
                        "page": page_num,
                        "text": snippet,
                    }
                )
                start += chunk_size - overlap
                chunk_idx += 1
    return records


def ingest():
    data_dir = Path(__file__).parent / "sample_data"
    corpus = load_json_corpus(data_dir / "municipal_bylaws.json")
    corpus.extend(chunk_pdf_files(data_dir))

    if not corpus:
        print("No policy records found to ingest.")
        return

    sample_vec = embed_text(corpus[0]["text"])
    vector_dim = len(sample_vec)

    if qdrant.collection_exists(COLLECTION_NAME):
        qdrant.delete_collection(COLLECTION_NAME)

    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
    )

    points = []
    for idx, item in enumerate(corpus):
        vec = sample_vec if idx == 0 else embed_text(item["text"])
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload=item,
            )
        )

    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"Successfully indexed {len(points)} municipal policy chunks into Qdrant collection '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    ingest()
