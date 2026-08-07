"""
resume_parser.py

Job of this file:
1. Take the raw resume text (from resume_reader.py)
2. Send it to Gemini with strict instructions to reply in JSON only
3. Check that the JSON we got back actually has the fields we need
   (this is the "validation" step)
"""

import json
import os
import google.generativeai as genai

# Reads your API key from an environment variable called GEMINI_API_KEY
# Set it like this before running (if running locally, not Colab):
#   export GEMINI_API_KEY=your-key-here      (Mac/Linux)
#   set GEMINI_API_KEY=your-key-here          (Windows)
#
# If you're running this in Google Colab like in class, replace the line
# below with:
#   from google.colab import userdata
#   using_api_key = userdata.get("GEMINI_API_KEYS")
from dotenv import load_dotenv
load_dotenv()
using_api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=using_api_key)

MODEL_NAME = "gemini-3.5-flash-lite"

# This is the instruction we give the LLM. Being VERY specific here is what
# makes the output reliable - this is "prompt engineering".
SYSTEM_PROMPT = """You are a resume parser. Read the resume text and output ONLY a JSON object.

Do not add any explanation, notes, or markdown formatting like ```json.
Just output the raw JSON object and nothing else.

The JSON must have exactly these fields:
{
  "name": "string",
  "skills": ["string", "string", ...],
  "experience": [
    {"title": "string", "company": "string", "duration": "string", "highlights": ["string", "string", ...]}
  ],
  "education": [
    {"degree": "string", "institution": "string"}
  ],
  "target_role": "string"
}

If you cannot find a value, use an empty string "" or an empty list [].

For "highlights" under experience: extract the actual bullet points or
achievement lines written under each job in the resume (e.g. "Reduced
processing time by 20%", "Led a team of 4 engineers"). If a job has no
bullet points in the original resume, use an empty list [].

For "target_role" specifically: this is NOT usually written directly on the
resume, so you must infer it. Look at the candidate's most recent job title
and their strongest/most repeated skills, and infer the most likely role
they are trying to get next. For example, someone with Active Directory,
Windows Server, and Red Hat Linux experience should get something like
"Systems Administrator" or "IT Infrastructure Engineer". Do not leave this
blank unless the resume gives truly no signal about their field at all.
"""


def call_llm(resume_text):
    """Send the resume text to Gemini and return its raw text reply."""
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT,
        generation_config={'temperature': 0.3}
    )
    prompt = f"Resume text:\n{resume_text}\n\nExtract the JSON now."
    response = model.generate_content(prompt)
    return response.text

def clean_json_text(raw_text):
    """
    Sometimes the LLM wraps its JSON reply in markdown fences like:
```json
        { ... }
```
    even when we tell it not to. This function removes those fences
    so json.loads() can read the text properly.
    """
    text = raw_text.strip()

    if text.startswith("```"):
        # remove the first line (```json or ```)
        text = text.split("\n", 1)[1] if "\n" in text else text
        # remove the last ``` if present
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]

    return text.strip()

def validate_json(data):
    """
    Check that the parsed JSON has all the fields we expect,
    with the right basic types. Returns True/False.
    """
    required_fields = ["name", "skills", "experience", "education", "target_role"]

    for field in required_fields:
        if field not in data:
            print(f"Missing field: {field}")
            return False

    if not isinstance(data["skills"], list):
        print("skills should be a list")
        return False

    if not isinstance(data["experience"], list):
        print("experience should be a list")
        return False

    if not isinstance(data["education"], list):
        print("education should be a list")
        return False

    return True


def parse_resume(resume_text):
    """
    Main function to use.
    Sends resume text to the LLM, parses the JSON, validates it.
    Returns a Python dictionary if successful.
    """
    raw_reply = call_llm(resume_text)
    cleaned_reply = clean_json_text(raw_reply)

    # Try to convert the text reply into a real Python dictionary
    try:
        data = json.loads(cleaned_reply)
    except json.JSONDecodeError:
        raise ValueError(f"LLM did not return valid JSON. Raw reply was:\n{raw_reply}")

    # Check the dictionary has the fields we need
    if not validate_json(data):
        raise ValueError("JSON was valid but missing expected fields")

    return data


# quick test - only runs if you run THIS file directly
if __name__ == "__main__":
    from resume_reader import read_resume

    resume_text = read_resume(r"C:\Users\prasa\Downloads\archive\data\data\ENGINEERING\43752620.pdf")
    profile = parse_resume(resume_text)

    print("Parsed profile:")
    print(json.dumps(profile, indent=2))
