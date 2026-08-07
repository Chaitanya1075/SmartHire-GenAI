"""
build_job_index.py

Job of this file: run ONCE to prepare the search system.
1. Read your jobs CSV
2. For each job, combine title + skills + description into one text block
3. Turn that text into an embedding (a list of numbers representing meaning)
4. Store all embeddings in a FAISS index (a fast search structure)
5. Save the index + the job details to disk so job_search.py can use them later

You do NOT need to run this every time. Only run it again if your CSV changes.
"""

import pandas as pd
import numpy as np
import faiss
import json
import time
import google.generativeai as genai
import os

from dotenv import load_dotenv
load_dotenv()
using_api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=using_api_key)

EMBEDDING_MODEL = "models/gemini-embedding-001"

CSV_PATH = r"C:\Users\prasa\Downloads\Job-Description_archive\postings.csv"
MAX_JOBS = 350                     # only embed the first 500 jobs (keep it fast/cheap while testing)
INDEX_SAVE_PATH = "vectorstore/jobs.index"     # the FAISS index file that gets created
METADATA_SAVE_PATH = "vectorstore/jobs_metadata.json"  # job details matched to each index position


def load_jobs(csv_path, max_jobs):
    """Read the CSV and keep only the columns we actually need."""
    df = pd.read_csv(csv_path)

    # keep only the columns relevant to matching, drop rows with no description
    df = df[["job_id", "title", "company_name", "description", "skills_desc", "location"]]
    df = df.dropna(subset=["description"])
    df = df.head(max_jobs)

    return df


def build_job_text(row):
    """
    Combine the useful fields into one text block.
    This combined text is what actually gets embedded (turned into numbers).
    """
    title = str(row["title"]) if pd.notna(row["title"]) else ""
    skills = str(row["skills_desc"]) if pd.notna(row["skills_desc"]) else ""
    description = str(row["description"]) if pd.notna(row["description"]) else ""

    return f"Job Title: {title}\nSkills: {skills}\nDescription: {description}"


def embed_text(text):
    """Send text to Gemini's embedding model and get back a vector (list of numbers)."""
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document"
    )
    return result["embedding"]


def build_index():
    """Main function: load jobs, embed each one, build and save the FAISS index."""
    jobs_df = load_jobs(CSV_PATH, MAX_JOBS)
    print(f"Loaded {len(jobs_df)} jobs. Creating embeddings...")

    embeddings = []
    metadata = []

    for i, row in jobs_df.iterrows():
        try:
            job_text = build_job_text(row)
            vector = embed_text(job_text)
        except Exception as e:
            print(f"Stopped early due to an error: {e}")
            print(f"Saving the {len(embeddings)} jobs embedded so far instead of losing them...")
            break

        embeddings.append(vector)

        metadata.append({
            "job_id": str(row["job_id"]),
            "title": row["title"],
            "company_name": row["company_name"],
            "location": row["location"],
            "description": row["description"][:500]  # store a short preview only
        })

        if (len(embeddings)) % 25 == 0:
            print(f"Embedded {len(embeddings)} / {len(jobs_df)} jobs...")

        time.sleep(6)  # small pause to avoid hitting rate limits

    # Convert to the format FAISS expects
    embeddings_array = np.array(embeddings).astype("float32")

    # Build a simple FAISS index (L2 = straight-line distance between vectors)
    dimension = embeddings_array.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_array)

    # Save index and metadata to disk
    faiss.write_index(index, INDEX_SAVE_PATH)
    with open(METADATA_SAVE_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nDone! Saved index to '{INDEX_SAVE_PATH}' and metadata to '{METADATA_SAVE_PATH}'")


if __name__ == "__main__":
    build_index()
