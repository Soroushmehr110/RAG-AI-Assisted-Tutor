// frontend/src/components/ResultCard.jsx
import React from "react";

export default function ResultCard({ title, subtitle, children }) {
  return (
    <div className="card result-card">
      <div className="card-head" style={{ justifyContent: "space-between" }}>
        <div>
          <div style={{ fontWeight: 800, fontSize: 15 }}>{title}</div>
          {subtitle && <div className="head-sub" style={{ marginTop: 6 }}>{subtitle}</div>}
        </div>
      </div>
      <div className="mt-3">
        {children}
      </div>
    </div>
  );
}
