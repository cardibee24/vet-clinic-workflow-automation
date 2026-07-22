import { useState, type FormEvent } from "react";
import { useToken } from "../auth/AuthContext";
import { askAssistant, type AssistantResult } from "../api/assistant";

const INTENT_LABELS: Record<string, string> = {
  policy: "Policy",
  booking: "Booking",
  triage: "Triage",
};

export function AssistantPage() {
  const token = useToken();
  const [message, setMessage] = useState("");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AssistantResult | null>(null);

  async function handleAsk(event: FormEvent) {
    event.preventDefault();
    setAsking(true);
    setError(null);
    try {
      const response = await askAssistant(token, message);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get a response");
      setResult(null);
    } finally {
      setAsking(false);
    }
  }

  return (
    <section>
      <h2>Assistant</h2>
      <p className="muted">Ask me anything.</p>

      <form className="card" onSubmit={handleAsk} style={{ marginTop: 16 }}>
        <div className="field">
          <label htmlFor="message">Message</label>
          <input
            id="message"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="e.g. What's the late-cancellation fee? / Is Tuesday at 2pm free? / My dog is limping"
            required
          />
        </div>
        <button type="submit" disabled={asking || !message.trim()} style={{ marginTop: 12 }}>
          {asking ? "Asking..." : "Ask"}
        </button>
        {error && <p className="error-text">{error}</p>}
      </form>

      {result && (
        <div className="card" style={{ marginTop: 24 }}>
          <span className="status-pill status-info">{INTENT_LABELS[result.intent] ?? result.intent}</span>
          <p style={{ marginTop: 12 }}>{result.reply}</p>
        </div>
      )}
    </section>
  );
}
