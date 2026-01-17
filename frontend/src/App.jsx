import { useState } from 'react';
import './App.css'; // Ensure the updated CSS file is imported

// PostJSON helper (to send the analyze request)
async function postJSON(path, body, setLoading, setError, setResult) {
  setLoading(true);
  setError('');
  try {
    const res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: body.text, // The policy text entered by the user
        url: body.url || "https://example.com" // Provide a placeholder URL
      }),
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
      <h1>Evidentia</h1>
      <p>Paste two policies to generate an evidence-backed checklist and comparison.</p>

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
      {result && <Output result={result} />}
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
