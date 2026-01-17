import { useState } from 'react';
import './App.css';

export default function App() {
  const [textA, setTextA] = useState('');
  const [textB, setTextB] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  async function postJSON(path, body) {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(path, {
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

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: 24 }}>
      <h1 style={{ marginBottom: 8 }}>Evidentia</h1>
      <p style={{ marginTop: 0, opacity: 0.8 }}>
        Paste two policies to generate an evidence-backed checklist and comparison.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div>
          <h3>Policy A</h3>
          <textarea
            value={textA}
            onChange={(e) => setTextA(e.target.value)}
            placeholder="Paste Policy A here..."
            rows={14}
            style={{ width: '100%', padding: 12, fontFamily: 'inherit' }}
          />
          <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
            <button
              disabled={loading || textA.trim().length < 50}
              onClick={() => postJSON('/api/analyze', { text: textA })}
            >
              Analyze A
            </button>
          </div>
        </div>

        <div>
          <h3>Policy B</h3>
          <textarea
            value={textB}
            onChange={(e) => setTextB(e.target.value)}
            placeholder="Paste Policy B here..."
            rows={14}
            style={{ width: '100%', padding: 12, fontFamily: 'inherit' }}
          />
          <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
            <button
              disabled={loading || textB.trim().length < 50}
              onClick={() => postJSON('/api/analyze', { text: textB })}
            >
              Analyze B
            </button>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
        <button
          disabled={loading || textA.trim().length < 50 || textB.trim().length < 50}
          onClick={() => postJSON('/api/compare', { textA, textB })}
        >
          Compare
        </button>

        <button
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

        {loading && <span style={{ alignSelf: 'center' }}>Running…</span>}
      </div>

      {error && (
        <div style={{ marginTop: 12, color: 'crimson' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div style={{ marginTop: 16 }}>
          <h3>Output</h3>
          <pre
            style={{
              background: '#0b1020',
              color: '#dce6ff',
              padding: 16,
              borderRadius: 8,
              overflowX: 'auto',
            }}
          >
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
