// frontend/src/App.jsx
import React, { useState } from "react";
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useLocation } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";

/* Header component (no left logo/title) */
function Header({ token, onLogout }) {
  const location = useLocation();
  const hideAuthLinks = location.pathname === "/login" || location.pathname === "/register";

  return (
    <header className="sticky top-0 z-30 bg-white/70 border-b border-gray-100">
      <div className="max-w-5xl mx-auto flex items-center justify-between px-6 py-3">
        {/* left placeholder to keep spacing consistent */}
        <div style={{ width: 36 }} />

        <nav className="flex items-center gap-3">
          {/* hide auth links when on the auth pages to avoid duplicate CTAs */}
          {!hideAuthLinks ? (
            token ? (
              <button onClick={onLogout} className="btn-ghost">Sign out</button>
            ) : (
              <>
                <Link to="/login" className="text-sm text-gray-700">Sign in</Link>
                <Link to="/register" className="btn-primary text-sm">Create account</Link>
              </>
            )
          ) : (
            token ? <button onClick={onLogout} className="btn-ghost">Sign out</button> : null
          )}
        </nav>
      </div>
    </header>
  );
}

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("token") || "");

  const onLogin = (tok) => {
    setToken(tok);
    localStorage.setItem("token", tok);
  };
  const onLogout = () => {
    setToken("");
    localStorage.removeItem("token");
  };

  return (
    <Router>
      <Header token={token} onLogout={onLogout} />
      <main className="max-w-5xl mx-auto p-6">
        <Routes>
          <Route path="/" element={token ? <Dashboard token={token} /> : <Navigate to="/login" />} />
          <Route path="/login" element={<Login onLogin={onLogin} />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="*" element={<div>Not found</div>} />
        </Routes>
      </main>
    </Router>
  );
}
