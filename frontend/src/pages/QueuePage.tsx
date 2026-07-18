import { useEffect, useState } from "react";
import { useToken } from "../auth/AuthContext";
import { getQueue, type QueueSummary } from "../api/appointments";
import { usePetDirectory } from "../hooks/usePetDirectory";
import { formatDateTime } from "../lib/format";

export function QueuePage() {
  const token = useToken();
  const petDirectory = usePetDirectory(token);

  const [queue, setQueue] = useState<QueueSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  const petsById = new Map(petDirectory.pets.map((pet) => [pet.id, pet]));

  return (
    <section>
      <h2>Queue</h2>
      <button type="button" className="secondary" onClick={refresh}>
        Refresh
      </button>

      {loading && <p style={{ marginTop: 16 }}>Loading queue...</p>}
      {error && <p className="error-text">{error}</p>}
      {!loading && !error && queue && (
        <>
          <p className="muted" style={{ marginTop: 16 }}>
            {queue.total_waiting} {queue.total_waiting === 1 ? "person" : "people"} waiting
          </p>
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Pet</th>
                <th>Owner</th>
                <th>Checked in</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {queue.entries.map((entry) => {
                const pet = petsById.get(entry.pet_id);
                return (
                  <tr key={entry.appointment_id}>
                    <td>{entry.position}</td>
                    <td>{pet?.name ?? "Unknown pet"}</td>
                    <td>{pet?.ownerName ?? "Unknown owner"}</td>
                    <td>{entry.checked_in_at ? formatDateTime(entry.checked_in_at) : "—"}</td>
                    <td>{entry.reason ?? "—"}</td>
                  </tr>
                );
              })}
              {queue.entries.length === 0 && (
                <tr>
                  <td colSpan={5} className="muted">
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
