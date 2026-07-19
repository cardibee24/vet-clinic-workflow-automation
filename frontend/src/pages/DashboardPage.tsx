import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { QRCodeSVG } from "qrcode.react";
import { useToken } from "../auth/AuthContext";
import { APPOINTMENT_REASON_LABELS, getQueue, type QueueSummary } from "../api/appointments";
import { listInvoices, type Invoice } from "../api/invoices";
import { listOwners, type Owner } from "../api/owners";
import { useAppointmentDirectory } from "../hooks/useAppointmentDirectory";
import { formatDateTime, isToday, statusPillClass } from "../lib/format";

function todayDateString(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

const SELF_CHECK_IN_URL = `${window.location.origin}/self-check-in`;

const STATUS_LABELS: Record<string, string> = {
  scheduled: "Scheduled",
  checked_in: "Checked in",
  in_progress: "In progress",
  completed: "Completed",
  cancelled: "Cancelled",
  no_show: "No show",
};

export function DashboardPage() {
  const token = useToken();
  const { appointments, loading: appointmentsLoading, error: appointmentsError } = useAppointmentDirectory(token);

  const [queue, setQueue] = useState<QueueSummary | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [owners, setOwners] = useState<Owner[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([getQueue(token), listInvoices(token), listOwners(token)])
      .then(([queueData, invoiceData, ownerData]) => {
        setQueue(queueData);
        setInvoices(invoiceData);
        setOwners(ownerData);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load dashboard"))
      .finally(() => setLoading(false));
  }, [token]);

  const todaysAppointments = appointments
    .filter((appointment) => isToday(appointment.scheduled_at))
    .sort((a, b) => a.scheduled_at.localeCompare(b.scheduled_at));

  const unpaidInvoiceCount = invoices.filter(
    (invoice) => invoice.status === "draft" || invoice.status === "issued",
  ).length;

  const ownersById = new Map(owners.map((owner) => [owner.id, `${owner.first_name} ${owner.last_name}`]));
  const today = todayDateString();
  const overdueInvoices = invoices
    .filter((invoice) => invoice.status === "issued" && invoice.due_date !== null && invoice.due_date < today)
    .sort((a, b) => (a.due_date ?? "").localeCompare(b.due_date ?? ""));

  const isLoading = appointmentsLoading || loading;
  const loadError = appointmentsError ?? error;

  return (
    <section>
      <h2>Dashboard</h2>

      {isLoading && <p>Loading...</p>}
      {loadError && <p className="error-text">{loadError}</p>}

      {!isLoading && !loadError && (
        <>
          <div className="stat-grid">
            <div className="stat-tile">
              <div className="stat-label">Appointments today</div>
              <div className="stat-value">{todaysAppointments.length}</div>
              <Link to="/appointments" className="stat-link">
                View appointments
              </Link>
            </div>
            <div className="stat-tile">
              <div className="stat-label">Waiting now</div>
              <div className="stat-value">{queue?.total_waiting ?? 0}</div>
              <Link to="/queue" className="stat-link">
                View queue
              </Link>
            </div>
            <div className="stat-tile">
              <div className="stat-label">Unpaid invoices</div>
              <div className="stat-value">{unpaidInvoiceCount}</div>
              <Link to="/invoices" className="stat-link">
                View invoices
              </Link>
            </div>
            <div className="stat-tile">
              <div className="stat-label">Overdue invoices</div>
              <div className="stat-value">{overdueInvoices.length}</div>
              <Link to="/invoices" className="stat-link">
                View invoices
              </Link>
            </div>
          </div>

          <div className="actions" style={{ marginBottom: 24 }}>
            <Link to="/owners">
              <button type="button">Add owner</button>
            </Link>
            <Link to="/appointments">
              <button type="button" className="secondary">
                Schedule appointment
              </button>
            </Link>
          </div>

          <div className="card" style={{ display: "flex", gap: 20, alignItems: "center", maxWidth: 420 }}>
            <QRCodeSVG value={SELF_CHECK_IN_URL} size={96} />
            <div>
              <p style={{ margin: 0, fontWeight: 600, color: "var(--text-h)" }}>Walk-in self check-in</p>
              <p className="muted" style={{ marginTop: 4 }}>
                Print or display this QR code at reception. Returning clients can scan it to check themselves in
                without staff.
              </p>
            </div>
          </div>

          <h3>Today's appointments</h3>
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Pet</th>
                <th>Owner</th>
                <th>Status</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {todaysAppointments.map((appointment) => (
                <tr key={appointment.id}>
                  <td>{formatDateTime(appointment.scheduled_at)}</td>
                  <td>{appointment.petName}</td>
                  <td>{appointment.ownerName}</td>
                  <td>
                    <span className={`status-pill ${statusPillClass(appointment.status)}`}>
                      {STATUS_LABELS[appointment.status]}
                    </span>
                  </td>
                  <td>{appointment.reason ? APPOINTMENT_REASON_LABELS[appointment.reason] : "—"}</td>
                </tr>
              ))}
              {todaysAppointments.length === 0 && (
                <tr>
                  <td colSpan={5} className="muted">
                    No appointments scheduled for today.
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          <h3>Overdue invoices</h3>
          <table>
            <thead>
              <tr>
                <th>Owner</th>
                <th>Due date</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {overdueInvoices.map((invoice) => (
                <tr key={invoice.id}>
                  <td>{ownersById.get(invoice.owner_id) ?? invoice.owner_id}</td>
                  <td>{invoice.due_date}</td>
                  <td>
                    <Link to={`/invoices/${invoice.id}`} className="secondary">
                      View
                    </Link>
                  </td>
                </tr>
              ))}
              {overdueInvoices.length === 0 && (
                <tr>
                  <td colSpan={3} className="muted">
                    No overdue invoices.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}
