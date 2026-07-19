import { Fragment, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useToken } from "../auth/AuthContext";
import {
  APPOINTMENT_REASON_LABELS,
  createAppointment,
  deleteAppointment,
  updateAppointment,
  updateAppointmentNotes,
  updateAppointmentStatus,
  type AppointmentReason,
  type AppointmentStatus,
} from "../api/appointments";
import { useAppointmentDirectory, type DirectoryAppointment } from "../hooks/useAppointmentDirectory";
import { usePetDirectory } from "../hooks/usePetDirectory";
import { formatDateTime, statusPillClass } from "../lib/format";

function toDateInputValue(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

const ALLOWED_TRANSITIONS: Record<AppointmentStatus, AppointmentStatus[]> = {
  scheduled: ["checked_in", "cancelled", "no_show"],
  checked_in: ["in_progress", "cancelled"],
  in_progress: ["completed", "cancelled"],
  completed: [],
  cancelled: [],
  no_show: [],
};

const TERMINAL_STATUSES: AppointmentStatus[] = ["completed", "cancelled", "no_show"];

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
  const [reason, setReason] = useState<AppointmentReason | "">("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editScheduledAt, setEditScheduledAt] = useState("");
  const [editReason, setEditReason] = useState<AppointmentReason | "">("");
  const [savingEdit, setSavingEdit] = useState(false);

  const [notesEditingId, setNotesEditingId] = useState<string | null>(null);
  const [notesDraft, setNotesDraft] = useState("");
  const [savingNotes, setSavingNotes] = useState(false);

  const [viewMode, setViewMode] = useState<"list" | "day">("list");
  const [dayDate, setDayDate] = useState(() => toDateInputValue(new Date()));

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<AppointmentStatus | "all">("all");
  const query = search.trim().toLowerCase();
  const visibleAppointments = appointments.filter((appointment) => {
    if (statusFilter !== "all" && appointment.status !== statusFilter) return false;
    if (!query) return true;
    const reasonLabel = appointment.reason ? APPOINTMENT_REASON_LABELS[appointment.reason] : null;
    return [appointment.petName, appointment.ownerName, reasonLabel].some((field) =>
      field?.toLowerCase().includes(query),
    );
  });

  const dayAppointments = appointments
    .filter((appointment) => appointment.scheduled_at.slice(0, 10) === dayDate)
    .sort((a, b) => a.scheduled_at.localeCompare(b.scheduled_at));

  function shiftDay(days: number) {
    const next = new Date(`${dayDate}T00:00:00`);
    next.setDate(next.getDate() + days);
    setDayDate(toDateInputValue(next));
  }

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

  function startEdit(appointmentId: string, scheduledAtValue: string, reasonValue: AppointmentReason | null) {
    setActionError(null);
    setEditingId(appointmentId);
    setEditScheduledAt(scheduledAtValue.slice(0, 16));
    setEditReason(reasonValue ?? "");
  }

  function cancelEdit() {
    setEditingId(null);
  }

  async function saveEdit(appointmentId: string) {
    setSavingEdit(true);
    setActionError(null);
    try {
      await updateAppointment(token, appointmentId, {
        scheduled_at: editScheduledAt,
        reason: editReason || undefined,
      });
      cancelEdit();
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to update appointment");
    } finally {
      setSavingEdit(false);
    }
  }

  function startNotesEdit(appointmentId: string, currentNotes: string | null) {
    setActionError(null);
    setNotesEditingId(appointmentId);
    setNotesDraft(currentNotes ?? "");
  }

  function cancelNotesEdit() {
    setNotesEditingId(null);
  }

  async function saveNotes(appointmentId: string) {
    setSavingNotes(true);
    setActionError(null);
    try {
      await updateAppointmentNotes(token, appointmentId, notesDraft);
      cancelNotesEdit();
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to update visit notes");
    } finally {
      setSavingNotes(false);
    }
  }

  function renderRow(appointment: DirectoryAppointment) {
    return (
      <Fragment key={appointment.id}>
        {editingId === appointment.id ? (
          <tr>
            <td>{appointment.petName}</td>
            <td>{appointment.ownerName}</td>
            <td>
              <input
                type="datetime-local"
                value={editScheduledAt}
                onChange={(e) => setEditScheduledAt(e.target.value)}
              />
            </td>
            <td>
              <span className={`status-pill ${statusPillClass(appointment.status)}`}>{STATUS_LABELS[appointment.status]}</span>
            </td>
            <td>
              <select value={editReason} onChange={(e) => setEditReason(e.target.value as AppointmentReason | "")}>
                <option value="">No reason</option>
                {Object.entries(APPOINTMENT_REASON_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </td>
            <td>
              <div className="actions">
                <button type="button" disabled={savingEdit} onClick={() => saveEdit(appointment.id)}>
                  {savingEdit ? "Saving..." : "Save"}
                </button>
                <button type="button" className="secondary" onClick={cancelEdit}>
                  Cancel
                </button>
              </div>
            </td>
          </tr>
        ) : (
          <tr>
            <td>{appointment.petName}</td>
            <td>{appointment.ownerName}</td>
            <td>{formatDateTime(appointment.scheduled_at)}</td>
            <td>
              <span className={`status-pill ${statusPillClass(appointment.status)}`}>{STATUS_LABELS[appointment.status]}</span>
            </td>
            <td>{appointment.reason ? APPOINTMENT_REASON_LABELS[appointment.reason] : "—"}</td>
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
                <Link to={`/check-queue/${appointment.id}`} target="_blank" rel="noreferrer" className="secondary">
                  Queue link
                </Link>
                {!TERMINAL_STATUSES.includes(appointment.status) && (
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => startEdit(appointment.id, appointment.scheduled_at, appointment.reason)}
                  >
                    Edit
                  </button>
                )}
                <button
                  type="button"
                  className="secondary"
                  onClick={() => startNotesEdit(appointment.id, appointment.visit_notes)}
                >
                  Visit notes
                </button>
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
        )}
        {notesEditingId === appointment.id && (
          <tr>
            <td colSpan={6}>
              <div className="field">
                <label htmlFor={`visit_notes_${appointment.id}`}>Visit notes for {appointment.petName}</label>
                <textarea
                  id={`visit_notes_${appointment.id}`}
                  rows={3}
                  value={notesDraft}
                  onChange={(e) => setNotesDraft(e.target.value)}
                />
              </div>
              <div className="actions">
                <button type="button" disabled={savingNotes} onClick={() => saveNotes(appointment.id)}>
                  {savingNotes ? "Saving..." : "Save notes"}
                </button>
                <button type="button" className="secondary" onClick={cancelNotesEdit}>
                  Cancel
                </button>
              </div>
            </td>
          </tr>
        )}
      </Fragment>
    );
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
            <select
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value as AppointmentReason | "")}
            >
              <option value="">No reason</option>
              {Object.entries(APPOINTMENT_REASON_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
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
        <>
          <div className="actions" style={{ marginBottom: 12 }}>
            <button
              type="button"
              className={viewMode === "list" ? undefined : "secondary"}
              onClick={() => setViewMode("list")}
            >
              List
            </button>
            <button
              type="button"
              className={viewMode === "day" ? undefined : "secondary"}
              onClick={() => setViewMode("day")}
            >
              Day view
            </button>
          </div>

          {viewMode === "list" ? (
            <>
              <div className="form-grid" style={{ marginBottom: 12, maxWidth: 480 }}>
                <div className="field">
                  <label htmlFor="appointment_search">Search</label>
                  <input
                    id="appointment_search"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Pet, owner, or reason"
                  />
                </div>
                <div className="field">
                  <label htmlFor="status_filter">Status</label>
                  <select
                    id="status_filter"
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value as AppointmentStatus | "all")}
                  >
                    <option value="all">All</option>
                    {Object.entries(STATUS_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
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
                  {visibleAppointments.map(renderRow)}
                  {visibleAppointments.length === 0 && (
                    <tr>
                      <td colSpan={6} className="muted">
                        {appointments.length === 0 ? "No appointments yet." : "No appointments match your filters."}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </>
          ) : (
            <>
              <div className="actions" style={{ marginBottom: 12 }}>
                <button type="button" className="secondary" onClick={() => shiftDay(-1)}>
                  &larr; Previous day
                </button>
                <input type="date" value={dayDate} onChange={(e) => setDayDate(e.target.value)} />
                <button type="button" className="secondary" onClick={() => shiftDay(1)}>
                  Next day &rarr;
                </button>
                <button type="button" className="secondary" onClick={() => setDayDate(toDateInputValue(new Date()))}>
                  Today
                </button>
              </div>
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
                  {dayAppointments.map(renderRow)}
                  {dayAppointments.length === 0 && (
                    <tr>
                      <td colSpan={6} className="muted">
                        No appointments scheduled for this day.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </>
          )}
        </>
      )}
    </section>
  );
}
