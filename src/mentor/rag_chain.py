"""
rag_mentor.py

Job of this file: the AI Career Mentor chatbot.
1. Take the user's career question
2. Embed the question
3. Search career_notes.index for the most relevant chunks (retrieval)
4. Give those chunks + the question to Gemini, and ask it to answer ONLY
   using that retrieved information (generation) - this combo is "RAG":
   Retrieval-Augmented Generation
5. If the notes don't contain the answer, the mentor should say so instead
   of making something up
"""

import os
import json
import numpy as np
import faiss
import google.generativeai as genai
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.safety.guardrails import validate_question

from dotenv import load_dotenv
load_dotenv()
using_api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=using_api_key)

EMBEDDING_MODEL = "models/gemini-embedding-001"
CHAT_MODEL = "gemini-3.5-flash-lite"

BASE_DIR = Path(__file__).resolve().parent.parent.parent
INDEX_PATH = str(BASE_DIR / "vectorstore" / "career_notes.index")
METADATA_PATH = str(BASE_DIR / "vectorstore" / "career_notes_metadata.json")

TOP_K_CHUNKS = 3  # how many relevant chunks to retrieve per question

MENTOR_SYSTEM_PROMPT = """You are an AI Career Mentor. You answer career-related
questions ONLY using the context provided below, which comes from a set of
career guide documents.

Rules:
- Base your answer only on the context given. Do not use outside knowledge.
- If the context does not contain enough information to answer the question,
  say clearly: "I don't have enough information in my career notes to answer
  that." Do not guess or make something up.
- Keep answers clear and practical, a few short paragraphs at most.
"""


def embed_query(text):
    """Turn the user's question into an embedding vector."""
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_query"
    )
    return result["embedding"]


def retrieve_relevant_chunks(question, top_k=TOP_K_CHUNKS):
    """
    Search career_notes.index for the chunks most relevant to the question.
    Returns a list of chunk dictionaries (source_file + text).
    """
    index = faiss.read_index(INDEX_PATH)
    with open(METADATA_PATH, "r") as f:
        metadata = json.load(f)

    query_vector = embed_query(question)
    query_vector = np.array([query_vector]).astype("float32")

    distances, positions = index.search(query_vector, top_k)

    results = []
    for position in positions[0]:
        results.append(metadata[position])
    return results


def build_context_text(chunks):
    """Combine the retrieved chunks into one text block to give to the LLM."""
    context_parts = []
    for chunk in chunks:
        context_parts.append(f"[From {chunk['source_file']}]\n{chunk['text']}")
    return "\n\n---\n\n".join(context_parts)


def ask_mentor(question):
    """
    Main function to use.
    Retrieves relevant career-notes chunks, then asks Gemini to answer the
    question using only that retrieved context.
    """
    chunks = retrieve_relevant_chunks(question)
    context_text = build_context_text(chunks)

    model = genai.GenerativeModel(
        model_name=CHAT_MODEL,
        system_instruction=MENTOR_SYSTEM_PROMPT,
        generation_config={'temperature': 0.3}
    )

    prompt = f"CONTEXT:\n{context_text}\n\nQUESTION: {question}"
    response = model.generate_content(prompt)

    return response.text, chunks


# quick test - only runs if you run THIS file directly
if __name__ == "__main__":
    print("===== AI Career Mentor =====")
    print("Ask a career question (type 'quit' to stop)\n")

    while True:
        question = input("You: ")
        if question.lower() == "quit":
            break

        is_valid, reason = validate_question(question)
        if not is_valid:
            print(f"\nMentor: I can't help with that. {reason}\n")
            continue

        answer, used_chunks = ask_mentor(question)

        print(f"\nMentor: {answer}\n")
        print("(Sources used:", ", ".join(set(c["source_file"] for c in used_chunks)), ")\n")
