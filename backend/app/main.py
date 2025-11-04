# backend/app/main.py
import os
import traceback
import tempfile
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from . import database, models, schemas, auth, ocr_service, utils
from .database import SessionLocal, engine
from fastapi.middleware.cors import CORSMiddleware

import os
import smtplib
from email.message import EmailMessage
from jose import jwt, JWTError
from datetime import timedelta
from .allowed_utils import load_emails_from_json, normalize_email, email_in_list


models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Math Vision Grader")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to your frontend host in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/register", response_model=schemas.UserOut)
def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    grade_level: str = Form(None),
    db: Session = Depends(get_db),
):
    # check allowed email (DB + runtime JSON)
    # normalize incoming email
    email_norm = normalize_email(email)

    # load from DB (normalize). Be robust to different return shapes.
    allowed_from_db = []
    try:
        rows = db.query(models.AllowedEmail.email).all()
        # rows may be list of tuples like [(email,), ...] or list of scalars depending on ORM
        for r in rows:
            if isinstance(r, (list, tuple)):
                val = r[0]
            else:
                val = r
            if val is None:
                continue
            allowed_from_db.append(str(val).strip().lower())
    except Exception:
        # on any DB read error, treat DB list as empty and rely on JSON
        allowed_from_db = []

    # load allowed emails from JSON (runtime); this function returns normalized emails
    allowed_from_json = load_emails_from_json()  # already normalized

    # combine and deduplicate
    combined_allowed = list(dict.fromkeys(allowed_from_db + allowed_from_json))
    # finally check membership
    if email_norm not in combined_allowed:
        raise HTTPException(status_code=400, detail="Email is not authorized to register.")

    # password policy
    if not utils.is_password_valid(password):
        raise HTTPException(
            status_code=400,
            detail="Password does not meet policy (>=10 chars, number, special char).",
        )
    # uniqueness
    if db.query(models.User).filter(models.User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already taken.")
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")
    user = models.User(
        username=username,
        email=email,
        hashed_password=auth.get_password_hash(password),
        grade_level=grade_level,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username/email or password")
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# ---------- Password reset helpers ----------
RESET_TOKEN_EXP_MINUTES = int(os.getenv("RESET_TOKEN_EXP_MINUTES", "60"))  # 60 minutes default
RESET_JWT_SECRET = os.getenv("RESET_JWT_SECRET", os.getenv("SECRET_KEY", "CHANGE_ME_TO_A_SECURE_RANDOM_KEY"))
RESET_JWT_ALGO = "HS256"

def create_password_reset_token(email: str, expires_minutes: int = RESET_TOKEN_EXP_MINUTES) -> str:
    payload = {"sub": email, "type": "pw_reset"}
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    payload.update({"exp": expire})
    return jwt.encode(payload, RESET_JWT_SECRET, algorithm=RESET_JWT_ALGO)

def verify_password_reset_token(token: str) -> str:
    """
    Returns email if token is valid, otherwise raises JWTError.
    """
    payload = jwt.decode(token, RESET_JWT_SECRET, algorithms=[RESET_JWT_ALGO])
    if payload.get("type") != "pw_reset":
        raise JWTError("Invalid token type")
    return payload.get("sub")

def send_reset_email(to_email: str, reset_link: str):
    """
    Send reset link via SMTP if SMTP env vars configured:
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM
    If not configured, this will raise or you can bypass for dev.
    """
    SMTP_HOST = os.getenv("SMTP_HOST")
    if not SMTP_HOST:
        raise RuntimeError("SMTP not configured")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")
    FROM = os.getenv("SMTP_FROM", SMTP_USER)

    msg = EmailMessage()
    msg["Subject"] = "Password reset for MathSight"
    msg["From"] = FROM
    msg["To"] = to_email
    msg.set_content(f"Hello,\n\nUse the link below to reset your password (valid for {RESET_TOKEN_EXP_MINUTES} minutes):\n\n{reset_link}\n\nIf you didn't request this, ignore this message.\n")
    # Send via TLS
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        if SMTP_USER and SMTP_PASS:
            smtp.login(SMTP_USER, SMTP_PASS)
        smtp.send_message(msg)

# ---------- API endpoints ----------
from fastapi import Body

@app.post("/request-password-reset")
def request_password_reset(email: str = Body(..., embed=True), db: Session = Depends(get_db)):
    """
    Request a password reset link for the given email.
    If SMTP is properly configured, an email will be sent.
    For local dev, if SMTP not configured, the endpoint returns the token (only for dev/test).
    """
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        # Do not reveal whether email exists -> return generic message for security
        return {"ok": True, "message": "If the email is registered, a reset link has been sent."}

    token = create_password_reset_token(email)
    # Build reset link -> frontend should have a reset route that accepts token
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    reset_link = f"{FRONTEND_ORIGIN}/reset-password?token={token}"
    smtp_configured = bool(os.getenv("SMTP_HOST"))

    if smtp_configured:
        try:
            send_reset_email(email, reset_link)
            return {"ok": True, "message": "If the email is registered, a reset link has been sent."}
        except Exception as e:
            # Log server-side and return generic message
            print("Error sending reset email:", e)
            return {"ok": True, "message": "If the email is registered, a reset link has been sent."}
    else:
        # Dev mode: return token so you can test quickly (DO NOT do this in production)
        return {"ok": True, "message": "DEV_MODE_TOKEN_RETURNED", "token": token, "reset_link": reset_link}

@app.post("/reset-password")
def reset_password(token: str = Body(...), new_password: str = Body(...), db: Session = Depends(get_db)):
    """
    Reset password using token and new password.
    Token should be the JWT created earlier.
    """
    # Validate password policy first
    if not utils.is_password_valid(new_password):
        raise HTTPException(status_code=400, detail="Password does not meet policy (>=10 chars, include number and special char).")
    try:
        email = verify_password_reset_token(token)
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token.")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token (user not found).")
    # Hash new password and update
    user.hashed_password = auth.get_password_hash(new_password)
    db.add(user)
    db.commit()
    return {"ok": True, "message": "Password updated successfully."}



def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from jose import jwt, JWTError

    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@app.get("/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.post("/analyze-image", response_model=schemas.OCRResult)
async def analyze_image(file: UploadFile = File(...), current_user: models.User = Depends(get_current_user)):
    """
    Endpoint:
    - Accepts uploaded image (multipart/form-data)
    - Saves it to a temp file
    - Calls ocr_service.call_vision_once (single vision model call)
    - Calls ocr_service.call_single_analysis_llm (single analysis call)
    - Returns extracted_text and analysis dict
    """
    tmp_input = None
    temp_preprocessed = None
    try:
        # Save uploaded file temporarily with original extension
        suffix = Path(file.filename).suffix if file.filename else ".png"
        tmp_input = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        contents = await file.read()
        tmp_input.write(contents)
        tmp_input.flush()
        tmp_input.close()
        image_path = tmp_input.name

        # Vision call once -> extracted_text, may create an internal preprocessed temp file
        extracted_text, temp_created = ocr_service.call_vision_once(image_path)
        temp_preprocessed = temp_created

        # Single LLM analysis call
        analysis = ocr_service.call_single_analysis_llm(extracted_text)

        # cleanup temp files
        try:
            if tmp_input:
                os.remove(image_path)
        except Exception:
            pass
        try:
            if temp_preprocessed:
                os.remove(temp_preprocessed)
        except Exception:
            pass

        result = {"extracted_text": extracted_text, "analysis": analysis}
        return result

    except Exception as e:
        traceback.print_exc()
        # try to remove temp files on error
        try:
            if tmp_input:
                os.remove(tmp_input.name)
        except Exception:
            pass
        try:
            if temp_preprocessed:
                os.remove(temp_preprocessed)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")
