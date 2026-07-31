import { useEffect, useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";
import {
  formatTicketNumber,
  getAppointmentQueueStatus,
  getQueueStatusByTicket,
  type AppointmentQueueStatus,
} from "../api/appointments";
import { statusPillClass } from "../lib/format";

const STATUS_LABELS: Record<string, string> = {
  scheduled: "Scheduled",
  checked_in: "Checked in",
  in_progress: "In progress",
  completed: "Completed",
  cancelled: "Cancelled",
  no_show: "No show",
};

export function CheckQueuePage() {
  const { appointmentId: paramId } = useParams<{ appointmentId?: string }>();
  const [ticketInput, setTicketInput] = useState("");
  const [result, setResult] = useState<AppointmentQueueStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Automatic lookup right after self-check-in, which redirects here with the
  // full appointment ID in the URL - no typing involved, so no ticket number needed.
  useEffect(() => {
    if (!paramId) return;
    setLoading(true);
    setError(null);
    getAppointmentQueueStatus(paramId)
      .then(setResult)
      .catch((err: unknown) => {
        setResult(null);
        setError(err instanceof Error ? err.message : "Could not find that appointment");
      })
      .finally(() => setLoading(false));
  }, [paramId]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const ticketNumber = Number(ticketInput);
    if (!Number.isInteger(ticketNumber) || ticketNumber <= 0) {
      setError("Enter a valid ticket number");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await getQueueStatusByTicket(ticketNumber);
      setResult(data);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Could not find that ticket number");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page" style={{ maxWidth: 480, margin: "0 auto" }}>
      <div className="brand" style={{ justifyContent: "center", marginBottom: 8 }}>
        VetFlow
      </div>
      <h2 style={{ textAlign: "center" }}>Check your queue number</h2>
      {!paramId && (
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="ticket_number">Ticket number</label>
            <input
              id="ticket_number"
              value={ticketInput}
              onChange={(e) => setTicketInput(e.target.value)}
              placeholder="e.g. 42"
              inputMode="numeric"
              required
            />
          </div>
          <button type="submit" disabled={loading} style={{ marginTop: 12 }}>
            {loading ? "Checking..." : "Check queue"}
          </button>
        </form>
      )}

      {error && <p className="error-text">{error}</p>}
      {result && (
        <div className="card" style={{ marginTop: 24 }}>
          {result.ticket_number !== null && (
            <p className="muted" style={{ marginTop: 0 }}>
              Ticket {formatTicketNumber(result.ticket_number)}
            </p>
          )}
          <p>
            Status:{" "}
            <span className={`status-pill ${statusPillClass(result.status)}`}>
              {STATUS_LABELS[result.status] ?? result.status}
            </span>
          </p>
          {result.status === "checked_in" && result.position !== null ? (
            <p>
              You are <strong>#{result.position}</strong> of {result.total_waiting} waiting.
            </p>
          ) : (
            <p className="muted">
              {result.total_waiting} {result.total_waiting === 1 ? "person" : "people"} currently waiting.
            </p>
          )}
        </div>
      )}
    </main>
  );
}
