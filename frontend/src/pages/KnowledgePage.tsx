import { useState, type FormEvent } from "react";
import { useToken } from "../auth/AuthContext";
import { askKnowledge, type AskResponse } from "../api/knowledge";

export function KnowledgePage() {
  const token = useToken();
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AskResponse | null>(null);

  async function handleAsk(event: FormEvent) {
    event.preventDefault();
    setAsking(true);
    setError(null);
    try {
      const response = await askKnowledge(token, question);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get an answer");
      setResult(null);
    } finally {
      setAsking(false);
    }
  }

  return (
    <section>
      <h2>Ask about clinic policy</h2>
      <p className="muted">
        Answers are grounded in the clinic's own policy documents (triage protocol, vaccination
        schedule, cancellation policy, walk-in emergency policy) instead of general guesses.
      </p>

      <form className="card" onSubmit={handleAsk} style={{ marginTop: 16 }}>
        <div className="field">
          <label htmlFor="question">Question</label>
          <input
            id="question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. What's the late-cancellation fee?"
            required
          />
        </div>
        <button type="submit" disabled={asking || !question.trim()} style={{ marginTop: 12 }}>
          {asking ? "Asking..." : "Ask"}
        </button>
        {error && <p className="error-text">{error}</p>}
      </form>

      {result && (
        <div className="card" style={{ marginTop: 24 }}>
          <p>{result.answer}</p>
          {result.sources.length > 0 && <p className="muted">Source: {result.sources.join(", ")}</p>}
        </div>
      )}
    </section>
  );
}
