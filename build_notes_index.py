"""
build_notes_index.py

Job of this file: run ONCE to prepare the AI Career Mentor's knowledge base.
1. Read every .txt file in the career_notes/ folder
2. Split each one into smaller chunks (so retrieval can find the specific
   relevant part of a document, not the whole file at once)
3. Embed each chunk
4. Store all chunk embeddings in a FAISS index
5. Save the index + chunk text to disk so rag_mentor.py can use them later
"""

import os
import time
import json
import numpy as np
import faiss
import google.generativeai as genai

from dotenv import load_dotenv
load_dotenv()
using_api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=using_api_key)

EMBEDDING_MODEL = "models/gemini-embedding-001"

NOTES_FOLDER = "career_notes"
CHUNK_SIZE = 800     # characters per chunk
CHUNK_OVERLAP = 100  # overlap between chunks so we don't cut a sentence awkwardly in half

INDEX_SAVE_PATH = "vectorstore/career_notes.index"
METADATA_SAVE_PATH = "vectorstore/career_notes_metadata.json"


def read_all_notes(folder_path):
    """Read every .txt file in the folder and return a list of (filename, full_text)."""
    documents = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            documents.append((filename, text))
    return documents


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split one document's text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def embed_text(text):
    """Send text to Gemini's embedding model and get back a vector."""
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document"
    )
    return result["embedding"]


def build_notes_index():
    """Main function: read notes, chunk them, embed each chunk, build and save the FAISS index."""
    documents = read_all_notes(NOTES_FOLDER)
    print(f"Found {len(documents)} career note files.")

    embeddings = []
    metadata = []

    for filename, full_text in documents:
        chunks = chunk_text(full_text)
        print(f"  {filename}: split into {len(chunks)} chunks")

        for chunk in chunks:
            try:
                vector = embed_text(chunk)
            except Exception as e:
                print(f"Stopped early due to an error: {e}")
                print(f"Saving the {len(embeddings)} chunks embedded so far instead of losing them...")
                break

            embeddings.append(vector)
            metadata.append({
                "source_file": filename,
                "text": chunk
            })

            time.sleep(2)  # pause between calls to avoid hitting rate limits

    embeddings_array = np.array(embeddings).astype("float32")
    dimension = embeddings_array.shape[1]

    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_array)

    faiss.write_index(index, INDEX_SAVE_PATH)
    with open(METADATA_SAVE_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nDone! Embedded {len(embeddings)} chunks from {len(documents)} files.")
    print(f"Saved index to '{INDEX_SAVE_PATH}' and metadata to '{METADATA_SAVE_PATH}'")


if __name__ == "__main__":
    build_notes_index()
