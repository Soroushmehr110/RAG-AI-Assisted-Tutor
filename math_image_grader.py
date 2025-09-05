"""
math_image_grader.py — Vision-first, task-aware pipeline
- Vision extracts BOTH:
  (A) the main equation (LaTeX + ASCII)
  (B) the task intent (evaluate/solve_roots/vertex/intercepts/graph/simplify/other) + parameters (e.g., x=1)
- Validator handles equalities (lhs=rhs) by converting to (lhs)-(rhs) and normalizes implicit multiplication.
- Grader is task-aware and produces the correct kind of steps/answer for the detected task.
"""

from __future__ import annotations
import os, json, base64, logging, re as _re
from typing import Dict, Any, Optional, List, Tuple
from io import BytesIO
from PIL import Image, ImageOps
import numpy as np

# Optional: SymPy for validation
try:
    import sympy as sp
except Exception:
    sp = None

# OpenAI clients (support both new and legacy)
try:
    from openai import OpenAI
    _HAS_NEW = True
except Exception:
    _HAS_NEW = False

try:
    import openai as _LEGACY_OPENAI
except Exception:
    _LEGACY_OPENAI = None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")
OPENAI_TEXT_MODEL   = os.getenv("OPENAI_TEXT_MODEL",   "gpt-4o-mini")
USE_VISION_FIRST    = os.getenv("USE_VISION_FIRST", "1") == "1"

# ---------------------------
# OpenAI helpers
# ---------------------------
def _require_api_key():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Please set OPENAI_API_KEY")

def _openai_chat(messages: List[Dict[str, Any]], model: str, temperature: float = 0) -> str:
    _require_api_key()
    if _HAS_NEW:
        client = OpenAI()
        resp = client.chat.completions.create(model=model, temperature=temperature, messages=messages)
        return resp.choices[0].message.content.strip()
    if _LEGACY_OPENAI is None:
        raise RuntimeError("OpenAI SDK not available")
    resp = _LEGACY_OPENAI.ChatCompletion.create(model=model, temperature=temperature, messages=messages)
    return resp["choices"][0]["message"]["content"].strip()

def _encode_image_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# ---------------------------
# Vision: equation extraction
# ---------------------------
VISION_EQUATION_SYS = (
    "You are a rigorous math transcription assistant. Read the photo and transcribe the main function/equation that defines f(x) (or the central formula). "
    "Do not solve.\n\n"
    "Output JSON only:\n"
    "{\n"
    '  "equation_latex": "<LaTeX, e.g., f(x) = -2x^{2} - 2x + 4>",\n'
    '  "equation_ascii": "<ASCII, e.g., f(x) = -2*x^2 - 2*x + 4>",\n'
    '  "found_equals": true,\n'
    '  "notes": "<where you found it; any uncertainty>"\n'
    "}\n"
    "Rules: preserve signs/exponents; if multiple appear, pick the function definition with f(x)=...; valid JSON only."
)

def call_vision_extract_equation(image_path: str, model: Optional[str] = None) -> Dict[str, Any]:
    model = model or OPENAI_VISION_MODEL
    img_b64 = _encode_image_b64(image_path)
    messages = [
        {"role": "system", "content": VISION_EQUATION_SYS},
        {"role": "user", "content": [
            {"type": "text", "text": "Photo attached. Return JSON per spec."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
        ]}
    ]
    raw = _openai_chat(messages, model=model, temperature=0)
    try:
        return json.loads(raw)
    except Exception:
        s, e = raw.find("{"), raw.rfind("}")
        return json.loads(raw[s:e+1]) if s != -1 and e != -1 else {}

# ---------------------------
# Vision: task extraction
# ---------------------------
VISION_TASK_SYS = (
    "You extract ONLY the task the problem asks for, not the equation. "
    "Read the photo and summarize the requested action.\n\n"
    "Output JSON only:\n"
    "{\n"
    '  "task_type": "evaluate|solve_roots|vertex|intercepts|graph|simplify|differentiate|integrate|other",\n'
    '  "parameters": {"x": 1},\n'
    '  "question_text": "<verbatim or short paraphrase of the instruction>",\n'
    '  "notes": "<uncertainty or alternatives if any>"\n'
    "}\n"
    "Rules:\n"
    "- If it says evaluate f(a), task_type=evaluate and parameters.x=a.\n"
    "- If it says solve f(x)=0 or find zeros/roots/x-intercepts, task_type=solve_roots.\n"
    "- If it asks vertex, task_type=vertex; if intercepts, task_type=intercepts; if graph features, task_type=graph.\n"
    "- If unclear, set task_type=other and summarize in notes.\n"
    "- JSON only."
)

def call_vision_extract_task(image_path: str, model: Optional[str] = None) -> Dict[str, Any]:
    model = model or OPENAI_VISION_MODEL
    img_b64 = _encode_image_b64(image_path)
    messages = [
        {"role": "system", "content": VISION_TASK_SYS},
        {"role": "user", "content": [
            {"type": "text", "text": "Photo attached. Return JSON per spec."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
        ]}
    ]
    raw = _openai_chat(messages, model=model, temperature=0)
    try:
        return json.loads(raw)
    except Exception:
        s, e = raw.find("{"), raw.rfind("}")
        return json.loads(raw[s:e+1]) if s != -1 and e != -1 else {}

# ---------------------------
# Validation helpers
# ---------------------------
def _normalize_for_sympy(expr: str) -> str:
    if not expr:
        return expr
    expr = expr.replace("−", "-").replace("–", "-").replace("—", "-")
    # 2x -> 2*x ; x2 -> x*2
    expr = _re.sub(r'(\d)\s*([A-Za-z])', r'\1*\2', expr)
    expr = _re.sub(r'([A-Za-z])\s*(\d)', r'\1*\2', expr)
    # )x -> )*x ; x( -> x*( ; 3( -> 3*(
    expr = _re.sub(r'(\))\s*([A-Za-z])', r'\1*\2', expr)
    expr = _re.sub(r'([A-Za-z])\s*\(', r'\1*(', expr)
    expr = _re.sub(r'(\d)\s*\(', r'\1*(', expr)
    expr = _re.sub(r'\)\s*(\d)', r')*\1', expr)
    return expr

def _equation_to_single_expr(expr_text: str) -> str:
    s = expr_text.strip()
    # If it's f(x)=... or y=..., just use RHS
    if "=" in s and (s.lower().startswith("f(x)") or s.lower().startswith("y")):
        return s.split("=", 1)[1].strip()
    if "=" in s:
        lhs, rhs = s.split("=", 1)
        return f"({lhs.strip()}) - ({rhs.strip()})"
    return s

def validate_polynomial(expr_text: str) -> bool:
    """Accept any polynomial in x (including equalities)."""
    if sp is None:
        return True
    try:
        x = sp.symbols('x')
        expr = _equation_to_single_expr(expr_text)
        expr_py = expr.replace("^{", "**(").replace("}", ")").replace("^", "**")
        expr_py = _normalize_for_sympy(expr_py)
        poly = sp.sympify(expr_py, dict(x=x))
        sp.Poly(poly, x)  # will raise if not a polynomial in x
        return True
    except Exception:
        return False

def pick_equation(vis_eq: Dict[str, Any]) -> str:
    return (vis_eq or {}).get("equation_latex") or (vis_eq or {}).get("equation_ascii") or ""

# ---------------------------
# Grader (task-aware)
# ---------------------------
GRADE_SYS = (
    "You are a patient math tutor. You will be given the problem's function/equation and a task object. "
    "Follow the task exactly. Explain step-by-step, then give a concise final answer.\n\n"
    "Return strict JSON only:\n"
    "{\n"
    '  "steps": ["...","..."],\n'
    '  "final_answer": "<string>",\n'
    '  "solution_confidence": 0.0\n'
    "}\n"
    "Rules:\n"
    "- Do not invent inputs. If task_type=evaluate but parameters.x is missing, explain what is missing and leave final_answer empty.\n"
    "- If task_type=solve_roots, solve f(x)=0 (zeros/x-intercepts) using factoring or quadratic formula.\n"
    "- If task_type=vertex, compute vertex (h,k) and state axis of symmetry.\n"
    "- If task_type=intercepts, give x- and y-intercepts.\n"
    "- Keep language at the student's grade level; be clear and brief."
)

def grade_with_equation_and_task(equation: str, grade_level: str, task: Dict[str, Any], model: Optional[str] = None) -> Dict[str, Any]:
    model = model or OPENAI_TEXT_MODEL
    user = {
        "role": "user",
        "content": (
            f"Equation: {equation}\n"
            f"Task object: {json.dumps(task, ensure_ascii=False)}\n"
            f"Student grade level: {grade_level}\n"
            "Follow the JSON schema exactly."
        )
    }
    raw = _openai_chat([{"role": "system", "content": GRADE_SYS}, user], model=model, temperature=0)
    try:
        return json.loads(raw)
    except Exception:
        s, e = raw.find("{"), raw.rfind("}")
        return json.loads(raw[s:e+1]) if s != -1 and e != -1 else {"steps": [], "final_answer": "", "solution_confidence": 0.0}

# ---------------------------
# Public entry points
# ---------------------------
def extract_from_image(image_path: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {"problem_definition": [], "raw_vision": None, "task": None, "metadata": {"notes": []}}

    if USE_VISION_FIRST:
        try:
            vis_eq = call_vision_extract_equation(image_path)
            vis_task = call_vision_extract_task(image_path)
            out["raw_vision"] = {"equation": vis_eq}
            out["task"] = vis_task

            eq = pick_equation(vis_eq)
            if eq and validate_polynomial(eq):
                out["problem_definition"].append({
                    "id": "equation_normalized",
                    "type": "equation",
                    "latex": eq,
                    "notes": "chosen_from=vision"
                })
            else:
                out["metadata"]["notes"].append("Vision extracted equation but failed validation or was empty.")
        except Exception as e:
            out["metadata"]["notes"].append(f"Vision error: {e}")
    return out

def run_grader(image_path: str, grade_level: str, out_json_path: str = "grader_output.json") -> Tuple[Dict[str, Any], str]:
    extracted = extract_from_image(image_path)
    eq_item = next((it for it in extracted["problem_definition"] if it.get("id") == "equation_normalized"), None)
    task = extracted.get("raw_vision", {}).get("task") or extracted.get("task")  # support older callers

    result: Dict[str, Any] = {"extracted": extracted, "solution": None}
    human_summary = ""

    if eq_item:
        eq = eq_item.get("latex", "")
        task_obj = task or {"task_type": "other", "parameters": {}, "question_text": "", "notes": "No task detected; provide general guidance."}
        graded = grade_with_equation_and_task(eq, grade_level, task_obj)
        result["solution"] = graded
        human_summary = f"Detected equation: {eq}. Task: {task_obj.get('task_type','other')}."

    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result, human_summary
