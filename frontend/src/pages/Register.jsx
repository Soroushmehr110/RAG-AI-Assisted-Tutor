// frontend/src/pages/Register.jsx
import React, { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

function passwordValid(pw) {
  if (!pw || pw.length < 10) return false;
  if (!/\d/.test(pw)) return false;
  if (!/[^\w\s]/.test(pw)) return false;
  return true;
}

export default function Register() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [grade, setGrade] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  async function submit(e) {
    e?.preventDefault();
    setError("");
    setMsg("");
    if (!username || !email || !password) {
      setError("Please fill username, email and password.");
      return;
    }
    if (password !== confirm) {
      setError("Password and confirmation do not match.");
      return;
    }
    if (!passwordValid(password)) {
      setError("Password must be ≥10 chars, include a number and a special character.");
      return;
    }

    setLoading(true);
    try {
      const form = new FormData();
      form.append("username", username);
      form.append("email", email);
      form.append("password", password);
      form.append("grade_level", grade);
      await axios.post("http://localhost:8000/register", form);
      setMsg("Account created. Redirecting to sign in…");
      setTimeout(() => navigate("/login"), 900);
    } catch (err) {
      setError(err.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <div style={{ marginBottom: 12 }}>
          <h2 className="title">Create account</h2>
          <div className="subtitle">Sign up to use MathSight</div>
        </div>

        <form onSubmit={submit}>
          <div className="form-row">
            <label>Username</label>
            <input value={username} onChange={e => setUsername(e.target.value)} placeholder="username" autoComplete="username" />
          </div>

          <div className="form-row">
            <label>Email (school)</label>
            <input value={email} onChange={e => setEmail(e.target.value)} placeholder="you@school.edu" autoComplete="email" />
          </div>

          <div className="form-row">
            <label>Grade level (optional)</label>
            <input value={grade} onChange={e => setGrade(e.target.value)} placeholder="e.g. 9" />
          </div>

          <div className="form-row">
            <label>Password</label>
            <input value={password} onChange={e => setPassword(e.target.value)} type="password" placeholder="Choose a strong password" autoComplete="new-password" />
          </div>

          <div className="form-row">
            <label>Confirm password</label>
            <input value={confirm} onChange={e => setConfirm(e.target.value)} type="password" placeholder="Confirm password" autoComplete="new-password" />
          </div>

          {error && <div className="err" role="alert" style={{ marginTop: 6 }}>{error}</div>}
          {msg && <div className="msg" style={{ marginTop: 6 }}>{msg}</div>}

          <div className="auth-actions" style={{ marginTop: 10 }}>
            <button type="submit" disabled={loading} className="btn btn-primary-auth">
              {loading ? "Creating..." : "Create account"}
            </button>

            <button type="button" className="btn btn-primary-auth" onClick={() => navigate("/login")}>
              Sign in
            </button>
          </div>

          <div style={{ marginTop: 10, fontSize: 12, color: "var(--muted)" }}>
            Password must be at least 10 characters and include a number and special character.
          </div>
        </form>
      </div>
    </div>
  );
}
