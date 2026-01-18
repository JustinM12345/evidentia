import { useState } from 'react';
import './App.css'; // Ensure the updated CSS file is imported

// PostJSON helper (Fixed to handle both Analyze and Compare)
async function postJSON(path, body, setLoading, setError, setResult) {
  setLoading(true);
  setError('');
  try {
    const res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body), // <--- FIXED: Send the exact object passed in
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

export default function App() {
  const [textA, setTextA] = useState('');  // Policy A input state
  const [textB, setTextB] = useState('');  // Policy B input state
  const [loading, setLoading] = useState(false); // Loading state
  const [result, setResult] = useState(null);  // Result state
  const [error, setError] = useState('');  // Error state

  return (
    <div className="container">
      {/* Logo as Header */}
      <img src="/logo.png" alt="Evidentia Logo" className="logo" />


      <p>
        Evidentia empowers you to analyze legal terms and conditions by identifying critical data that companies may collect when you agree to their policies. You can also compare two policies side-by-side, helping you spot key differences and similarities to make more informed decisions about your privacy and data security.
      </p>

      <div className="policy-container">
        <PolicyInput
          label="Policy A"
          value={textA}
          onChange={setTextA}
          loading={loading}
          onAnalyze={() => postJSON('/api/analyze', { text: textA, url: "https://example.com/policyA" }, setLoading, setError, setResult)}
        />
        <PolicyInput
          label="Policy B"
          value={textB}
          onChange={setTextB}
          loading={loading}
          onAnalyze={() => postJSON('/api/analyze', { text: textB, url: "https://example.com/policyB" }, setLoading, setError, setResult)}
        />
      </div>

      {loading && <span className="loading-text">Running…</span>} {/* Running text above buttons */}

      <div className="button-container">
        <button
          className="primary"
          disabled={loading || textA.trim().length < 50 || textB.trim().length < 50}
          onClick={() => postJSON('/api/compare', { textA, textB, urlA: "https://example.com/policyA", urlB: "https://example.com/policyB" }, setLoading, setError, setResult)}
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
      {result && (
        result.comparison ? (
          <ComparisonView result={result} />
        ) : (
          <Output result={result} />
        )
      )}
    </div>
  );
}

// Policy Input Component
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
        disabled={loading || value.trim().length < 50}
        onClick={onAnalyze}
      >
        Analyze {label}
      </button>
    </div>
  );
}

// Error Notification Component
function ErrorNotification({ error }) {
  return (
    <div className="error-notification">
      <strong>Error:</strong> {error}
    </div>
  );
}

// Output Component
function Output({ result }) {
  return (
    <div className="output">
      <h3>Output</h3>
      <pre>{JSON.stringify(result, null, 2)}</pre>
    </div>
  );
}

// New Component for Side-by-Side Comparison
function ComparisonView({ result }) {
  const { reportA, reportB, comparison } = result;
  
  // Helper to choose color based on winner
  const getHeaderColor = () => {
    if (comparison.winner === 'A') return 'linear-gradient(135deg, #d4fc79 0%, #96e6a1 100%)';
    if (comparison.winner === 'B') return 'linear-gradient(135deg, #d4fc79 0%, #96e6a1 100%)'; // Same green for "safer"
    return '#f0f0f0';
  };

  return (
    <div className="comparison-container">
      {/* 1. The Verdict Banner */}
      <div className="verdict-banner" style={{ background: comparison.winner !== 'Tie' ? '#e6fffa' : '#f5f5f5', border: '2px solid #2ecc71' }}>
        <h2>🏆 Verdict: {comparison.verdict}</h2>
        <p>Difference in Risk Score: {comparison.score_diff}</p>
      </div>

      {/* 2. Score Cards */}
      <div className="score-cards">
        <div className={`score-card ${comparison.winner === 'A' ? 'winner' : ''}`}>
          <h3>Policy A</h3>
          <div className="big-score">{reportA.overall_score}</div>
          <span className="label">Risk Score</span>
        </div>
        <div className="vs-badge">VS</div>
        <div className={`score-card ${comparison.winner === 'B' ? 'winner' : ''}`}>
          <h3>Policy B</h3>
          <div className="big-score">{reportB.overall_score}</div>
          <span className="label">Risk Score</span>
        </div>
      </div>

      {/* 3. The Details Table */}
      <div className="details-section">
        
        {/* Unique to A */}
        <div className="detail-column">
          <h4 className="danger-text">⚠️ Risks Unique to Policy A</h4>
          {comparison.unique_to_A.length === 0 ? <p className="good-text">No unique risks!</p> : (
            <ul>
              {comparison.unique_to_A.map((flag, i) => (
                <li key={i} title={flag.evidence_quote}>
                  <strong>{flag.label}</strong>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Common Risks */}
        <div className="detail-column center-col">
          <h4 className="warning-text">⚖️ Shared Risks (Both)</h4>
          {comparison.common_risks.length === 0 ? <p>No shared risks.</p> : (
            <ul>
              {comparison.common_risks.map((flag, i) => (
                <li key={i}>
                  {flag.label}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Unique to B */}
        <div className="detail-column">
          <h4 className="danger-text">⚠️ Risks Unique to Policy B</h4>
          {comparison.unique_to_B.length === 0 ? <p className="good-text">No unique risks!</p> : (
            <ul>
              {comparison.unique_to_B.map((flag, i) => (
                <li key={i} title={flag.evidence_quote}>
                  <strong>{flag.label}</strong>
                </li>
              ))}
            </ul>
          )}
        </div>

      </div>
    </div>
  );
}