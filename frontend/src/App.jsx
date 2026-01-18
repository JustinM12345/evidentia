import { useState } from 'react';
import './App.css'; 

// --- CONSTANTS: The Master List of Flags ---
const MASTER_FLAGS = {
  "data_collection": {
    "uses_cookies": "Uses cookies",
    "collects_email_address": "Collects email address",
    "collects_birthday": "Collects birthday",
    "collects_location": "Collects location data",
    "collects_device_info": "Collects device information",
    "collects_ip_address": "Collects IP address",
  },
  "advertising": {
    "shares_for_advertising": "Shares data for advertising",
    "uses_targeted_ads": "Uses targeted advertising",
    "uses_cross_site_tracking": "Uses cross-site tracking",
    "sells_user_data": "Sells user data",
    "collects_behavioral_data": "Collects behavioral data",
  },
  "data_sharing": {
    "shares_with_third_parties": "Shares with third parties",
    "shares_with_government": "Shares with government",
    "shares_with_data_brokers": "Shares with data brokers",
    "sells_sensitive_data": "Sells sensitive data",
    "shares_health_data": "Shares health data",
  },
  "sensitive_data": {
    "collects_biometrics": "Collects biometric data",
    "collects_health_information": "Collects health information",
    "collects_precise_location": "Collects precise location",
    "collects_children_data": "Collects children's data",
  },
  "user_rights": {
    "no_data_portability": "No data portability",
    "no_data_deletion": "No data deletion rights",
    "no_access_correction_rights": "No access correction rights",
    "denies_user_access": "Denies user access",
  },
  "legal": {
    "binding_arbitration": "Has binding arbitration clause",
    "class_action_waiver": "Has class action waiver",
    "unilateral_terms_change": "Has unilateral terms change",
    "waives_rights": "Waives user rights",
    "indefinite_data_retention": "Indefinite data retention",
  },
  "extreme_cases": {
    "reidentifies_anonymous_data": "Re-identifies anonymous data",
    "forced_disclosure_of_data": "Forced disclosure of user data",
    "life_control_technology": "Takes control of your life via advanced tech",
  },
};

// Flatten for easy iteration in the view
const ALL_FLAGS_FLAT = {};
Object.values(MASTER_FLAGS).forEach(category => {
  Object.assign(ALL_FLAGS_FLAT, category);
});

// --- API HELPER (FIXED) ---
async function postJSON(path, body, setLoading, setError, setResult) {
  setLoading(true);
  setError('');

  // --- THE FIX IS HERE ---
  const BACKEND_URL = "https://evidentia.onrender.com"; 

  try {
    // We add BACKEND_URL before the path
    const res = await fetch(`${BACKEND_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const msg = await res.text();
      throw new Error(msg || `Request failed: ${res.status}`);
    }

    const data = await res.json();
    setResult(data);
  } catch (e) {
    setError(e.message || 'Something went wrong');
    setResult(null);
  } finally {
    setLoading(false);
  }
}

// --- MAIN APP COMPONENT ---
export default function App() {
  const [textA, setTextA] = useState('');
  const [textB, setTextB] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  return (
    <div className="container">
      <img src="/logo.png" alt="Evidentia Logo" className="logo" />

      <p>
        Evidentia empowers you to analyze legal terms and conditions by identifying critical data that companies may collect when you agree to their policies. You can also compare two policies side-by-side, helping you spot key differences and similarities to make more informed decisions about your privacy and data security.
      </p>

      {/* Inputs */}
      <div className="policy-container">
        <PolicyInput
          label="Policy A"
          value={textA}
          onChange={setTextA}
          loading={loading}
          onAnalyze={() => postJSON('/api/analyze', { text: textA }, setLoading, setError, setResult)}
        />
        <PolicyInput
          label="Policy B"
          value={textB}
          onChange={setTextB}
          loading={loading}
          onAnalyze={() => postJSON('/api/analyze', { text: textB }, setLoading, setError, setResult)}
        />
      </div>

      {loading && <span className="loading-text">Running…</span>}

      <div className="button-container">
        <button
          className="primary"
          disabled={loading || textA.trim().length < 10 || textB.trim().length < 10}
          onClick={() => postJSON('/api/compare', { textA, textB }, setLoading, setError, setResult)}
        >
          Compare
        </button>

        <button
          className="secondary"
          disabled={loading}
          onClick={() => {
            setTextA('');
            setTextB('');
            setResult(null);
            setError('');
          }}
        >
          Clear
        </button>
      </div>

      {error && <ErrorNotification error={error} />}

      {/* RESULT LOGIC */}
      {result && (
        result.comparison ? (
          <ComparisonView result={result} />
        ) : (
          <SingleAnalysisView result={result} />
        )
      )}
    </div>
  );
}

// --- SUB-COMPONENTS ---

function PolicyInput({ label, value, onChange, loading, onAnalyze }) {
  return (
    <div className="policy-input">
      <h3>{label}</h3>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={`Paste ${label} here...`}
        rows={14}
        disabled={loading}
      />
      <button
        disabled={loading || value.trim().length < 10}
        onClick={onAnalyze}
      >
        Analyze {label}
      </button>
    </div>
  );
}

function ErrorNotification({ error }) {
  return <div className="error-notification"><strong>Error:</strong> {error}</div>;
}

// --- VIEW 1: SINGLE ANALYSIS (Score Moved to Top) ---
function SingleAnalysisView({ result }) {
  const { findings, overall_score } = result;

  const findingsMap = {};
  findings.forEach(f => {
    findingsMap[f.flag] = f;
  });

  // Determine Score Color
  let scoreColor = '#2ecc71'; // Green
  let scoreLabel = 'Safe';
  if (overall_score > 70) {
    scoreColor = '#e74c3c'; // Red
    scoreLabel = 'Dangerous';
  } else if (overall_score > 30) {
    scoreColor = '#f1c40f'; // Yellow
    scoreLabel = 'Moderate Risk';
  }

  return (
    <div className="single-view-container">
      <h2>Policy Analysis</h2>
      
      {/* 1. SCORE HEADER (Moved Here) */}
      <div className="score-header" style={{ borderBottom: `4px solid ${scoreColor}` }}>
        <div className="score-circle" style={{ borderColor: scoreColor, color: scoreColor }}>
          {Math.round(overall_score)}
        </div>
        <div className="score-text">
          <h3 style={{ color: scoreColor }}>{scoreLabel}</h3>
          <p>Overall Risk Score</p>
        </div>
      </div>

      {/* 2. THE CHECKLIST */}
      <div className="checklist-container">
        {Object.entries(ALL_FLAGS_FLAT).map(([flagId, label]) => {
          const finding = findingsMap[flagId];
          const isFound = finding && finding.status === 'true';
          const isUnknown = finding && finding.status === 'unknown';

          let boxClass = 'box-green';
          let statusText = 'Not Found';
          let description = 'No evidence of this risk was found in the text.';

          if (isFound) {
            boxClass = 'box-red';
            statusText = 'Detected';
            description = finding.evidence_quote ? `"${finding.evidence_quote}"` : 'Explicitly mentioned in the policy.';
          } else if (isUnknown) {
            boxClass = 'box-yellow';
            statusText = 'Unclear';
            description = 'The policy language is ambiguous regarding this term.';
          }

          return (
            <div key={flagId} className="checklist-row">
              <div className={`status-box ${boxClass}`}>
                <strong>{label}</strong>
                <span className="status-badge">{statusText}</span>
              </div>
              <div className="description-box">
                {description}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// --- VIEW 2: COMPARISON ---
function ComparisonView({ result }) {
  const { reportA, reportB, comparison } = result;
  
  return (
    <div className="comparison-container">
      <div className="verdict-banner" style={{ background: comparison.winner !== 'Tie' ? '#e6fffa' : '#f5f5f5', border: '2px solid #2ecc71' }}>
        <h2>🏆 Verdict: {comparison.verdict}</h2>
        <p>Difference in Risk Score: {comparison.score_diff}</p>
      </div>

      <div className="score-cards">
        <div className={`score-card ${comparison.winner === 'A' ? 'winner' : ''}`}>
          <h3>Policy A</h3>
          <div className="big-score">{Math.round(reportA.overall_score)}</div>
          <span className="label">Risk Score</span>
        </div>
        <div className="vs-badge">VS</div>
        <div className={`score-card ${comparison.winner === 'B' ? 'winner' : ''}`}>
          <h3>Policy B</h3>
          <div className="big-score">{Math.round(reportB.overall_score)}</div>
          <span className="label">Risk Score</span>
        </div>
      </div>

      <div className="details-section">
        <div className="detail-column">
          <h4 className="danger-text">⚠️ Risks Unique to Policy A</h4>
          {comparison.unique_to_A.length === 0 ? <p className="good-text">No unique risks!</p> : (
            <ul>{comparison.unique_to_A.map((f, i) => <li key={i} title={f.evidence_quote}><strong>{f.label}</strong></li>)}</ul>
          )}
        </div>
        <div className="detail-column center-col">
          <h4 className="warning-text">⚖️ Shared Risks (Both)</h4>
          {comparison.common_risks.length === 0 ? <p>No shared risks.</p> : (
            <ul>{comparison.common_risks.map((f, i) => <li key={i}>{f.label}</li>)}</ul>
          )}
        </div>
        <div className="detail-column">
          <h4 className="danger-text">⚠️ Risks Unique to Policy B</h4>
          {comparison.unique_to_B.length === 0 ? <p className="good-text">No unique risks!</p> : (
            <ul>{comparison.unique_to_B.map((f, i) => <li key={i} title={f.evidence_quote}><strong>{f.label}</strong></li>)}</ul>
          )}
        </div>
      </div>
    </div>
  );
}