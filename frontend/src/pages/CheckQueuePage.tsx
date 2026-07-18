import { useEffect, useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";
import { getAppointmentQueueStatus, type AppointmentQueueStatus } from "../api/appointments";

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
  const [appointmentId, setAppointmentId] = useState(paramId ?? "");
  const [result, setResult] = useState<AppointmentQueueStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function check(id: string) {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getAppointmentQueueStatus(id);
      setResult(data);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Could not find that appointment");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (paramId) void check(paramId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramId]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    await check(appointmentId);
  }

  return (
    <main className="page" style={{ maxWidth: 480 }}>
      <h2>Check your queue number</h2>
      <form onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="appointment_id">Appointment ID</label>
          <input
            id="appointment_id"
            value={appointmentId}
            onChange={(e) => setAppointmentId(e.target.value)}
            placeholder="Paste the ID from your confirmation"
            required
          />
        </div>
        <button type="submit" disabled={loading} style={{ marginTop: 12 }}>
          {loading ? "Checking..." : "Check queue"}
        </button>
      </form>

      {error && <p className="error-text">{error}</p>}
      {result && (
        <div className="card" style={{ marginTop: 24 }}>
          <p>
            Status: <span className="status-pill">{STATUS_LABELS[result.status] ?? result.status}</span>
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
