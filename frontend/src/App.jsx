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

const ALL_FLAGS_FLAT = {};
Object.values(MASTER_FLAGS).forEach(category => {
  Object.assign(ALL_FLAGS_FLAT, category);
});

// --- API HELPER ---
async function postJSON(path, body, setLoading, setError, setResult) {
  setLoading(true);
  setError('');
  setResult(null);

  // Note: Change this to http://localhost:8000 if testing locally
  const BACKEND_URL = "http://localhost:8000"; 

  try {
    const res = await fetch(`${BACKEND_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "An unexpected error occurred.");
    }

    setResult(data);
  } catch (e) {
    setError(e.message);
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

      <p className="text-center text-gray-600 text-3xl font-serif font-bold mb-12 max-w-2xl mx-auto">
        Presenting Facts So Clearly That The Truth Becomes Impossible To Ignore.
      </p>

      <div className="instructions-panel" style={{ textAlign: 'center', marginBottom: '30px', background: '#f0f4f8', padding: '20px', borderRadius: '12px' }}>
        <h2 style={{ margin: '0 0 10px 0' }}>Manual Analysis Mode</h2>
        <p style={{ margin: 0 }}>
          Go to your target website, press <b>Ctrl+A</b> then <b>Ctrl+C</b>, and paste the text into the boxes below.
        </p>
      </div>

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

      <div className="button-container" style={{ marginTop: '20px' }}>
        <button
          className="primary"
          disabled={loading || textA.trim().length < 50 || textB.trim().length < 50}
          onClick={() => postJSON('/api/compare', { textA, textB }, setLoading, setError, setResult)}
        >
          {loading ? "Analyzing..." : "Compare Policies"}
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
          Clear All
        </button>
      </div>

      {error && <div className="error-box" style={{ color: 'red', marginTop: '20px', fontWeight: 'bold' }}>{error}</div>}

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

// --- COMPONENTS ---

function PolicyInput({ label, value, onChange, loading, onAnalyze }) {
  return (
    <div className="policy-input">
      <h3>{label}</h3>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={`Paste ${label} text here...`}
        rows={14}
        disabled={loading}
      />
      <button
        disabled={loading || value.trim().length < 50}
        onClick={onAnalyze}
      >
        Analyze {label}
      </button>
    </div>
  );
}

function SingleAnalysisView({ result }) {
  const { findings, overall_score } = result;
  const findingsMap = {};
  findings.forEach(f => { findingsMap[f.flag] = f; });

  let scoreColor = overall_score > 70 ? '#e74c3c' : (overall_score > 30 ? '#f1c40f' : '#2ecc71');
  let scoreLabel = overall_score > 70 ? 'Dangerous' : (overall_score > 30 ? 'Moderate Risk' : 'Safe');

  return (
    <div className="single-view-container">
      <div className="score-header" style={{ borderBottom: `4px solid ${scoreColor}` }}>
        <div className="score-circle" style={{ borderColor: scoreColor, color: scoreColor }}>
          {Math.round(overall_score)}
        </div>
        <div className="score-text">
          <h3 style={{ color: scoreColor }}>{scoreLabel}</h3>
          <p>Overall Risk Score</p>
        </div>
      </div>

      <div className="checklist-container">
        {Object.entries(ALL_FLAGS_FLAT).map(([flagId, label]) => {
          const finding = findingsMap[flagId];
          const isFound = finding && finding.status === 'true';
          return (
            <div key={flagId} className="checklist-row">
              <div className={`status-box ${isFound ? 'box-red' : 'box-green'}`}>
                <strong>{label}</strong>
                <span className="status-badge">{isFound ? 'Detected' : 'Not Found'}</span>
              </div>
              <div className="description-box">
                {isFound ? `"${finding.evidence_quote}"` : 'No evidence found.'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ComparisonView({ result }) {
  const { reportA, reportB, comparison } = result;
  return (
    <div className="comparison-container">
      <div className="verdict-banner" style={{ border: '2px solid #2ecc71', background: '#f0fff4' }}>
        <h2>🏆 Verdict: {comparison.verdict}</h2>
        <p>Difference in Risk Score: {comparison.score_diff}</p>
      </div>

      <div className="score-cards">
        <div className={`score-card ${comparison.winner === 'A' ? 'winner' : ''}`}>
          <h3>Policy A</h3>
          <div className="big-score">{Math.round(reportA.overall_score)}</div>
        </div>
        <div className="vs-badge">VS</div>
        <div className={`score-card ${comparison.winner === 'B' ? 'winner' : ''}`}>
          <h3>Policy B</h3>
          <div className="big-score">{Math.round(reportB.overall_score)}</div>
        </div>
      </div>

      <div className="details-section">
        <div className="detail-column">
          <h4 className="danger-text">⚠️ Unique to A</h4>
          <ul>{comparison.unique_to_A.map((f, i) => <li key={i}><strong>{f.label}</strong></li>)}</ul>
        </div>
        <div className="detail-column center-col">
          <h4 className="warning-text">⚖️ Shared Risks</h4>
          <ul>{comparison.common_risks.map((f, i) => <li key={i}>{f.label}</li>)}</ul>
        </div>
        <div className="detail-column">
          <h4 className="danger-text">⚠️ Unique to B</h4>
          <ul>{comparison.unique_to_B.map((f, i) => <li key={i}><strong>{f.label}</strong></li>)}</ul>
        </div>
      </div>
    </div>
  );
}