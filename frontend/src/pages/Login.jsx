// frontend/src/pages/Login.jsx
import React, { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

export default function Login({ onLogin }) {
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e?.preventDefault();
    setError("");
    if (!identifier || !password) {
      setError("Please enter both username/email and password.");
      return;
    }
    setLoading(true);
    try {
      const body = new URLSearchParams();
      body.append("username", identifier);
      body.append("password", password);
      const res = await axios.post("http://localhost:8000/token", body.toString(), {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      const token = res.data.access_token;
      if (token) {
        localStorage.setItem("token", token);
        if (onLogin) onLogin(token);
        navigate("/");
      } else {
        setError("Unexpected server response.");
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed — check credentials.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <div style={{ marginBottom: 12 }}>
          <h2 className="title">Sign in</h2>
          <div className="subtitle">Access your MathSight workspace</div>
        </div>

        <form onSubmit={submit} aria-label="Sign in form">
          <div className="form-row">
            <label>Username or email</label>
            <input
              value={identifier}
              onChange={e => setIdentifier(e.target.value)}
              placeholder="yourname or email@example.com"
              autoComplete="username"
            />
          </div>

          <div className="form-row" style={{ position: "relative" }}>
            <label>Password</label>
            <input
              type={show ? "text" : "password"}
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Enter your password"
              autoComplete="current-password"
            />
            <button type="button" className="password-toggle" onClick={() => setShow(s => !s)}>
              {show ? "Hide" : "Show"}
            </button>
          </div>

          {error && <div className="err" role="alert" style={{ marginTop: 6 }}>{error}</div>}

          <div className="auth-actions" style={{ marginTop: 10 }}>
            <button type="submit" className="btn btn-primary-auth" disabled={loading}>
              {loading ? "Signing in..." : "Sign in"}
            </button>

            <button type="button" className="btn btn-primary-auth" onClick={() => navigate("/register")}>
              Create account
            </button>
          </div>

          <div className="form-footer" style={{ marginTop: 12 }}>
            <button type="button" onClick={() => navigate("/forgot-password")} style={{ background: "transparent", border: "none", color: "var(--accent)", cursor: "pointer", padding: 0 }}>
              Forgot password?
            </button>

            <div />
          </div>
        </form>
      </div>
    </div>
  );
}
