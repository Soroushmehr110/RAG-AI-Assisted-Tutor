# backend/app/ocr_service.py
import os, json, base64, traceback
from .utils import reduce_image_to_max_bytes
from pathlib import Path
from openai import OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_VISION = os.getenv("OPENAI_MODEL_VISION", "gpt-4o")  # adjust as necessary
OPENAI_MODEL_TEXT = os.getenv("OPENAI_MODEL_TEXT", "gpt-4o")    # small text model for analysis; pick your account's available model

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else OpenAI()

def image_to_data_uri(path):
    with open(path, "rb") as f:
        data = f.read()
    suf = Path(path).suffix.lower()
    mime = "image/jpeg" if suf in [".jpg", ".jpeg"] else "image/png"
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def call_vision_once(image_path):
    """
    1) Preprocess image if > 1MB (reduce_image_to_max_bytes)
    2) Send single vision-enabled call to extract text
    Returns extracted_text (string) and optionally temp_path (to delete).
    """
    temp = None
    path_to_send = image_path
    try:
        path_to_send = reduce_image_to_max_bytes(image_path, max_bytes=1_000_000)
        if path_to_send != image_path:
            temp = path_to_send

        data_uri = image_to_data_uri(path_to_send)

        user_instruction = (
            "Extract the textual content from the image. The image contains:\n"
            "- A typed (printed) math problem (short English text, may include math notation/equations).\n"
            "- Possibly a student's handwritten attempt/solution (may contain multiple lines and arrows like '->').\n\n"
            "Return EXACTLY one JSON object and nothing else with two keys:\n"
            "  { \"extracted_text\": \"...\" }\n\n"
            "The value of 'extracted_text' should be a single string containing all text you see in the image, "
            "preserving line breaks. Do not correct the math or the student's steps here. Be literal and include arrows, punctuation, and math symbols as present.\n"
            "IMPORTANT: This is the only call that uses the image. Do not call image/vision again.\n"
        )
        content_blocks = [
            {"type":"text", "text": user_instruction},
            {"type":"image_url", "image_url": {"url": data_uri}}
        ]

        resp = openai_client.chat.completions.create(
            model=OPENAI_MODEL_VISION,
            messages=[{"role":"system","content":"You are a precise extractor. Return results strictly as instructed."},
                      {"role":"user","content": content_blocks}],
            max_tokens=1400,
            temperature=0.0
        )
        assistant_text = None
        try:
            assistant_text = resp.choices[0].message.content
        except Exception:
            assistant_text = str(resp)

        # parse JSON substring
        idx = assistant_text.find("{")
        if idx != -1:
            # simple extraction of JSON block
            # find closing brace
            stack = []
            start = None
            for i,ch in enumerate(assistant_text):
                if ch == "{":
                    if start is None:
                        start = i
                    stack.append("{")
                elif ch == "}":
                    if stack:
                        stack.pop()
                        if not stack:
                            json_text = assistant_text[start:i+1]
                            try:
                                parsed = json.loads(json_text)
                                return parsed.get("extracted_text", ""), temp
                            except:
                                break
        # fallback: return full assistant text as extracted_text
        return assistant_text.strip(), temp

    except Exception as e:
        raise RuntimeError("Vision call failed: " + str(e) + "\n" + traceback.format_exc())

def call_single_analysis_llm(extracted_text):
    """
    Single text-only LLM call to:
     - check relevance
     - segregate problem/student attempt
     - evaluate percent correctness (0,10,...100)
     - provide rationale, mistakes[], hint, confidence (0-100)
    Returns parsed dict.
    """

    system_msg = (
        "You are an expert math grader and tutor. You will receive raw extracted text from an image that "
        "contains a math problem (typed/printed) and possibly a student's handwritten attempt. "
        "Perform the following tasks carefully and return only valid JSON (no additional text):\n"
        " - 'relevant': 'yes' or 'no' (whether the content is relevant to a math course problem that a student might solve). "
        "If 'no', other fields may be empty or null.\n"
        " - 'problem': the problem statement extracted (string). If none, empty string.\n"
        " - 'student_attempt': the student's solution text (string, keep line breaks and arrows) or empty string if none.\n"
        " - 'evaluation_score': choose ONE from the set [0,10,20,30,40,50,60,70,80,90,100] representing percent correctness. Use 100 only if fully correct.\n"
        " - 'evaluation_rationale': brief (1-3 short sentences) explanation of the chosen score.\n"
        " - 'mistakes': an array (possibly empty) listing up to 6 concise mistakes found.\n"
        " - 'hint': a concise, actionable hint (1-3 sentences) to help the student proceed if incomplete or wrong. If correct, provide brief positive reinforcement.\n"
        " - 'confidence': integer 0-100 indicating confidence.\n"
        "Guidelines: be conservative; don't invent data; keep math symbols as ASCII when reproducing them. Return EXACTLY one JSON object and nothing else."
    )

    user_msg = f"EXTRACTED_TEXT:\n'''START'''\n{extracted_text}\n'''END'''\n\nNow produce the JSON described."

    resp = openai_client.chat.completions.create(
        model=OPENAI_MODEL_TEXT,
        messages=[{"role":"system","content":system_msg},{"role":"user","content":user_msg}],
        max_tokens=700,
        temperature=0.0
    )
    assistant_text = None
    try:
        assistant_text = resp.choices[0].message.content
    except Exception:
        assistant_text = str(resp)
    # extract JSON substring
    idx = assistant_text.find("{")
    if idx == -1:
        raise RuntimeError("Analysis model returned non-JSON response.")
    stack = []
    start = None
    for i,ch in enumerate(assistant_text):
        if ch == "{":
            if start is None:
                start = i
            stack.append("{")
        elif ch == "}":
            if stack:
                stack.pop()
                if not stack:
                    json_text = assistant_text[start:i+1]
                    parsed = json.loads(json_text)
                    return parsed
    raise RuntimeError("Failed to parse JSON out of analysis model output.")
