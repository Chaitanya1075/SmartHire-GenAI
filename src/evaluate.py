"""
evaluate.py

Answer-quality checks for the AI Career Mentor and job search.
This script re-runs the test questions documented in reports/answer_quality.md
so results can be reproduced programmatically, not just read as a static report.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.mentor.rag_chain import ask_mentor
from src.search.job_search import search_jobs

# Same test questions used in reports/answer_quality.md's Module 4 evaluation
MENTOR_TEST_QUESTIONS = [
    "What skills do I need as a financial analyst?",
    "Who is our prime minister?",                      # should refuse - off-topic
    "Can we use paracetamol for fever and cold?",       # should refuse - off-topic
    "How do I transition from IT support to software engineering?",
    "What are the main basics of sales?",
    "How do I become a financial analyst without a finance degree?",  # trick question
]


def run_mentor_evaluation():
    """Run each test question through the mentor and print the answer +
    sources, so results can be manually judged for correctness/grounding
    (see reports/answer_quality.md for the judged results)."""
    print("===== AI Career Mentor Evaluation =====\n")
    for question in MENTOR_TEST_QUESTIONS:
        answer, chunks = ask_mentor(question)
        sources = ", ".join(set(c["source_file"] for c in chunks)) if chunks else "none"
        print(f"Q: {question}")
        print(f"A: {answer}")
        print(f"Sources: {sources}\n{'-'*60}\n")


def run_job_search_evaluation(search_text, label):
    """Run one profile's search text through job search and print the
    top 5 matches with match percentages, for manual relevance judging."""
    print(f"===== Job Search Evaluation: {label} =====\n")
    results = search_jobs(search_text, top_n=5)
    for i, job in enumerate(results, start=1):
        print(f"{i}. {job['title']} at {job['company_name']} - {job.get('match_percentage', '?')}% match")
    print()


if __name__ == "__main__":
    run_mentor_evaluation()

    # Example job search evaluation - replace with a real parsed profile's
    # search text to reproduce the tests from reports/answer_quality.md
    run_job_search_evaluation(
        "Target Role: Finance Manager\nSkills: Budgeting, Financial Analysis, Cash Flow",
        "Finance resume"
    )