"""
streamlit_app.py

Module 6: SmartHire GenAI - the full portal.
Run with: streamlit run app/streamlit_app.py

UI/UX improvements in this version:
1. Match percentage instead of raw "distance" numbers
2. Sidebar showing current profile summary + a "Start Over" button
3. Guardrail/crisis messages styled distinctly (colored warning box)
4. A step-flow guide showing the 4-stage pipeline
5. A "Clear Chat" button in the AI Mentor tab
"""

import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src.parsing.loader import read_resume
from src.parsing.resume_parser import parse_resume
from src.search.job_search import search_jobs, profile_to_search_text
from src.generate.cv_suggestions import generate_cv_suggestions
from src.mentor.rag_chain import ask_mentor
from src.safety.guardrails import validate_question


st.set_page_config(page_title="SmartHire GenAI", page_icon="🎯", layout="wide")

# ---------------- SIDEBAR (Improvement #2) ----------------
with st.sidebar:
    st.header("Your Profile")

    if "profile" in st.session_state:
        profile = st.session_state["profile"]
        st.success(f"**{profile.get('name', 'Unknown')}**")
        st.write(f"🎯 Target role: {profile.get('target_role') or '—'}")
        skill_count = len(profile.get("skills", []))
        st.write(f"🛠️ {skill_count} skills detected")

        if "matches" in st.session_state:
            st.write(f"🔍 {len(st.session_state['matches'])} job matches found")
    else:
        st.info("No resume uploaded yet.\n\nGo to the **Resume Parser** tab to get started.")

    st.divider()

    if st.button("🔄 Start Over", use_container_width=True):
        for key in ["profile", "matches", "chat_history", "last_uploaded_filename"]:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state["uploader_version"] = st.session_state.get("uploader_version", 0) + 1
        st.rerun()


st.title("🎯 SmartHire GenAI")
st.caption("Resume Matching & AI Career Mentor")

# ---------------- STEP FLOW GUIDE (Improvement #4) ----------------
step1_done = "profile" in st.session_state
step2_done = "matches" in st.session_state
step1_icon = "✅" if step1_done else "1️⃣"
step2_icon = "✅" if step2_done else "2️⃣"
step3_icon = "3️⃣"
step4_icon = "4️⃣"
st.caption(
    f"{step1_icon} Upload Resume  →  {step2_icon} Find Job Matches  →  "
    f"{step3_icon} Get CV Suggestions  →  {step4_icon} Chat with Mentor"
)

tab_parse, tab_jobs, tab_suggest, tab_mentor = st.tabs(
    ["📄 Resume Parser", "🔍 Job Matches", "✨ CV Suggestions", "💬 AI Mentor"]
)

# ---------------- TAB 1: RESUME PARSER ----------------
with tab_parse:
    uploaded_file = st.file_uploader("Upload your resume (PDF or DOCX)", type=["pdf", "docx"])

    if uploaded_file is not None:
        if st.session_state.get("last_uploaded_filename") != uploaded_file.name:
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            with st.spinner("Reading and parsing resume..."):
                try:
                    resume_text = read_resume(temp_path)
                    profile = parse_resume(resume_text)
                except Exception as e:
                    st.error(f"Something went wrong: {e}")
                    st.stop()
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

            st.session_state["profile"] = profile
            st.session_state["last_uploaded_filename"] = uploaded_file.name

        profile = st.session_state["profile"]

        st.success(f"Parsed profile for **{profile['name']}**")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Target Role")
            st.write(profile.get("target_role", "—"))
            st.subheader("Skills")
            st.write(", ".join(profile.get("skills", [])) or "—")
        with col2:
            st.subheader("Experience")
            for exp in profile.get("experience", []):
                st.markdown(f"**{exp.get('title','')}** — {exp.get('company','')} ({exp.get('duration','')})")
            st.subheader("Education")
            for edu in profile.get("education", []):
                st.markdown(f"- {edu.get('degree','')}, {edu.get('institution','')}")

        with st.expander("Raw parsed JSON"):
            st.json(profile)

        st.info("👉 Head to the **Job Matches** tab next.")
    else:
        st.info("Upload a resume above to get started.")

# ---------------- TAB 2: JOB MATCHES ----------------
with tab_jobs:
    if "profile" not in st.session_state:
        st.info("Upload and parse a resume in the first tab to see job matches.")
    else:
        profile = st.session_state["profile"]

        if st.button("Find Matching Jobs"):
            search_text = profile_to_search_text(profile)

            with st.spinner("Searching job index..."):
                try:
                    matches = search_jobs(search_text, top_n=5)
                except Exception as e:
                    st.error(f"Job search failed: {e}")
                    st.stop()

            st.session_state["matches"] = matches

        if "matches" in st.session_state:
            st.subheader("Top Matching Jobs")
            for i, job in enumerate(st.session_state["matches"], start=1):
                with st.container(border=True):
                    top_row = st.columns([4, 1])
                    with top_row[0]:
                        st.markdown(f"**{i}. {job['title']}** at {job['company_name']} ({job['location']})")
                    with top_row[1]:
                        match_pct = job.get("match_percentage")
                        if match_pct is not None:
                            st.metric("Match", f"{match_pct:.0f}%")
                    st.write(job.get("description", "")[:300] + "...")

            st.info("👉 Head to the **CV Suggestions** tab next.")

# ---------------- TAB 3: CV SUGGESTIONS ----------------
with tab_suggest:
    if "profile" not in st.session_state or "matches" not in st.session_state:
        st.info("Upload a resume and find job matches first (Tabs 1 and 2).")
    else:
        profile = st.session_state["profile"]
        matches = st.session_state["matches"]

        job_titles = [f"{i+1}. {job['title']} at {job['company_name']}" for i, job in enumerate(matches)]
        selected_index = st.selectbox("Pick a target job", range(len(matches)), format_func=lambda i: job_titles[i])

        if st.button("Generate CV Suggestions"):
            target_job = matches[selected_index]

            with st.spinner("Generating suggestions..."):
                try:
                    suggestions = generate_cv_suggestions(profile, target_job)
                except Exception as e:
                    st.error(f"Suggestion generation failed: {e}")
                    st.stop()

            st.markdown(suggestions)

# ---------------- TAB 4: AI MENTOR ----------------
with tab_mentor:
    header_row = st.columns([5, 1])
    with header_row[0]:
        st.write("Ask a career-related question. The mentor answers using its career notes knowledge base.")
    with header_row[1]:
        if st.button("🗑️ Clear Chat"):
            st.session_state["chat_history"] = []
            st.rerun()

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    CRISIS_MARKERS = ["crisis line", "helpline", "kiran mental health", "vandrevala", "icall"]

    def is_crisis_message(text):
        lowered = text.lower()
        return any(marker in lowered for marker in CRISIS_MARKERS)

    for role, message in st.session_state["chat_history"]:
        with st.chat_message(role):
            if role == "assistant" and is_crisis_message(message):
                st.warning(message)
            else:
                st.write(message)

    user_question = st.chat_input("Ask the AI Career Mentor...")

    if user_question:
        st.session_state["chat_history"].append(("user", user_question))

        is_valid, reason = validate_question(user_question)

        if not is_valid:
            answer = reason
        else:
            with st.spinner("Thinking..."):
                answer, used_chunks = ask_mentor(user_question)
                if used_chunks:
                    sources = ", ".join(set(c["source_file"] for c in used_chunks))
                    answer = answer + f"\n\n*Sources: {sources}*"

        st.session_state["chat_history"].append(("assistant", answer))
        st.rerun()
