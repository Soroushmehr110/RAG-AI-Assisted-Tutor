# app.py — Streamlit UI (vision-first, task-aware)
import os
import json
import tempfile
from datetime import datetime
from urllib.parse import quote

import streamlit as st

from math_image_grader import run_grader, grade_with_equation_and_task

st.set_page_config(
    page_title="Math Teaching Assistant (Vision-first, Task-aware)",
    page_icon="🧮",
    layout="wide",
)

# ---------------- Sidebar ----------------
st.sidebar.header("Inputs")
uploaded_file = st.sidebar.file_uploader(
    "Upload an image of the problem",
    type=["png", "jpg", "jpeg", "webp", "heic", "pdf"],
)
grade_input = st.sidebar.text_input("Student grade level", "11th grade")

use_vision = st.sidebar.checkbox("Use Vision (no OCR)", value=True)
os.environ["USE_VISION_FIRST"] = "1" if use_vision else "0"

run_button = st.sidebar.button("Run")

# ---------------- Helpers ----------------
def save_temp_file(upload) -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix="-" + upload.name.replace(" ", "_"))
    tmp.write(upload.read())
    tmp.flush()
    return tmp.name

def download_link_for_json(data: dict, path: str) -> str:
    payload = quote(json.dumps(data), safe="")
    filename = path.split("/")[-1]
    return f'<a href="data:application/json;charset=utf-8,{payload}" download="{filename}">Download JSON</a>'

def safe_markdown(text: str):
    if text:
        st.markdown(text)

# ---------------- Main ----------------
st.title("🧮 Math Teaching Assistant (Vision-first, Task-aware)")
st.write(
    "This app reads your **image** directly to extract the *equation* **and** the *task* "
    "(e.g., evaluate at x=1, solve roots, vertex, intercepts), validates it, and then explains the solution step-by-step. "
    "If vision fails, you can still edit the fields and re-run."
)

if run_button:
    if uploaded_file is None:
        st.error("Please upload an image first.")
        st.stop()

    tmp_path = save_temp_file(uploaded_file)
    st.success(f"Saved to `{tmp_path}`")

    out_json_path = f"grader_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    combined, human_summary = run_grader(tmp_path, grade_input, out_json_path)

    # Always show the uploaded image for context
    with st.expander("Uploaded image preview", expanded=True):
        st.image(tmp_path, caption=uploaded_file.name, use_column_width=True)

    # ---------------- Detected equation (editable) ----------------
    st.markdown("---")
    st.subheader("Detected equation (editable)")

    eq_candidates = []
    try:
        for item in combined.get("extracted", {}).get("problem_definition", []):
            if isinstance(item, dict) and item.get("type") == "equation":
                eq_candidates.append(item.get("latex"))
    except Exception:
        pass
    eq_text = eq_candidates[0] if eq_candidates else ""
    eq_text = st.text_input(
        "LaTeX / plain equation",
        value=eq_text,
        help="Fix any extraction mistakes here (e.g., add missing ^ or signs).",
    )
    if eq_text:
        # Show LaTeX rendering for quick visual check
        st.latex(eq_text if eq_text.strip().startswith("$") else f"{eq_text}")

    # ---------------- Detected task (editable) ----------------
    st.markdown("---")
    st.subheader("Detected task (editable)")

    # try both locations (depending on which version of the backend)
    det_task = (
        combined.get("extracted", {}).get("task")
        or combined.get("extracted", {}).get("raw_vision", {}).get("task")
        or combined.get("extracted", {}).get("raw_vision", {})  # in case task got nested oddly
        or {}
    )

    task_types = [
        "evaluate",
        "solve_roots",
        "vertex",
        "intercepts",
        "graph",
        "simplify",
        "differentiate",
        "integrate",
        "other",
    ]
    default_idx = task_types.index(det_task.get("task_type", "other")) if det_task.get("task_type", "other") in task_types else task_types.index("other")
    task_type = st.selectbox("Task type", task_types, index=default_idx)

    params = det_task.get("parameters") or {}
    # Only meaningful for evaluate; harmless otherwise
    x_val = st.number_input("x (for evaluate)", value=float(params.get("x", 0.0)))
    question_text = st.text_input("Question text (optional)", value=det_task.get("question_text", ""))
    notes_text = st.text_input("Notes (optional)", value=det_task.get("notes", ""))

    edited_task = {
        "task_type": task_type,
        "parameters": {"x": x_val} if task_type == "evaluate" else params,
        "question_text": question_text,
        "notes": notes_text,
    }

    # ---------------- Actions ----------------
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Re-run grading with edited equation & task"):
            if not eq_text.strip():
                st.error("Please provide an equation above before re-running.")
            else:
                graded = grade_with_equation_and_task(eq_text.strip(), grade_input, edited_task)
                combined["solution"] = graded
                combined.setdefault("extracted", {})["task"] = edited_task
                st.success("Re-ran grading with your edits.")

    with col2:
        st.write("")  # spacer
        st.write("")

    # ---------------- Render solution ----------------
    st.markdown("---")
    st.subheader("Solution")
    sol = combined.get("solution")
    if not sol:
        st.info("No solution produced yet. You can edit the equation/task above and click re-run.")
    else:
        steps = sol.get("steps", [])
        for i, s in enumerate(steps, start=1):
            st.markdown(f"**Step {i}:**")
            safe_markdown(str(s))
        final = sol.get("final_answer")
        if final:
            st.markdown("**Final answer:**")
            safe_markdown(str(final))
        conf = sol.get("solution_confidence")
        if conf is not None:
            st.caption(f"Solution confidence: {conf}")

    # ---------------- Debug + Download ----------------
    with st.expander("Raw outputs (debug)"):
        st.json(combined)

    st.markdown(download_link_for_json(combined, out_json_path), unsafe_allow_html=True)
