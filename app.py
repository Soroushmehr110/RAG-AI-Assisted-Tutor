# app.py — Streamlit UI (vision-first, 0–4 grading + hint on incorrect)
# - Auto-runs as soon as an image is uploaded
# - No mock mode, no OCR, no HEIC-specific handling

import os
import json
import tempfile
from datetime import datetime

import streamlit as st
from math_image_grader import run_grader, grade_with_equation_and_task

st.set_page_config(
    page_title="Math Teaching Assistant (Vision + 0–4 grading)",
    page_icon="🧮",
    layout="wide"
)

# -------- Sidebar --------
st.sidebar.header("Inputs")
uploaded_file = st.sidebar.file_uploader(
    "Upload an image of the problem",
    type=["png", "jpg", "jpeg", "webp"]
)
grade_input = st.sidebar.text_input("Student grade level", "11th grade")

# Keep timeout configurable (honored by the backend)
os.environ["OPENAI_TIMEOUT"] = os.environ.get("OPENAI_TIMEOUT", "30")
debug_on = st.sidebar.checkbox("Show debug/errors during run", value=True)

# -------- Manual mode (optional) --------
with st.expander("Manual mode (paste equation & student attempt)"):
    man_equation = st.text_area("Equation (LaTeX or text)", value="", height=120, key="_manual_eq")
    man_student  = st.text_area("Student attempt (text)", value="", height=120, key="_manual_stu")
    if st.button("Grade manual input"):
        try:
            task_obj = {"task_type": "other", "parameters": {}, "question_text": "Grade this solution."}
            graded = grade_with_equation_and_task(
                man_equation.strip(),
                grade_input,
                task_obj,
                man_student.strip()
            )
            st.success("Graded (manual mode). See results below.")
            st.session_state["_manual_solution"] = graded
        except Exception as e:
            st.error("Manual grading failed.")
            if debug_on:
                st.exception(e)

# -------- Image mode (auto-run on upload) --------
st.markdown("---")
st.markdown("## Image mode")

combined = None
human_summary = ""
solution = None

if uploaded_file is not None:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{uploaded_file.name}") as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name

        with st.spinner("Reading the image and grading..."):
            combined, human_summary = run_grader(tmp_path, grade_input, out_json_path=None)

        st.success("Done.")
        st.caption(human_summary or "")

        # ---- Show what we extracted (text + nicely rendered formula) ----
        extracted = combined.get("extracted", {}) or {}
        eq = (extracted.get("equation") or {})
        task = (extracted.get("task") or {})
        student_attempt = extracted.get("student_attempt") or ""

        st.markdown("### What we detected from the image")
        # Problem text
        st.markdown("**Problem text (task):**")
        st.write(task.get("question_text") or "(none)")
        # Equation (rendered first, fallback to ASCII, then raw LaTeX)
        st.markdown("**Equation:**")
        eq_ltx = (eq.get("latex") or "").strip()
        eq_ascii = (eq.get("ascii") or "").strip()
        if eq_ltx:
            try:
                st.latex(eq_ltx)  # pretty, typeset math
            except Exception:
                pass
        if eq_ascii:
            st.code(eq_ascii)

        # --- NEW: side-by-side input image + extracted text/formula ---
        st.markdown("### Preview")
        col_img, col_text = st.columns(2, gap="large")

        with col_img:
            st.markdown("**Input image**")
            st.image(tmp_path, use_column_width=True)

        with col_text:
            st.markdown("**Extracted problem text:**")
            st.write(task.get("question_text") or "(none)")

            st.markdown("**Extracted equation:**")
            if eq_ltx:
                try:
                    st.latex(eq_ltx)   # nicely rendered math
                except Exception:
                    pass
            if eq_ascii:
                # show ascii either as fallback or alongside LaTeX
                st.code(eq_ascii)

            st.markdown("**Student attempt:**")
            st.code(student_attempt or "(none)")

        if eq_ltx:
            with st.expander("Show raw LaTeX (debug)"):
                st.code(eq_ltx)

        # Student attempt
        st.markdown("**Student attempt (as text):**")
        st.code(student_attempt or "(none)")

        # Show extraction JSON for full transparency
        with st.expander("Extraction JSON (full)"):
            st.code(json.dumps(extracted, ensure_ascii=False, indent=2))

        solution = combined.get("solution")

        # Offer download of full JSON
        st.download_button(
            label="⬇️ Download result JSON",
            data=json.dumps(combined, ensure_ascii=False, indent=2),
            file_name=f"grader_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

    except Exception as e:
        st.error("Image grading failed.")
        if debug_on:
            st.exception(e)

# -------- Results panel --------
st.markdown("---")
st.markdown("## Grading Result (0–4)")

if solution is None:
    solution = st.session_state.get("_manual_solution")

if not solution:
    st.info("No grade to show yet. Upload an image (or use Manual mode) to see results here.")
else:
    st.write(f"**Grade:** {solution.get('grade')}")
    st.write(f"**Why:** {solution.get('explanation')}")
    st.write("**Feedback on steps:**")
    for fb in solution.get("steps_feedback", []) or []:
        st.markdown(f"- {fb}")

    # ---- Show a FIRST HINT if the student's final answer is NOT correct (hide 'false') ----
    verdict = (solution.get("final_answer_correct") or "").strip().lower()
    if verdict == "false":
        first_hint = (solution.get("first_hint") or "").strip()
        if first_hint:
            st.markdown("**Hint to start:**")
            st.info(first_hint)
        else:
            # Fallback hint if model didn't provide one
            st.markdown("**Hint to start:**")
            st.info("Find a common denominator, combine the fractions carefully, and note where denominators are zero.")
