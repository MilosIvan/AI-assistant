import os

from dotenv import load_dotenv
from google import genai
from supabase import create_client


load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"],
)


def search_chunks(
    question: str,
    course_id: str,
    limit: int = 5,
) -> list[dict]:
    """Vraća najsličnije odlomke za zadano pitanje."""

    if not question.strip():
        return []

    # 1. Generiraj embedding pitanja.
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=question,
        config={"output_dimensionality": 1536}
    )

    query_embedding = response.embeddings[0].values

    # 2. Pozovi PostgreSQL funkciju preko Supabase RPC-a.
    result = supabase.rpc(
        "match_document_chunks",
        {
            "query_embedding": query_embedding,
            "match_count": limit,
            "filter_course_id": course_id,
        },
    ).execute()

    return result.data


if __name__ == "__main__":
    question = input("Unesi pitanje: ")
    course_id = os.environ["COURSE_ID"]

    results = search_chunks(question, course_id)

    if not results:
        print("Nema pronađenih odlomaka.")
    else:
        for i, item in enumerate(results, start=1):
            print(f"\n{'=' * 50}")
            print(f"Rezultat {i}")
            print(f"Dokument: {item['filename']}")
            print(f"Stranica: {item['page_number']}")
            print(f"Sličnost: {item['similarity']:.4f}")
            print(f"\n{item['content']}")
