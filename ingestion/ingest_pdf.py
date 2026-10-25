import os
from pathlib import Path

import fitz
from dotenv import load_dotenv
from google import genai
from supabase import create_client


load_dotenv()

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
COURSE_ID = os.environ["COURSE_ID"]
PDF_PATH = Path(os.environ["PDF_PATH"])

client = genai.Client(api_key=GEMINI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def extract_pages(pdf_path: Path) -> list[dict]:
    pages = []

    with fitz.open(pdf_path) as pdf:
        for index, page in enumerate(pdf):
            text = page.get_text("text").strip()

            if text:
                pages.append({
                    "page_number": index + 1,
                    "text": text,
                })

    return pages


def chunk_text(text: str, size=450, overlap=70) -> list[str]:
    """Jednostavna podjela teksta po riječima."""
    words = text.split()

    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))

        if end == len(words):
            break

        start = end - overlap

    return chunks


def vector_to_pgvector(vector: list[float]) -> str:
    """Pretvara embedding u tekstualni zapis pgvector vektora."""
    return "[" + ",".join(str(x) for x in vector) + "]"


def main():
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF ne postoji: {PDF_PATH}")

    pages = extract_pages(PDF_PATH)

    if not pages:
        raise ValueError(
            "PDF nema čitljivog teksta. Provjeri je li potrebno OCR."
        )

    chunks = []

    for page in pages:
        for text in chunk_text(page["text"]):
            chunks.append({
                "page_number": page["page_number"],
                "content": text,
            })

    if not chunks:
        raise ValueError("Nije pronađen nijedan odlomak.")

    print(f"Stranica s tekstom: {len(pages)}")
    print(f"Broj odlomaka: {len(chunks)}")

    # Kreiraj zapis dokumenta.
    document_result = (
        supabase.table("documents")
        .insert({
            "course_id": COURSE_ID,
            "filename": PDF_PATH.name,
            "storage_path": None,
            "status": "processing",
        })
        .execute()
    )

    document_id = document_result.data[0]["id"]

    try:
        # Generiraj embeddinge u manjim grupama.
        batch_size = 64

        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]

            result = client.models.embed_content(
                model="gemini-embedding-001",
                contents=[item["content"] for item in batch],
                config={"output_dimensionality": 1536}
            )

            rows = []

            for offset, embedding_data in enumerate(result.embeddings):
                chunk = batch[offset]

                rows.append({
                    "document_id": document_id,
                    "chunk_index": start + offset,
                    "page_number": chunk["page_number"],
                    "content": chunk["content"],
                    "embedding": vector_to_pgvector(
                        embedding_data.values
                    ),
                })

            supabase.table("document_chunks").insert(rows).execute()

            print(
                f"Spremljeno {min(start + len(batch), len(chunks))}"
                f"/{len(chunks)} odlomaka"
            )

        supabase.table("documents").update({
            "status": "ready"
        }).eq("id", document_id).execute()

        print("Obrada uspješno završena.")
        print(f"ID dokumenta: {document_id}")

    except Exception:
        supabase.table("documents").update({
            "status": "failed"
        }).eq("id", document_id).execute()
        raise


if __name__ == "__main__":
    main()
