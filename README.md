# MathSight — Math Vision Grader (Demo)

## Overview
MathSight enables users to upload or capture an image that contains a math problem and a student's handwritten solution (if present). The backend processes the image and uses AI models to:

- Preprocess the image (≤ 1MB)
- Extract text using a vision-enabled model
- Analyze the extracted text using an LLM to:
  - Separate the problem statement from the student’s attempt
  - Evaluate correctness
  - Generate a helpful hint

---

## Backend Setup

### 1. Environment Variables
Create a `.env` file in the `backend` directory or export environment variables:
OPENAI_API_KEY=your_api_key_here

Optional overrides:
OPENAI_MODEL_VISION=your_vision_model
OPENAI_MODEL_TEXT=your_text_model

bash
Copy code

### 2. Install Dependencies & Run Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000



cd frontend
npm run dev


# add new email to db:
sqlite3 backend/app.db "INSERT INTO allowed_emails (email) VALUES('sample@gmail.com');"
