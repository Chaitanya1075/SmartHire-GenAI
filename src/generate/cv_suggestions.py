"""
cv_suggestions.py

Job of this file:
1. Take a parsed resume profile (from resume_parser.py) and a target job
   (from job_search.py results, or typed in manually)
2. Fill in the prompt template from prompts.py with real details
3. Send it to Gemini and get back CV improvement suggestions
4. Save the suggestions to a text file
"""

import os
import google.generativeai as genai

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from prompts import CV_SUGGESTION_PROMPT_TEMPLATE

from dotenv import load_dotenv
load_dotenv()
using_api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=using_api_key)

MODEL_NAME = "gemini-3.5-flash-lite"


def format_experience(experience_list):
    """Turn the list of experience dictionaries into readable text for the prompt."""
    lines = []
    for exp in experience_list:
        lines.append(f"- {exp.get('title', '')} at {exp.get('company', '')} ({exp.get('duration', '')})")
        for highlight in exp.get('highlights', []):
            lines.append(f"    - {highlight}")
    return "\n".join(lines) if lines else "No experience listed"


def format_education(education_list):
    """Turn the list of education dictionaries into readable text for the prompt."""
    lines = []
    for edu in education_list:
        lines.append(f"- {edu.get('degree', '')}, {edu.get('institution', '')}")
    return "\n".join(lines) if lines else "No education listed"


def build_prompt(profile, job):
    """
    Fill in the CV_SUGGESTION_PROMPT_TEMPLATE with real resume and job details.
    `profile` = dictionary from resume_parser.py
    `job` = dictionary from job_search.py results (has 'title', 'company_name', 'description')
    """
    prompt = CV_SUGGESTION_PROMPT_TEMPLATE.format(
        name=profile.get("name", ""),
        skills=", ".join(profile.get("skills", [])),
        experience=format_experience(profile.get("experience", [])),
        education=format_education(profile.get("education", [])),
        job_title=job.get("title", ""),
        job_company=job.get("company_name", ""),
        job_description=job.get("description", "")
    )
    return prompt


def generate_cv_suggestions(profile, job):
    """
    Main function to use.
    Builds the prompt, sends it to Gemini, returns the suggestions as text.
    """
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config={'temperature': 0.4}
    )

    prompt = build_prompt(profile, job)
    response = model.generate_content(prompt)

    return response.text


def save_suggestions_to_file(suggestions_text, file_path="cv_suggestions_output.txt"):
    """Save the suggestions to a text file, similar to the email example from class."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(suggestions_text)
    print(f"Suggestions saved to '{file_path}'")


if __name__ == "__main__":
    from resume_reader import read_resume
    from resume_parser import parse_resume
    from job_search import search_jobs, profile_to_search_text

    resume_text = read_resume(r"C:\Users\prasa\Downloads\resume_archive\data\data\INFORMATION-TECHNOLOGY\36856210.pdf")   # your real resume path
    profile = parse_resume(resume_text)

    search_text = profile_to_search_text(profile)
    matches = search_jobs(search_text, top_n=5)
    top_job = matches[0]   # use the best-matching job as the target

    print(f"Generating suggestions for target job: {top_job['title']} at {top_job['company_name']}\n")

    suggestions = generate_cv_suggestions(profile, top_job)
    print(suggestions)
    save_suggestions_to_file(suggestions)
