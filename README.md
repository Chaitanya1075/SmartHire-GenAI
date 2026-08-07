# SmartHire GenAI

Resume Matching & AI Career Mentor — capstone project.

## What it does
1. **Upload a resume** (PDF/DOCX) → get a structured, validated profile (name, skills, experience, education, inferred target role)
2. **Semantic job search** → see the top 5 matching jobs from a FAISS-indexed job postings dataset, with an intuitive match percentage
3. **CV suggestions** → pick any matched job and get AI-generated missing skills, rewritten bullet points, and a tailored summary
4. **AI Career Mentor** → ask career questions and get answers grounded in a written knowledge base (RAG), with guardrails against unsafe or off-topic input

## Status — all 6 core modules complete
- [x] Module 1: Resume Parser (structured JSON extraction + validation)
- [x] Module 2: Semantic Job Search (FAISS)
- [x] Module 3: CV Improvement Generator + prompt library
- [x] Module 4: AI Career Mentor (RAG)
- [x] Module 5: Guardrails (unsafe input, off-topic input, self-harm crisis handling)
- [x] Module 6: Streamlit Portal

See `reports/answer_quality.md` for the full evaluation writeup: retrieval
relevance testing across 5 resumes/industries, hallucination checks, a
prompt before/after comparison, and guardrails testing.

## Local Setup

1. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and add your real Gemini API key:
   ```powershell
   copy .env.example .env
   ```
   Then edit `.env` and set `GEMINI_API_KEY=your-real-key`.

3. **Build the indexes** (already pre-built and included in this repo under
   `vectorstore/` - `jobs.index`, `career_notes.index`, and their metadata
   files - so you normally don't need to redo this step. Only re-run if you
   change the source data):
   ```powershell
   python build_job_index.py
   python build_notes_index.py
   ```

4. Run the app:
   ```powershell
   streamlit run app/streamlit_app.py
   ```

## Deploying to Streamlit Community Cloud

1. Push this project to a GitHub repository. `.env` is excluded via
   `.gitignore` and never gets pushed - but the pre-built `.index` and
   `_metadata.json` files ARE pushed, since the deployed app needs them and
   can't rebuild them on the server without burning API quota again.
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with
   GitHub, click "New app," and select this repository.
3. Set the main file path to `app/streamlit_app.py`.
4. In the app's **Settings → Secrets**, add:
   ```
   GEMINI_API_KEY = "your-real-key-here"
   ```
5. Deploy, then test all 4 tabs on the live URL.

## Project Structure
```
smarthire-genai/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── data/
│   ├── jobs/               # postings.csv (excluded from git - see .gitignore)
│   ├── resumes/            # sample resumes for testing
│   └── career_notes/       # knowledge base (7 industries, 21 sub-roles)
│
├── vectorstore/            # pre-built FAISS indexes + metadata
│
├── notebooks/
│   ├── 01_embeddings_explore.ipynb
│   ├── 02_build_faiss.ipynb
│   └── 03_rag_prototype.ipynb
│
├── src/
│   ├── config.py            # model names, paths, params (reference)
│   ├── evaluate.py          # reproducible evaluation script
│   ├── parsing/
│   │   ├── loader.py             # Module 1: PDF/DOCX text extraction
│   │   └── resume_parser.py      # Module 1: LLM structured parsing + validation
│   ├── search/
│   │   └── job_search.py         # Module 2: semantic job search
│   ├── generate/
│   │   ├── prompts.py             # Module 3: prompt library
│   │   └── cv_suggestions.py      # Module 3: CV improvement generator
│   ├── mentor/
│   │   └── rag_chain.py           # Module 4: RAG-based AI Career Mentor
│   └── safety/
│       └── guardrails.py          # Module 5: input safety checks
│
├── build_job_index.py      # Module 2: builds the FAISS job index (run once)
├── build_notes_index.py    # Module 4: builds the FAISS career-notes index (run once)
│
├── app/
│   └── streamlit_app.py    # Module 6: the full portal UI
│
└── reports/
    ├── answer_quality.md   # full evaluation report
    └── final_report.pdf    # design choices, what worked, limitations
```

## Notes on design choices
- **Model:** `gemini-3.5-flash-lite` for chat/generation,
  `models/gemini-embedding-001` for embeddings - chosen for free-tier
  availability while learning, with API keys read from environment
  variables (`.env` locally, Streamlit Secrets when deployed).
- **Job index size:** built from a subset (~300-350) of the full LinkedIn
  job postings dataset rather than the complete file, due to free-tier
  rate limits on the embedding API. This is a documented limitation (see
  evaluation report) - a larger index would likely improve match quality
  further, especially for less common resume fields.
- **Career notes knowledge base:** covers 7 industries (IT, Finance, HR,
  Sales, Healthcare, Engineering, Marketing/Digital Media), written
  specifically for this project rather than scraped from external sources,
  to keep the RAG mentor's grounding reliable and testable.
- **Guardrails:** combine fast rule-based checks (keyword blocklist with
  word-boundary matching to avoid false positives, prompt-injection
  detection) with one LLM-based topic classifier call, plus a dedicated
  self-harm detection path that routes to real crisis resources instead of
  a generic refusal.
- **Notebooks vs. scripts:** `build_job_index.py` and `build_notes_index.py`
  contain the actual FAISS index-building logic and remain at the project
  root, rather than being fully embedded in the `notebooks/` files. The
  notebooks (`02_build_faiss.ipynb`, etc.) import and demonstrate this same
  logic on a small sample instead of re-running the full embedding process,
  to avoid repeatedly consuming free-tier API quota. This keeps the reusable
  pipeline logic in versioned, testable scripts while still providing
  notebook-based exploration and documentation as requested.

## Known limitations
- The job index (~300-350 jobs) is a subset of the full dataset; retrieval
  quality varies by industry as a result (see evaluation report - IT/Finance/
  Sales scored well, Healthcare scored poorly due to underrepresentation in
  the sampled subset).
- The career-notes knowledge base covers 7 industries; questions about
  fields outside those (e.g. law, education, agriculture) will be correctly
  refused by the mentor rather than answered, since nothing in the source
  data supports an answer.
- RAG retrieval occasionally misses a relevant chunk when the question's
  phrasing differs significantly from the source text's wording (documented
  with a specific example in the evaluation report).
