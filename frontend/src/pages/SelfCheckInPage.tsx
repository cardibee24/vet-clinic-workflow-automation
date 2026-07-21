import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { lookupOwnersByPhone, type PublicOwnerLookupResult } from "../api/owners";
import { APPOINTMENT_REASON_LABELS, selfCheckIn, type AppointmentReason } from "../api/appointments";

export function SelfCheckInPage() {
  const navigate = useNavigate();

  const [phone, setPhone] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [matches, setMatches] = useState<PublicOwnerLookupResult[]>([]);

  const [reason, setReason] = useState<AppointmentReason | "">("");
  const [checkingInPetId, setCheckingInPetId] = useState<string | null>(null);
  const [checkInError, setCheckInError] = useState<string | null>(null);

  async function handleSearch(event: FormEvent) {
    event.preventDefault();
    setSearching(true);
    setSearchError(null);
    try {
      const results = await lookupOwnersByPhone(phone);
      setMatches(results);
      setSearched(true);
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : "Something went wrong, please try again");
    } finally {
      setSearching(false);
    }
  }

  function startOver() {
    setSearched(false);
    setMatches([]);
    setPhone("");
    setReason("");
    setCheckInError(null);
  }

  async function handleCheckIn(petId: string) {
    setCheckingInPetId(petId);
    setCheckInError(null);
    try {
      const appointment = await selfCheckIn({ pet_id: petId, reason: reason || undefined });
      navigate(`/check-queue/${appointment.id}`);
    } catch (err) {
      setCheckInError(err instanceof Error ? err.message : "Failed to check in");
      setCheckingInPetId(null);
    }
  }

  return (
    <main className="page" style={{ maxWidth: 480, margin: "0 auto" }}>
      <div className="brand" style={{ justifyContent: "center", marginBottom: 8 }}>
        VetFlow
      </div>
      <h2 style={{ textAlign: "center" }}>Self check-in</h2>

      {!searched && (
        <form onSubmit={handleSearch}>
          <div className="field">
            <label htmlFor="phone">Phone number on file</label>
            <input
              id="phone"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="e.g. 555-1234"
              required
            />
          </div>
          <button type="submit" disabled={searching} style={{ marginTop: 12 }}>
            {searching ? "Looking..." : "Find me"}
          </button>
          {searchError && <p className="error-text">{searchError}</p>}
        </form>
      )}

      {searched && matches.length === 0 && (
        <div className="card">
          <p>We couldn't find you with that number.</p>
          <p className="muted">Please check in with the front desk instead.</p>
          <button type="button" className="secondary" style={{ marginTop: 12 }} onClick={startOver}>
            Try a different number
          </button>
        </div>
      )}

      {searched && matches.length > 0 && (
        <>
          <div className="field" style={{ marginBottom: 16 }}>
            <label htmlFor="reason">Reason for visit (optional)</label>
            <select id="reason" value={reason} onChange={(e) => setReason(e.target.value as AppointmentReason | "")}>
              <option value="">No reason</option>
              {Object.entries(APPOINTMENT_REASON_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <p className="muted">Which pet are you checking in?</p>
          {matches.map((owner) => (
            <div key={owner.owner_id} className="card">
              <p>
                <strong>
                  {owner.first_name} {owner.last_name}
                </strong>
              </p>
              <div className="actions">
                {owner.pets.map((pet) => (
                  <button
                    key={pet.id}
                    type="button"
                    disabled={checkingInPetId !== null}
                    onClick={() => handleCheckIn(pet.id)}
                  >
                    {checkingInPetId === pet.id ? "Checking in..." : `Check in ${pet.name} (${pet.species})`}
                  </button>
                ))}
                {owner.pets.length === 0 && <span className="muted">No pets on file.</span>}
              </div>
            </div>
          ))}

          {checkInError && <p className="error-text">{checkInError}</p>}
          <button type="button" className="secondary" onClick={startOver}>
            Not you? Try a different number
          </button>
        </>
      )}
    </main>
  );
}
