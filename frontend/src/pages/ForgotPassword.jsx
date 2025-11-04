// frontend/src/pages/ForgotPassword.jsx
import React, { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

export default function ForgotPassword() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  async function submit(e) {
    e?.preventDefault();
    setErr(""); setMsg("");
    if (!email) { setErr("Please enter your email."); return; }
    setLoading(true);
    try {
      // If you have a backend endpoint to handle this, point to it.
      // For now we'll just simulate success.
      // await axios.post("http://localhost:8000/forgot-password", { email });
      setMsg("If that email exists, a reset link has been sent (simulated).");
      setTimeout(() => navigate("/login"), 2500);
    } catch (error) {
      setErr("Unable to send reset link (server error).");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <div style={{ marginBottom: 12 }}>
          <h2 className="title">Forgot password</h2>
          <div className="subtitle">Enter your email to receive a reset link</div>
        </div>

        <form onSubmit={submit}>
          <div className="form-row">
            <label>Email</label>
            <input value={email} onChange={e => setEmail(e.target.value)} placeholder="you@school.edu" autoComplete="email" />
          </div>

          {err && <div className="err" role="alert" style={{ marginTop: 6 }}>{err}</div>}
          {msg && <div className="msg" style={{ marginTop: 6 }}>{msg}</div>}

          <div className="auth-actions" style={{ marginTop: 10 }}>
            <button type="submit" className="btn btn-primary-auth" disabled={loading}>
              {loading ? "Sending..." : "Send reset link"}
            </button>
            <button type="button" className="btn btn-primary-auth" onClick={() => navigate("/login")}>
              Back to sign in
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
