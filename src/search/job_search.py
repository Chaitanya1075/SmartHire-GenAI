"""
job_search.py

Job of this file: search the FAISS index you built in build_job_index.py.
1. Take a candidate's profile (from resume_parser.py) or any search text
2. Turn it into an embedding
3. Search the FAISS index for the closest matching jobs
4. Return the top-N matches with their details
"""

import faiss
import json
import numpy as np
import google.generativeai as genai
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()
using_api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=using_api_key)

EMBEDDING_MODEL = "models/gemini-embedding-001"
BASE_DIR = Path(__file__).resolve().parent.parent.parent
INDEX_PATH = str(BASE_DIR / "vectorstore" / "jobs.index")
METADATA_PATH = str(BASE_DIR / "vectorstore" / "jobs_metadata.json")


def embed_query(text):
    """Turn the search text (candidate profile) into an embedding vector."""
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_query"   # note: "query" here vs "document" when building the index
    )
    return result["embedding"]


def profile_to_search_text(profile):
    """
    Convert a parsed resume profile (the dictionary from resume_parser.py)
    into one text block to search with - similar style to build_job_text()
    in build_job_index.py.
    """
    skills_text = ", ".join(profile.get("skills", []))
    target_role = profile.get("target_role", "")

    return f"Target Role: {target_role}\nSkills: {skills_text}"

def clean_value(value, fallback="Unknown"):
    """
    Some job entries have missing data (empty CSV cells become NaN).
    This replaces any NaN/None value with a readable fallback like "Unknown".
    """
    if value is None:
        return fallback
    if isinstance(value, float) and value != value:  # this is how you detect NaN in Python
        return fallback
    return value

def search_jobs(search_text, top_n=5):
    """
    Main function to use.
    Takes search text (usually from profile_to_search_text), embeds it,
    and returns the top_n most similar jobs from the saved index.
    """
    # load the saved index and job details
    index = faiss.read_index(INDEX_PATH)
    with open(METADATA_PATH, "r") as f:
        metadata = json.load(f)

    # embed the search text
    query_vector = embed_query(search_text)
    query_vector = np.array([query_vector]).astype("float32")

    # search the index - returns distances and positions of closest matches
    distances, positions = index.search(query_vector, top_n)

    results = []
    for rank, position in enumerate(positions[0]):
        job_info = metadata[position]
        distance = float(distances[0][rank])
        job_info["match_distance"] = distance  # lower = closer match

        similarity = max(0.0, 1 - (distance ** 2) / 2)
        job_info["match_percentage"] = round(similarity * 100, 1)

        job_info["company_name"] = clean_value(job_info.get("company_name"), "Unknown Company")
        job_info["location"] = clean_value(job_info.get("location"), "Unknown Location")
        results.append(job_info)

    return results


# quick test - only runs if you run THIS file directly
if __name__ == "__main__":
    from resume_reader import read_resume
    from resume_parser import parse_resume

    resume_text = read_resume(r"C:\Users\prasa\Downloads\resume_archive\data\data\HEALTHCARE\33750209.pdf")
    profile = parse_resume(resume_text)

    search_text = profile_to_search_text(profile)
    print("Searching jobs using this profile text:\n", search_text)

    matches = search_jobs(search_text, top_n=5)

    print("Top matching jobs:")
    for i, job in enumerate(matches, start=1):
        print(f"\n{i}. {job['title']} at {job['company_name']} ({job['location']})")
        print(f"   Match distance: {job['match_distance']:.4f} (lower = better match)")
