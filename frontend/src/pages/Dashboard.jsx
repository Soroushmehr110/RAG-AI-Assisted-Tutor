// frontend/src/pages/Dashboard.jsx
import React, { useState, useRef } from "react";
import axios from "axios";
import ResultCard from "../components/ResultCard";

/*
 Updated Dashboard with:
 - improved containment so items don't overflow card areas
 - increased vertical spacing between mid-column cards
 - personalized evaluation text targeted to the student (2nd person)
 - keeps backend integration unchanged
*/

export default function Dashboard({ token }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const fileRef = useRef();

  const onFileChange = (e) => {
    setError("");
    setMessage("");
    setResult(null);
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  const openFilePicker = () => fileRef.current?.click();

  const analyze = async () => {
    if (!file) {
      setError("Please select an image first.");
      return;
    }
    setLoading(true);
    setError("");
    setMessage("");
    setResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await axios.post("http://localhost:8000/analyze-image", form, {
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "multipart/form-data" },
      });
      setResult(res.data);
      setMessage("Extraction & analysis complete.");
      window.requestAnimationFrame(() => window.scrollTo({ top: 0, behavior: "smooth" }));
    } catch (err) {
      setError(err.response?.data?.detail || "Upload/analysis failed.");
    } finally {
      setLoading(false);
    }
  };

  // Map score 0..100 to HSL hue 0 (red) -> 60 (yellow) -> 140 (greenish)
  const colorForScore = (score) => {
    const s = Math.max(0, Math.min(100, score));
    let hue;
    if (s <= 50) {
      hue = (s / 50) * 60;
    } else {
      hue = 60 + ((s - 50) / 50) * 80;
    }
    return `hsl(${hue.toFixed(0)} 78% 47%)`;
  };

  // motivational message in second-person (student-facing)
  const motivationalMessage = (scoreValue) => {
    if (scoreValue >= 90) return "Excellent — you're doing great! Keep it up.";
    if (scoreValue >= 75) return "Very good — a little polishing and you'll be there.";
    if (scoreValue >= 50) return "Good progress — focus on the key issues below.";
    if (scoreValue >= 25) return "You're getting started — follow the hint to continue.";
    return "Don't worry — start from the hint and try again. You can do this!";
  };

  // Convert instructor-style phrasing to student-facing phrasing.
  // Simple, conservative replacements to avoid accidental meaning changes.
  const personalizeText = (text) => {
    if (!text) return text;
    let t = String(text);
    // common safe replacements
    t = t.replace(/\b[Ss]tudents\b/g, "you");
    t = t.replace(/\b[Ss]tudent\b/g, "you");
    t = t.replace(/\bthe student\b/gi, "you");
    t = t.replace(/\btheir\b/gi, "your");
    t = t.replace(/\bthey\b/gi, "you");
    // minor cosmetic: remove leading "Student:" if present
    t = t.replace(/^[\s]*Student[:\-\s]+/i, "");
    return t;
  };

  const score = result?.analysis?.evaluation_score ?? 0;
  const confidence = result?.analysis?.confidence ?? null;
  const relevant = result?.analysis?.relevant ?? null;

  return (
    <>
      {/* center app branding above grid */}
      <div style={{ display: "flex", justifyContent: "center", margin: "18px 0 12px 0" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <img src="/app-icon.png" alt="MathSight" style={{ width: 56, height: 56, borderRadius: 12, boxShadow: "0 8px 26px rgba(76,67,160,0.08)" }} onError={(e) => (e.target.style.display = "none")} />
          <div>
            <div style={{ fontSize: 22, fontWeight: 900, color: "var(--accent)" }}>MathSight</div>
            <div style={{ fontSize: 13, color: "var(--muted)" }}>Upload problem → Get feedback & guidance</div>
          </div>
        </div>
      </div>

      <div className="dashboard-grid">
        {/* LEFT: Upload + preview */}
        <aside className="left-col card" style={{ boxSizing: "border-box" }}>
          <div className="card-head">
            <div>
              <div className="head-title">Add problem</div>
              <div className="head-sub">Use your camera or upload</div>
            </div>
          </div>

          <div className="mt-4">
            <input
              ref={fileRef}
              id="file-input"
              accept="image/*"
              capture="environment"
              type="file"
              onChange={onFileChange}
              style={{ display: "none" }}
            />

            <div className="controls">
              <button className="btn-ghost" onClick={openFilePicker}>Choose Image</button>
              <button className="btn-primary" onClick={analyze} disabled={loading || !file}>{loading ? "Analyzing..." : "Analyze"}</button>
            </div>

            {error && <div className="mt-3 err">{error}</div>}
            {message && <div className="mt-3 msg">{message}</div>}

            <div className="image-box mt-5" style={{ boxSizing: "border-box" }}>
              {preview ? (
                <img src={preview} alt="preview" />
              ) : (
                <div className="empty-preview">
                  <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="3" width="18" height="14" rx="2" />
                    <path d="M8 21l3-4 2 2 3-5 3 6" />
                  </svg>
                  <div className="mt-3" style={{ color: "var(--muted)" }}>No image selected</div>
                </div>
              )}
            </div>
          </div>
        </aside>

        {/* MIDDLE: Problem & Student Work */}
        <main className="mid-col" style={{ display: "flex", flexDirection: "column", gap: "1.6rem" }}>
          <ResultCard title="Problem" subtitle="Extracted problem statement">
            <div className="card-block" style={{ boxSizing: "border-box" }}>
              {/* protect against overflowing text: pre has max-height & scroll */}
              <pre style={{ maxHeight: 420, overflow: "auto", padding: 8, margin: 0, whiteSpace: "pre-wrap" }}>
                {result ? (result.extracted_text || "No problem extracted yet.") : "No problem extracted yet."}
              </pre>
            </div>
          </ResultCard>

          <ResultCard title="Student Work" subtitle="Student's attempt">
            <div className="card-block" style={{ boxSizing: "border-box" }}>
              <pre style={{ maxHeight: 420, overflow: "auto", padding: 8, margin: 0, whiteSpace: "pre-wrap" }}>
                {result ? (result.analysis.student_attempt || "No student attempt detected.") : "No student attempt detected."}
              </pre>
            </div>
          </ResultCard>
        </main>

        {/* RIGHT: Evaluation (wider) */}
        <aside className="right-col card" style={{ boxSizing: "border-box" }}>
          <div className="card-head" style={{ alignItems: "center" }}>
            <div>
              <div className="head-title">Evaluation</div>
              <div className="head-sub">Score, confidence and next steps</div>
            </div>
          </div>

          <div className="mt-4">
            {result ? (
              <>
                {relevant === "no" ? (
                  <div className="text-red-600">This content is not recognized as math material.</div>
                ) : (
                  <>
                    <div className="score-row">
                      <div className="score-badge">{Math.round(score)}<span className="score-percent">%</span></div>

                      <div style={{ flex: 1, marginLeft: 12 }}>
                        <div className="progress" aria-hidden>
                          <div
                            className="bar"
                            style={{
                              width: `${Math.max(0, Math.min(100, score))}%`,
                              background: `linear-gradient(90deg, ${colorForScore(score)} 0%, ${colorForScore(Math.min(100, score + 8))} 100%)`,
                            }}
                          />
                        </div>

                        <div className="meta-row" style={{ marginTop: 8, justifyContent: "space-between", display: "flex" }}>
                          <div className="kv">Confidence</div>
                          <div className="kv strong">{confidence !== null ? `${confidence}%` : "—"}</div>
                        </div>

                        <div style={{ marginTop: 10, fontWeight: 700, color: colorForScore(Math.max(10, score)) }}>
                          {motivationalMessage(score)}
                        </div>
                      </div>
                    </div>

                    <div className="mt-5">
                      <div className="kv">Feedback</div>
                      <div className="mt-2" style={{ whiteSpace: "pre-wrap" }}>{personalizeText(result.analysis.evaluation_rationale)}</div>
                    </div>

                    <div className="mt-4">
                      <div className="kv">Key issues</div>
                      <ul className="mistakes mt-2">
                        {(result.analysis.mistakes || []).length === 0 ? <li>None identified.</li> : (result.analysis.mistakes || []).map((m, i) => <li key={i}>{personalizeText(m)}</li>)}
                      </ul>
                    </div>

                    <div className="mt-4">
                      <div className="kv">Hint</div>
                      <div className="hint-box mt-2">{personalizeText(result.analysis.hint)}</div>
                    </div>

                    <div className="mt-4 flex gap-3">
                      <button className="btn-secondary">Save report</button>
                    </div>
                  </>
                )}
              </>
            ) : (
              <div className="text-sm text-gray-600">Run analysis to see a score, rationale, and next-step hint for you.</div>
            )}
          </div>
        </aside>
      </div>
    </>
  );
}
