import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useToken } from "../auth/AuthContext";
import {
  createAppointment,
  deleteAppointment,
  updateAppointmentStatus,
  type AppointmentStatus,
} from "../api/appointments";
import { useAppointmentDirectory } from "../hooks/useAppointmentDirectory";
import { usePetDirectory } from "../hooks/usePetDirectory";
import { formatDateTime } from "../lib/format";

const ALLOWED_TRANSITIONS: Record<AppointmentStatus, AppointmentStatus[]> = {
  scheduled: ["checked_in", "cancelled", "no_show"],
  checked_in: ["in_progress", "cancelled"],
  in_progress: ["completed", "cancelled"],
  completed: [],
  cancelled: [],
  no_show: [],
};

const STATUS_LABELS: Record<AppointmentStatus, string> = {
  scheduled: "Scheduled",
  checked_in: "Checked in",
  in_progress: "In progress",
  completed: "Completed",
  cancelled: "Cancelled",
  no_show: "No show",
};

export function AppointmentsPage() {
  const token = useToken();
  const { appointments, loading, error, refresh } = useAppointmentDirectory(token);
  const petDirectory = usePetDirectory(token);

  const [petId, setPetId] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await createAppointment(token, {
        pet_id: petId,
        scheduled_at: scheduledAt,
        reason: reason || undefined,
      });
      setPetId("");
      setScheduledAt("");
      setReason("");
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create appointment");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTransition(appointmentId: string, status: AppointmentStatus) {
    setActionError(null);
    try {
      await updateAppointmentStatus(token, appointmentId, status);
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to update appointment");
    }
  }

  async function handleDelete(appointmentId: string) {
    if (!window.confirm("Delete this appointment? This cannot be undone.")) {
      return;
    }
    setDeletingId(appointmentId);
    setActionError(null);
    try {
      await deleteAppointment(token, appointmentId);
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to delete appointment");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section>
      <h2>Appointments</h2>

      <form className="card" onSubmit={handleSubmit}>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="pet">Pet</label>
            <select id="pet" value={petId} onChange={(e) => setPetId(e.target.value)} required>
              <option value="" disabled>
                Select a pet
              </option>
              {petDirectory.pets.map((pet) => (
                <option key={pet.id} value={pet.id}>
                  {pet.name} ({pet.species}) — {pet.ownerName}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="scheduled_at">Date &amp; time</label>
            <input
              id="scheduled_at"
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="reason">Reason</label>
            <input id="reason" value={reason} onChange={(e) => setReason(e.target.value)} />
          </div>
          <button type="submit" disabled={submitting || petDirectory.pets.length === 0}>
            {submitting ? "Scheduling..." : "Schedule appointment"}
          </button>
        </div>
        {petDirectory.pets.length === 0 && !petDirectory.loading && (
          <p className="muted">Add an owner and a pet before scheduling an appointment.</p>
        )}
        {formError && <p className="error-text">{formError}</p>}
      </form>

      {loading && <p>Loading appointments...</p>}
      {error && <p className="error-text">{error}</p>}
      {actionError && <p className="error-text">{actionError}</p>}
      {!loading && !error && (
        <table>
          <thead>
            <tr>
              <th>Pet</th>
              <th>Owner</th>
              <th>Date &amp; time</th>
              <th>Status</th>
              <th>Reason</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {appointments.map((appointment) => (
              <tr key={appointment.id}>
                <td>{appointment.petName}</td>
                <td>{appointment.ownerName}</td>
                <td>{formatDateTime(appointment.scheduled_at)}</td>
                <td>
                  <span className="status-pill">{STATUS_LABELS[appointment.status]}</span>
                </td>
                <td>{appointment.reason ?? "—"}</td>
                <td>
                  <div className="actions">
                    {ALLOWED_TRANSITIONS[appointment.status].map((next) => (
                      <button
                        key={next}
                        type="button"
                        className="secondary"
                        onClick={() => handleTransition(appointment.id, next)}
                      >
                        {STATUS_LABELS[next]}
                      </button>
                    ))}
                    <Link to={`/check-queue/${appointment.id}`} target="_blank" rel="noreferrer">
                      Queue link
                    </Link>
                    <button
                      type="button"
                      className="secondary"
                      disabled={deletingId === appointment.id}
                      onClick={() => handleDelete(appointment.id)}
                    >
                      {deletingId === appointment.id ? "Deleting..." : "Delete"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {appointments.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  No appointments yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </section>
  );
}
