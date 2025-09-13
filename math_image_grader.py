"""
math_image_grader.py — Vision-first pipeline with 0–4 grading and hinting.
- No mock mode
- No OCR fallback (vision-only extraction)
- No HEIC-specific logic
- Returns a first hint when the student's final answer is incorrect
- Robust JSON parsing + response_format to avoid JSONDecodeError
"""

from __future__ import annotations
import os
import io
import json
import base64
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image, ImageOps

__all__ = ["extract_from_image", "run_grader", "grade_with_equation_and_task"]

# ---------------- Config ----------------
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")
OPENAI_TEXT_MODEL   = os.getenv("OPENAI_TEXT_MODEL",   "gpt-4o-mini")
OPENAI_TIMEOUT      = float(os.getenv("OPENAI_TIMEOUT", "30"))

# ---------------- OpenAI wrappers ----------------
_HAS_NEW_SDK = True
try:
    from openai import OpenAI
except Exception:
    _HAS_NEW_SDK = False

try:
    import openai as _OPENAI_LEGACY
except Exception:
    _OPENAI_LEGACY = None


def _require_api_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY. Please set it before running the app.")


def _extract_first_json_obj(s: str) -> Dict[str, Any]:
    """
    Robustly extract the FIRST balanced {...} JSON object from a string, ignoring any extra text
    before/after, and respecting braces inside quoted strings.
    """
    if not s:
        return {}
    # Fast path
    try:
        return json.loads(s)
    except Exception:
        pass

    in_str = False
    esc = False
    depth = 0
    start = -1
    for i, ch in enumerate(s):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                if depth > 0:
                    depth -= 1
                    if depth == 0 and start != -1:
                        candidate = s[start : i + 1]
                        try:
                            return json.loads(candidate)
                        except Exception:
                            # continue scanning in case a later balanced block parses
                            start = -1
    return {}


def _openai_chat(
    messages: List[Dict[str, Any]],
    model: str,
    temperature: float = 0,
    force_json: bool = True,
) -> str:
    """Call OpenAI chat completions with a timeout; supports new and legacy SDKs."""
    _require_api_key()
    if _HAS_NEW_SDK:
        client = OpenAI().with_options(timeout=OPENAI_TIMEOUT)
        kwargs = dict(model=model, temperature=temperature, messages=messages)
        if force_json:
            kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""
    if _OPENAI_LEGACY is None:
        raise RuntimeError("OpenAI SDK not available.")
    os.environ["OPENAI_TIMEOUT"] = str(OPENAI_TIMEOUT)  # best-effort for legacy
    # Legacy SDK doesn't support response_format; rely on our robust extractor
    resp = _OPENAI_LEGACY.ChatCompletion.create(model=model, temperature=temperature, messages=messages)
    return resp["choices"][0]["message"]["content"] or ""

# ---------------- Helpers ----------------
def _encode_image_b64_all_orientations(path: str) -> List[str]:
    """Open image, EXIF-correct, convert to PNG; return 0/90/180/270 orientations as base64 strings."""
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im.convert("RGB"))
    variants = [im, im.rotate(90, expand=True), im.rotate(180, expand=True), im.rotate(270, expand=True)]
    outs: List[str] = []
    for v in variants:
        buf = io.BytesIO()
        v.save(buf, format="PNG")
        outs.append(base64.b64encode(buf.getvalue()).decode("utf-8"))
    return outs


def _soft_accept_equation(eq_ltx: str) -> bool:
    if not eq_ltx:
        return False
    s = eq_ltx.lower()
    return "=" in s or r"\approx" in s

# ---------------- Vision prompts ----------------
VISION_EQUATION_SYS = (
    "You are a transcription assistant for math photos. "
    "Detect ONE main equation on the page (prefer the most complete). "
    "Return strict JSON: {\"equation_latex\":\"...\",\"equation_ascii\":\"...\",\"found_equals\":true|false,\"notes\":\"...\"}"
)

VISION_TASK_SYS = (
    "Extract ONLY the task/instruction statement from the photo. "
    "Return strict JSON: {\"task_type\":\"evaluate|solve_root|simplify|differentiate|integrate|other\",\"parameters\":{},\"question_text\":\"...\",\"notes\":\"...\"}"
)

VISION_STUDENT_SYS = (
    "Extract ONLY the student's written/typed attempt (not the problem text). "
    "Return strict JSON: {\"student_answer\":\"...\",\"notes\":\"...\"}"
)

GRADE_SYS = (
    "You are a strict but fair math grader. Grade on 0–4 scale:\n"
    "0 = no answer; 1 = wrong; 3 = partially correct; 4 = fully correct.\n"
    "Check domain restrictions and verify solutions conceptually (no long derivations).\n"
    "If the student's final answer is NOT correct, provide ONE short, actionable 'first hint'—"
    "a gentle next step without revealing the solution.\n"
    'Return JSON ONLY with keys exactly:\n'
    '{"steps_feedback":[...], "final_answer_correct":"true|false", "grade":0, "explanation":"...", "first_hint":""}\n'
    "- Keep first_hint under 25 words; do not include the final answer."
)

# ---------------- Vision calls (send 4 orientations) ----------------
def _vision_call(image_path: str, system_prompt: str) -> Dict[str, Any]:
    b64s = _encode_image_b64_all_orientations(image_path)
    content = [{"type": "text", "text": "Photo attached. Return JSON only per spec."}]
    content += [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b}"}} for b in b64s]
    raw = _openai_chat(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": content}],
        model=OPENAI_VISION_MODEL,
        temperature=0,
        force_json=True,
    )
    # Even with response_format, keep robust fallback for legacy SDK or imperfect outputs.
    return _extract_first_json_obj(raw)


def call_vision_extract_equation(image_path: str) -> Dict[str, Any]:
    return _vision_call(image_path, VISION_EQUATION_SYS)


def call_vision_extract_task(image_path: str) -> Dict[str, Any]:
    return _vision_call(image_path, VISION_TASK_SYS)


def call_vision_extract_student_answer(image_path: str) -> Dict[str, Any]:
    d = _vision_call(image_path, VISION_STUDENT_SYS)
    if not isinstance(d, dict):
        return {"student_answer": "", "notes": "parse_error"}
    d.setdefault("student_answer", "")
    return d

# ---------------- Public grading ----------------
def grade_with_equation_and_task(
    equation: str,
    grade_level: str,
    task: Dict[str, Any],
    student_answer: str,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """Use a text model to grade the student's solution and (if wrong) produce a first hint."""
    model = model or OPENAI_TEXT_MODEL
    user = {
        "role": "user",
        "content": [
            {"type": "text", "text": f"Equation (LaTeX): {equation}"},
            {"type": "text", "text": f"Task: {json.dumps(task, ensure_ascii=False)}"},
            {"type": "text", "text": f"Student attempt: {student_answer}"},
            {"type": "text", "text": f"Grade level: {grade_level}"}
        ]
    }
    raw = _openai_chat(
        [{"role": "system", "content": GRADE_SYS}, user],
        model=model,
        temperature=0,
        force_json=True,
    )
    res = _extract_first_json_obj(raw)

    # Guardrails / defaults
    if "grade" not in res:
        res["grade"] = 0 if not (student_answer or "").strip() else 3
        res.setdefault("explanation", "Auto-fallback grade.")
    res.setdefault("steps_feedback", [])
    res.setdefault("final_answer_correct", "")
    res.setdefault("first_hint", "")

    return res

# ---------------- Orchestrator ----------------
def extract_from_image(image_path: str) -> Dict[str, Any]:
    """Vision-first extraction: equation, task, and student's attempt."""
    # 1) Equation (LaTeX + ASCII)
    eqd = call_vision_extract_equation(image_path)
    eq_item = {}
    if isinstance(eqd, dict) and (eqd.get("found_equals") or _soft_accept_equation((eqd.get("equation_latex") or ""))):
        eq_item = {
            "latex": (eqd.get("equation_latex") or "").strip(),
            "ascii": (eqd.get("equation_ascii") or "").strip(),
        }

    # 2) Task
    task = call_vision_extract_task(image_path)
    if not isinstance(task, dict):
        task = {}

    # 3) Student's attempt
    stud = call_vision_extract_student_answer(image_path)
    student_attempt = stud.get("student_answer", "") if isinstance(stud, dict) else ""

    return {
        "equation": eq_item,
        "task": task,
        "student_attempt": student_attempt,
        "metadata": {}
    }


def run_grader(image_path: str, grade_level: str, out_json_path: Optional[str] = None) -> Tuple[Dict[str, Any], str]:
    """
    End-to-end: extract + grade. If out_json_path is provided, write results to it.
    """
    extracted = extract_from_image(image_path)
    eq_item = extracted.get("equation") or {}
    result: Dict[str, Any] = {"extracted": extracted, "solution": None}
    human_summary = "No valid equation detected."

    if eq_item:
        graded = grade_with_equation_and_task(
            equation=eq_item.get("latex", "").strip(),
            grade_level=grade_level,
            task=extracted.get("task") or {},
            student_answer=extracted.get("student_attempt", "")
        )
        result["solution"] = graded
        human_summary = "Equation extracted; grading complete."

    # Only write if a real path was supplied
    if out_json_path:
        with open(out_json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    return result, human_summary
