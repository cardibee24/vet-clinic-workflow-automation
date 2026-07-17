import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useToken } from "../auth/AuthContext";
import { createInvoice, listInvoices, type Invoice, type InvoiceStatus } from "../api/invoices";
import { listOwners, type Owner } from "../api/owners";
import { useAppointmentDirectory } from "../hooks/useAppointmentDirectory";

const STATUS_LABELS: Record<InvoiceStatus, string> = {
  draft: "Draft",
  issued: "Issued",
  paid: "Paid",
  void: "Void",
};

export function InvoicesPage() {
  const token = useToken();
  const { appointments } = useAppointmentDirectory(token);

  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [owners, setOwners] = useState<Owner[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [ownerId, setOwnerId] = useState("");
  const [appointmentId, setAppointmentId] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  function refresh() {
    setLoading(true);
    Promise.all([listInvoices(token), listOwners(token)])
      .then(([invoiceData, ownerData]) => {
        setInvoices(invoiceData);
        setOwners(ownerData);
        setLoadError(null);
      })
      .catch((err: unknown) => setLoadError(err instanceof Error ? err.message : "Failed to load invoices"))
      .finally(() => setLoading(false));
  }

  useEffect(refresh, [token]);

  const ownersById = new Map(owners.map((owner) => [owner.id, `${owner.first_name} ${owner.last_name}`]));
  const appointmentsForOwner = appointments.filter((appointment) => appointment.ownerId === ownerId);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await createInvoice(token, {
        owner_id: ownerId,
        appointment_id: appointmentId || undefined,
        due_date: dueDate || undefined,
        notes: notes || undefined,
      });
      setOwnerId("");
      setAppointmentId("");
      setDueDate("");
      setNotes("");
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create invoice");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section>
      <h2>Invoices</h2>

      <form className="card" onSubmit={handleSubmit}>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="owner">Owner</label>
            <select
              id="owner"
              value={ownerId}
              onChange={(e) => {
                setOwnerId(e.target.value);
                setAppointmentId("");
              }}
              required
            >
              <option value="" disabled>
                Select an owner
              </option>
              {owners.map((owner) => (
                <option key={owner.id} value={owner.id}>
                  {owner.first_name} {owner.last_name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="appointment">Appointment (optional)</label>
            <select
              id="appointment"
              value={appointmentId}
              onChange={(e) => setAppointmentId(e.target.value)}
              disabled={!ownerId}
            >
              <option value="">No appointment</option>
              {appointmentsForOwner.map((appointment) => (
                <option key={appointment.id} value={appointment.id}>
                  {appointment.petName} — {appointment.scheduled_start.replace("T", " ")}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="due_date">Due date</label>
            <input id="due_date" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="notes">Notes</label>
            <input id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
          <button type="submit" disabled={submitting || owners.length === 0}>
            {submitting ? "Creating..." : "Create invoice"}
          </button>
        </div>
        {owners.length === 0 && <p className="muted">Add an owner before creating an invoice.</p>}
        {formError && <p className="error-text">{formError}</p>}
      </form>

      {loading && <p>Loading invoices...</p>}
      {loadError && <p className="error-text">{loadError}</p>}
      {!loading && !loadError && (
        <table>
          <thead>
            <tr>
              <th>Owner</th>
              <th>Status</th>
              <th>Due date</th>
              <th>Notes</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((invoice) => (
              <tr key={invoice.id}>
                <td>{ownersById.get(invoice.owner_id) ?? invoice.owner_id}</td>
                <td>
                  <span className="status-pill">{STATUS_LABELS[invoice.status]}</span>
                </td>
                <td>{invoice.due_date ?? "—"}</td>
                <td>{invoice.notes ?? "—"}</td>
                <td>
                  <Link to={`/invoices/${invoice.id}`}>View</Link>
                </td>
              </tr>
            ))}
            {invoices.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  No invoices yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </section>
  );
}
