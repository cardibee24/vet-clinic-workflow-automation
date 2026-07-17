import { useEffect, useState, type FormEvent } from "react";
import { useToken } from "../auth/AuthContext";
import {
  createReminder,
  listReminders,
  updateReminderStatus,
  type Reminder,
  type ReminderChannel,
  type ReminderStatus,
} from "../api/reminders";
import { useAppointmentDirectory } from "../hooks/useAppointmentDirectory";
import { formatDateTime } from "../lib/format";

const ALLOWED_TRANSITIONS: Record<ReminderStatus, ReminderStatus[]> = {
  pending: ["sent", "failed", "cancelled"],
  failed: ["pending", "cancelled"],
  sent: [],
  cancelled: [],
};

const STATUS_LABELS: Record<ReminderStatus, string> = {
  pending: "Pending",
  sent: "Sent",
  failed: "Failed",
  cancelled: "Cancelled",
};

export function RemindersPage() {
  const token = useToken();
  const { appointments } = useAppointmentDirectory(token);

  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const [appointmentId, setAppointmentId] = useState("");
  const [channel, setChannel] = useState<ReminderChannel>("email");
  const [sendAt, setSendAt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  function refresh() {
    setLoading(true);
    listReminders(token)
      .then((data) => {
        setReminders(data);
        setLoadError(null);
      })
      .catch((err: unknown) => setLoadError(err instanceof Error ? err.message : "Failed to load reminders"))
      .finally(() => setLoading(false));
  }

  useEffect(refresh, [token]);

  const appointmentsById = new Map(appointments.map((appointment) => [appointment.id, appointment]));

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await createReminder(token, { appointment_id: appointmentId, channel, send_at: sendAt });
      setAppointmentId("");
      setSendAt("");
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create reminder");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTransition(reminderId: string, status: ReminderStatus) {
    setActionError(null);
    try {
      await updateReminderStatus(token, reminderId, status);
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to update reminder");
    }
  }

  return (
    <section>
      <h2>Reminders</h2>

      <form className="card" onSubmit={handleSubmit}>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="appointment">Appointment</label>
            <select
              id="appointment"
              value={appointmentId}
              onChange={(e) => setAppointmentId(e.target.value)}
              required
            >
              <option value="" disabled>
                Select an appointment
              </option>
              {appointments.map((appointment) => (
                <option key={appointment.id} value={appointment.id}>
                  {appointment.petName} ({appointment.ownerName}) — {formatDateTime(appointment.scheduled_start)}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="channel">Channel</label>
            <select id="channel" value={channel} onChange={(e) => setChannel(e.target.value as ReminderChannel)}>
              <option value="email">Email</option>
              <option value="sms">SMS</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="send_at">Send at</label>
            <input
              id="send_at"
              type="datetime-local"
              value={sendAt}
              onChange={(e) => setSendAt(e.target.value)}
              required
            />
          </div>
          <button type="submit" disabled={submitting || appointments.length === 0}>
            {submitting ? "Adding..." : "Add reminder"}
          </button>
        </div>
        {appointments.length === 0 && <p className="muted">Schedule an appointment before adding a reminder.</p>}
        {formError && <p className="error-text">{formError}</p>}
      </form>

      {loading && <p>Loading reminders...</p>}
      {loadError && <p className="error-text">{loadError}</p>}
      {actionError && <p className="error-text">{actionError}</p>}
      {!loading && !loadError && (
        <table>
          <thead>
            <tr>
              <th>Appointment</th>
              <th>Channel</th>
              <th>Send at</th>
              <th>Status</th>
              <th>Sent at</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {reminders.map((reminder) => {
              const appointment = appointmentsById.get(reminder.appointment_id);
              return (
                <tr key={reminder.id}>
                  <td>
                    {appointment ? `${appointment.petName} (${appointment.ownerName})` : reminder.appointment_id}
                  </td>
                  <td>{reminder.channel.toUpperCase()}</td>
                  <td>{formatDateTime(reminder.send_at)}</td>
                  <td>
                    <span className="status-pill">{STATUS_LABELS[reminder.status]}</span>
                  </td>
                  <td>{reminder.sent_at ? formatDateTime(reminder.sent_at) : "—"}</td>
                  <td>
                    <div className="actions">
                      {ALLOWED_TRANSITIONS[reminder.status].map((next) => (
                        <button
                          key={next}
                          type="button"
                          className="secondary"
                          onClick={() => handleTransition(reminder.id, next)}
                        >
                          {STATUS_LABELS[next]}
                        </button>
                      ))}
                    </div>
                  </td>
                </tr>
              );
            })}
            {reminders.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  No reminders yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </section>
  );
}
