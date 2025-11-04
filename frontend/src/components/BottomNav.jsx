import React from "react";

export default function BottomNav({ onAnalyze, onHelp }) {
  return (
    <div className="bottom-nav" role="navigation" aria-label="Quick actions">
      <div className="nav-container">
        <div className="nav-item" onClick={onHelp} title="Tips">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6B7280" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a10 10 0 100 20 10 10 0 000-20z"></path>
            <path d="M9.09 9a3 3 0 115.82 1c0 1.5-1.5 2.2-1.5 2.2"></path>
            <path d="M12 17h.01"></path>
          </svg>
          <div style={{fontSize:13}}>Tips</div>
        </div>

        <div style={{display:"flex", alignItems:"center", justifyContent:"center"}}>
          <button className="fab" onClick={onAnalyze} aria-label="Analyze image">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 7h4l2-3h6l2 3h4v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7z"></path>
              <path d="M12 11a3 3 0 100 6 3 3 0 000-6z"></path>
            </svg>
            <span style={{fontSize:14}}>Analyze</span>
          </button>
        </div>

        <div style={{width:54}}></div> {/* keep symmetry */}
      </div>
    </div>
  );
}
