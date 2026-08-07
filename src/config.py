"""
config.py

Central place for model names, paths, and tunable parameters.

Note: other modules (resume_parser.py, job_search.py, etc.) currently
define their own MODEL_NAME / EMBEDDING_MODEL constants directly, rather
than importing from here. This file exists to document the project's
settings in one place as required by the spec, without risking breaking
already-working modules by rewiring their imports this late in the project.
"""

# --- Models ---
CHAT_MODEL = "gemini-3.5-flash-lite"
EMBEDDING_MODEL = "models/gemini-embedding-001"

# --- Search params ---
TOP_N_JOBS = 5
TOP_K_CHUNKS = 3  # career notes chunks retrieved per mentor question

# --- Chunking params (career notes) ---
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# --- Guardrail params ---
MAX_QUESTION_LENGTH = 500