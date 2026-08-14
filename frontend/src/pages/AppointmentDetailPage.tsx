import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useToken } from "../auth/AuthContext";
import {
  APPOINTMENT_REASON_LABELS,
  deleteAppointment,
  formatTicketNumber,
  getAppointmentInvoice,
  updateAppointment,
  updateAppointmentNotes,
  updateAppointmentStatus,
  type AppointmentReason,
  type AppointmentStatus,
} from "../api/appointments";
import { ApiError } from "../api/client";
import { useAppointmentDirectory } from "../hooks/useAppointmentDirectory";
import { createInvoice } from "../api/invoices";
import { formatDateTime, statusPillClass } from "../lib/format";

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

export function AppointmentDetailPage() {
  const token = useToken();
  const { appointmentId } = useParams<{ appointmentId: string }>();
  const navigate = useNavigate();
  const { appointments, loading, error, refresh } = useAppointmentDirectory(token);

  const appointment = appointments.find((a) => a.id === appointmentId) ?? null;

  const [actionError, setActionError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [billing, setBilling] = useState(false);

  const [editing, setEditing] = useState(false);
  const [editScheduledAt, setEditScheduledAt] = useState("");
  const [editReason, setEditReason] = useState<AppointmentReason | "">("");
  const [savingEdit, setSavingEdit] = useState(false);

  const [notesDraft, setNotesDraft] = useState("");
  const [prescriptionDraft, setPrescriptionDraft] = useState("");
  const [savingNotes, setSavingNotes] = useState(false);
  const notesLoadedForId = useRef<string | null>(null);

  useEffect(() => {
    if (appointment && notesLoadedForId.current !== appointment.id) {
      setNotesDraft(appointment.visit_notes ?? "");
      setPrescriptionDraft(appointment.prescription ?? "");
      notesLoadedForId.current = appointment.id;
    }
  }, [appointment]);

  async function handleTransition(status: AppointmentStatus) {
    if (!appointmentId) return;
    setActionError(null);
    try {
      await updateAppointmentStatus(token, appointmentId, status);
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to update appointment");
    }
  }

  function startEdit() {
    if (!appointment) return;
    setActionError(null);
    setEditScheduledAt(appointment.scheduled_at.slice(0, 16));
    setEditReason(appointment.reason ?? "");
    setEditing(true);
  }

  async function saveEdit() {
    if (!appointmentId) return;
    setSavingEdit(true);
    setActionError(null);
    try {
      await updateAppointment(token, appointmentId, {
        scheduled_at: editScheduledAt,
        reason: editReason || undefined,
      });
      setEditing(false);
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to update appointment");
    } finally {
      setSavingEdit(false);
    }
  }

  async function saveNotes() {
    if (!appointmentId) return;
    setSavingNotes(true);
    setActionError(null);
    try {
      await updateAppointmentNotes(token, appointmentId, notesDraft, prescriptionDraft);
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to update visit notes");
    } finally {
      setSavingNotes(false);
    }
  }

  async function handleBillVisit() {
    if (!appointment) return;
    setActionError(null);
    setBilling(true);
    try {
      let invoice;
      try {
        invoice = await getAppointmentInvoice(token, appointment.id);
      } catch (err) {
        if (!(err instanceof ApiError) || err.status !== 404) throw err;
        invoice = await createInvoice(token, { owner_id: appointment.ownerId, appointment_id: appointment.id });
      }
      navigate(`/invoices/${invoice.id}`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to bill this visit");
      setBilling(false);
    }
  }

  async function handleDelete() {
    if (!appointmentId) return;
    if (!window.confirm("Delete this appointment? This cannot be undone.")) {
      return;
    }
    setDeleting(true);
    setActionError(null);
    try {
      await deleteAppointment(token, appointmentId);
      navigate("/appointments");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to delete appointment");
      setDeleting(false);
    }
  }

  if (loading) return <p>Loading appointment...</p>;
  if (error) return <p className="error-text">{error}</p>;
  if (!appointment) return <p className="error-text">Appointment not found.</p>;

  const isTerminal = TERMINAL_STATUSES.includes(appointment.status);

  return (
    <section>
      <Link to="/appointments" className="back-link">
        &larr; Back to appointments
      </Link>
      <h2>{appointment.petName}</h2>
      <p className="muted">
        Owner:{" "}
        <Link to={`/owners/${appointment.ownerId}`}>{appointment.ownerName}</Link>
      </p>
      <p>
        <span className={`status-pill ${statusPillClass(appointment.status)}`}>
          {STATUS_LABELS[appointment.status]}
        </span>
        <span className="muted"> &middot; {formatDateTime(appointment.scheduled_at)}</span>
        {appointment.reason && (
          <span className="muted"> &middot; {APPOINTMENT_REASON_LABELS[appointment.reason]}</span>
        )}
        {appointment.ticket_number !== null && (
          <span className="muted"> &middot; ticket {formatTicketNumber(appointment.ticket_number)}</span>
        )}
      </p>

      {ALLOWED_TRANSITIONS[appointment.status].length > 0 && (
        <div className="actions" style={{ marginTop: 16 }}>
          {ALLOWED_TRANSITIONS[appointment.status].map((next) => (
            <button type="button" key={next} onClick={() => handleTransition(next)}>
              {STATUS_LABELS[next]}
            </button>
          ))}
        </div>
      )}

      {!isTerminal && (
        <div className="card" style={{ marginTop: 24 }}>
          <h3>Schedule</h3>
          {editing ? (
            <>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="edit_scheduled_at">Date &amp; time</label>
                  <input
                    id="edit_scheduled_at"
                    type="datetime-local"
                    value={editScheduledAt}
                    onChange={(e) => setEditScheduledAt(e.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="edit_reason">Reason</label>
                  <select
                    id="edit_reason"
                    value={editReason}
                    onChange={(e) => setEditReason(e.target.value as AppointmentReason | "")}
                  >
                    <option value="">No reason</option>
                    {Object.entries(APPOINTMENT_REASON_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="actions" style={{ marginTop: 12 }}>
                <button type="button" disabled={savingEdit} onClick={saveEdit}>
                  {savingEdit ? "Saving..." : "Save"}
                </button>
                <button type="button" className="secondary" onClick={() => setEditing(false)}>
                  Cancel
                </button>
              </div>
            </>
          ) : (
            <button type="button" className="secondary" onClick={startEdit}>
              Edit schedule
            </button>
          )}
        </div>
      )}

      <div className="card" style={{ marginTop: 24 }}>
        <h3>Visit notes</h3>
        <p className="muted">
          These feed the invoice automatically when you bill this visit &mdash; description becomes the
          consultation/diagnosis charge, prescription becomes the medication charge.
        </p>
        <div className="field">
          <label htmlFor="visit_notes">Description (checkup, diagnosis)</label>
          <textarea
            id="visit_notes"
            rows={3}
            value={notesDraft}
            onChange={(e) => setNotesDraft(e.target.value)}
            placeholder="e.g. Checkup, diagnosed with ear mites"
          />
        </div>
        <div className="field" style={{ marginTop: 12 }}>
          <label htmlFor="prescription">Prescription (medication, treatment given)</label>
          <textarea
            id="prescription"
            rows={3}
            value={prescriptionDraft}
            onChange={(e) => setPrescriptionDraft(e.target.value)}
            placeholder="e.g. Gave antifungal cream"
          />
        </div>
        <div className="actions" style={{ marginTop: 12 }}>
          <button type="button" disabled={savingNotes} onClick={saveNotes}>
            {savingNotes ? "Saving..." : "Save notes"}
          </button>
        </div>
      </div>

      <div className="actions" style={{ marginTop: 24 }}>
        <Link to={`/check-queue/${appointment.id}`} target="_blank" rel="noreferrer" className="secondary">
          Queue link
        </Link>
        <button type="button" className="secondary" disabled={billing} onClick={handleBillVisit}>
          {billing ? "Opening invoice..." : "Bill this visit"}
        </button>
        <button type="button" className="secondary" disabled={deleting} onClick={handleDelete}>
          {deleting ? "Deleting..." : "Delete appointment"}
        </button>
      </div>
      {actionError && <p className="error-text">{actionError}</p>}
    </section>
  );
}
