# Math-Teaching-Assistant

Lightweight tool that converts a math problem (student work allowed) into a structured, graded result using OCR + a large language model.
It extracts the problem, understands the math, grades student attempts, generates step-by-step solutions, and provides scaffolded hints — all presented in a clean UI.

---

## Features

* Image upload (PNG / JPG / JPEG / BMP) → OCR → LLM-based grading pipeline
* Extracts problem statement and (if present) the student's attempt
* Produces: problem restatement, topic, difficulty, full solution, scored rubric, component scores, and up to 3 hints (sorted)
* Simple UI with math-aware inline rendering (Markdown + MathJax)
* Downloadable structured JSON result for each run
* Defensive parsing to handle a variety of grader outputs (strings, dicts, lists, None)

---

## Quick start

### Prerequisites

* Python 3.10+
* `pip` (or `poetry`)
* An OpenAI API key set in the environment variable `OPENAI_API_KEY` (the grader uses the OpenAI API)

### Install system dependencies (Tesseract)

* Ubuntu / Debian:

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr
```

* macOS (Homebrew):

```bash
brew install tesseract
```

### Create & activate virtual environment

```bash
python -m venv .venv
source .venv/bin/activate         # macOS / Linux
.venv\Scripts\activate            # Windows (PowerShell)
```

### Install Python dependencies

Create a `requirements.txt` containing your dependencies (example below) and then:

```bash
pip install -r requirements.txt
```

### Configure environment

Ensure your OpenAI API key is set:

```bash
export OPENAI_API_KEY="sk-...yourkey..."   # macOS / Linux
# Windows (PowerShell)
# setx OPENAI_API_KEY "sk-...yourkey..."
```

### Run the app

```bash
streamlit run app.py
```

Open the local URL printed by Streamlit (e.g. `http://localhost:8501`) and upload an image.

---

## Output JSON (example snippet)

```json
{
  "grader_result": {
    "problem_text": "Solve: 2(x+3)-3(y-2)=6",
    "topic": "Algebra",
    "difficulty_assessment": "Medium",
    "solution": {
      "steps": [
        "Expand: 2x+6-3y+6 = 6",
        "Simplify: 2x - 3y + 12 = 6",
        "Solve for x in terms of y: 2x = 3y - 6 => x = (3y-6)/2"
      ],
      "final_answer": "x = (3y-6)/2"
    },
    "student_attempt": null,
    "score": 0,
    "component_scores": {
      "understanding": 0,
      "execution": 0,
      "accuracy": 0
    },
    "hints_sorted": [
      "Start by expanding the left-hand side.",
      "Combine like terms.",
      "Isolate one variable in terms of the other."
    ],
    "first_hint": "Start by expanding the left-hand side."
  },
  "generated_at": "2025-08-25T17:18:07.472Z",
  "source_file": "question1.png"
}
```

---

## Repository layout

```
math-teaching-assistant/
├─ app.py                     # Streamlit UI
├─ math_image_grader.py       # OCR + LLM grader pipeline (exposes run_grader)
├─ requirements.txt
├─ README.md
├─ examples/
│  ├─ question1.png
│  └─ sample_result.json
├─ outputs/                   # where grader outputs are stored (auto-generated filenames)
└─ tests/
```

---

## License

This project is released under the **MIT License**. See `LICENSE` for details.

# math-teaching-assistant
