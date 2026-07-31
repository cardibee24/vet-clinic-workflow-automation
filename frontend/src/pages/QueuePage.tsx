import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useToken } from "../auth/AuthContext";
import {
  APPOINTMENT_REASON_LABELS,
  formatTicketNumber,
  getQueue,
  updateAppointmentStatus,
  type QueueSummary,
} from "../api/appointments";
import { usePetDirectory } from "../hooks/usePetDirectory";
import { formatDateTime } from "../lib/format";

export function QueuePage() {
  const token = useToken();
  const petDirectory = usePetDirectory(token);

  const [queue, setQueue] = useState<QueueSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  function refresh() {
    setLoading(true);
    getQueue(token)
      .then((data) => {
        setQueue(data);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load queue"))
      .finally(() => setLoading(false));
  }

  useEffect(refresh, [token]);

  async function handleTransition(appointmentId: string, status: "in_progress" | "cancelled") {
    setActionError(null);
    setUpdatingId(appointmentId);
    try {
      await updateAppointmentStatus(token, appointmentId, status);
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to update appointment");
    } finally {
      setUpdatingId(null);
    }
  }

  const petsById = new Map(petDirectory.pets.map((pet) => [pet.id, pet]));

  return (
    <section>
      <h2>Queue</h2>
      <button type="button" className="secondary" onClick={refresh}>
        Refresh
      </button>

      {loading && <p style={{ marginTop: 16 }}>Loading queue...</p>}
      {error && <p className="error-text">{error}</p>}
      {actionError && <p className="error-text">{actionError}</p>}
      {!loading && !error && queue && (
        <>
          <p className="muted" style={{ marginTop: 16 }}>
            {queue.total_waiting} {queue.total_waiting === 1 ? "person" : "people"} waiting
          </p>
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Ticket</th>
                <th>Pet</th>
                <th>Owner</th>
                <th>Checked in</th>
                <th>Reason</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {queue.entries.map((entry) => {
                const pet = petsById.get(entry.pet_id);
                const updating = updatingId === entry.appointment_id;
                return (
                  <tr key={entry.appointment_id}>
                    <td>{entry.position}</td>
                    <td>{entry.ticket_number !== null ? formatTicketNumber(entry.ticket_number) : "—"}</td>
                    <td>{pet?.name ?? "Unknown pet"}</td>
                    <td>{pet?.ownerName ?? "Unknown owner"}</td>
                    <td>{entry.checked_in_at ? formatDateTime(entry.checked_in_at) : "—"}</td>
                    <td>{entry.reason ? APPOINTMENT_REASON_LABELS[entry.reason] : "—"}</td>
                    <td>
                      <div className="actions">
                        <button
                          type="button"
                          disabled={updating}
                          onClick={() => handleTransition(entry.appointment_id, "in_progress")}
                        >
                          {updating ? "Starting..." : "Start visit"}
                        </button>
                        <button
                          type="button"
                          className="secondary"
                          disabled={updating}
                          onClick={() => handleTransition(entry.appointment_id, "cancelled")}
                        >
                          Cancel
                        </button>
                        <Link to={`/appointments/${entry.appointment_id}`} className="secondary">
                          View
                        </Link>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {queue.entries.length === 0 && (
                <tr>
                  <td colSpan={7} className="muted">
                    Nobody is waiting right now.
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
