import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useToken } from "../auth/AuthContext";
import { APPOINTMENT_REASON_LABELS, listAppointments, type Appointment } from "../api/appointments";
import { listOwners, type Owner, type Pet } from "../api/owners";
import { listPets } from "../api/pets";
import { formatDateTime, statusPillClass } from "../lib/format";

const STATUS_LABELS: Record<string, string> = {
  scheduled: "Scheduled",
  checked_in: "Checked in",
  in_progress: "In progress",
  completed: "Completed",
  cancelled: "Cancelled",
  no_show: "No show",
};

export function PetDetailPage() {
  const token = useToken();
  const { petId } = useParams<{ petId: string }>();

  const [pet, setPet] = useState<Pet | null>(null);
  const [owner, setOwner] = useState<Owner | null>(null);
  const [visits, setVisits] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!petId) return;
    setLoading(true);
    Promise.all([listPets(token), listOwners(token), listAppointments(token)])
      .then(([pets, owners, appointments]) => {
        const foundPet = pets.find((p) => p.id === petId) ?? null;
        setPet(foundPet);
        setOwner(owners.find((o) => o.id === foundPet?.owner_id) ?? null);
        setVisits(
          appointments
            .filter((appointment) => appointment.pet_id === petId)
            .sort((a, b) => b.scheduled_at.localeCompare(a.scheduled_at)),
        );
        setLoadError(null);
      })
      .catch((err: unknown) => setLoadError(err instanceof Error ? err.message : "Failed to load pet"))
      .finally(() => setLoading(false));
  }, [token, petId]);

  if (loading) return <p>Loading pet...</p>;
  if (loadError) return <p className="error-text">{loadError}</p>;
  if (!pet) return <p className="error-text">Pet not found.</p>;

  return (
    <section>
      {owner && (
        <Link to={`/owners/${owner.id}`} className="back-link">
          &larr; Back to {owner.first_name} {owner.last_name}
        </Link>
      )}
      <h2>{pet.name}</h2>
      <p className="muted">
        {pet.species}
        {pet.breed && ` · ${pet.breed}`}
        {pet.date_of_birth && ` · born ${pet.date_of_birth}`}
      </p>

      <h3>Visit history</h3>
      <table>
        <thead>
          <tr>
            <th>Date &amp; time</th>
            <th>Status</th>
            <th>Reason</th>
            <th>Visit notes</th>
          </tr>
        </thead>
        <tbody>
          {visits.map((visit) => (
            <tr key={visit.id}>
              <td>{formatDateTime(visit.scheduled_at)}</td>
              <td>
                <span className={`status-pill ${statusPillClass(visit.status)}`}>{STATUS_LABELS[visit.status]}</span>
              </td>
              <td>{visit.reason ? APPOINTMENT_REASON_LABELS[visit.reason] : "—"}</td>
              <td>{visit.visit_notes ?? "—"}</td>
            </tr>
          ))}
          {visits.length === 0 && (
            <tr>
              <td colSpan={4} className="muted">
                No visits recorded yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}
