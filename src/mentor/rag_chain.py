"""
rag_chain.py

AI Career Mentor - RAG pipeline.

Retrieval: custom FAISS search over BOTH the career_notes index and the
jobs index, so the mentor is grounded in the job corpus AND career notes.

Generation: orchestrated with LangChain - a ChatPromptTemplate composed
with a Gemini chat model via LCEL (the `prompt | llm` pattern), instead of
calling the Gemini API directly.
"""

import os
import json
import numpy as np
import faiss
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai  # used only for embeddings here

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()
using_api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=using_api_key)

EMBEDDING_MODEL = "models/gemini-embedding-001"
CHAT_MODEL = "gemini-3.5-flash-lite"

BASE_DIR = Path(__file__).resolve().parent.parent.parent
NOTES_INDEX_PATH = str(BASE_DIR / "vectorstore" / "career_notes.index")
NOTES_METADATA_PATH = str(BASE_DIR / "vectorstore" / "career_notes_metadata.json")
JOBS_INDEX_PATH = str(BASE_DIR / "vectorstore" / "jobs.index")
JOBS_METADATA_PATH = str(BASE_DIR / "vectorstore" / "jobs_metadata.json")

TOP_K_NOTES = 3
TOP_K_JOBS = 2

MENTOR_SYSTEM_PROMPT = """You are an AI Career Mentor. You answer career-related
questions ONLY using the context provided below, which comes from two sources:
career guide documents AND real job postings.

Rules:
- Base your answer only on the context given. Do not use outside knowledge.
- If the context does not contain enough information to answer the question,
  say clearly: "I don't have enough information in my career notes to answer
  that." Do not guess or make something up.
- Keep answers clear and practical, a few short paragraphs at most.
- If a job posting is relevant to the question, you may mention it by title
  and company as a concrete example."""


def embed_query(text):
    """Turn the user's question into an embedding vector."""
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_query"
    )
    return result["embedding"]


def retrieve_note_chunks(question, top_k=TOP_K_NOTES):
    """Search career_notes.index for the most relevant chunks."""
    index = faiss.read_index(NOTES_INDEX_PATH)
    with open(NOTES_METADATA_PATH, "r") as f:
        metadata = json.load(f)
    query_vector = np.array([embed_query(question)]).astype("float32")
    _, positions = index.search(query_vector, top_k)
    return [metadata[p] for p in positions[0]]


def retrieve_job_chunks(question, top_k=TOP_K_JOBS):
    """Search jobs.index for the most relevant job postings."""
    index = faiss.read_index(JOBS_INDEX_PATH)
    with open(JOBS_METADATA_PATH, "r") as f:
        metadata = json.load(f)
    query_vector = np.array([embed_query(question)]).astype("float32")
    _, positions = index.search(query_vector, top_k)
    return [metadata[p] for p in positions[0]]


def build_context_text(note_chunks, job_chunks):
    """Combine career-note chunks AND job posting chunks into one context block."""
    parts = []
    for chunk in note_chunks:
        parts.append(f"[Career Note: {chunk['source_file']}]\n{chunk['text']}")
    for job in job_chunks:
        parts.append(
            f"[Job Posting: {job['title']} at {job.get('company_name', 'Unknown')}]\n"
            f"{job.get('description', '')[:400]}"
        )
    return "\n\n---\n\n".join(parts)


# ---- LangChain orchestration ----
# A ChatPromptTemplate composed with the Gemini chat model via LCEL.
# This is the "orchestrated with LangChain" piece: instead of calling
# genai.GenerativeModel(...).generate_content(...) directly, generation now
# flows through a LangChain Runnable chain.
llm = ChatGoogleGenerativeAI(
    model=CHAT_MODEL,
    google_api_key=using_api_key,
    temperature=0.3
)

prompt_template = ChatPromptTemplate.from_messages([
    ("system", MENTOR_SYSTEM_PROMPT),
    ("human", "CONTEXT:\n{context}\n\nQUESTION: {question}")
])

mentor_chain = prompt_template | llm


def ask_mentor(question):
    """
    Main function to use.
    Retrieves relevant chunks from BOTH career notes and job postings,
    then runs them through the LangChain-orchestrated generation chain.
    Returns (answer_text, list_of_source_chunks).
    """
    note_chunks = retrieve_note_chunks(question)
    job_chunks = retrieve_job_chunks(question)
    context_text = build_context_text(note_chunks, job_chunks)

    response = mentor_chain.invoke({"context": context_text, "question": question})

    # response.content is usually a string, but LangChain's Gemini wrapper can
    # sometimes return a list of content parts instead - handle both cases
    if isinstance(response.content, list):
        answer = "".join(
            part if isinstance(part, str) else part.get("text", "")
            for part in response.content
        )
    else:
        answer = response.content

    # Combine sources for display - job chunks get a synthetic "source_file"
    # label so the Streamlit app's existing source-display code keeps working
    # without any changes needed there.
    all_sources = list(note_chunks)
    for job in job_chunks:
        all_sources.append({"source_file": f"Job posting: {job['title']}"})

    return answer, all_sources


# quick test - only runs if you run THIS file directly
if __name__ == "__main__":
    import sys
    sys.path.append(str(BASE_DIR))
    from src.safety.guardrails import validate_question

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