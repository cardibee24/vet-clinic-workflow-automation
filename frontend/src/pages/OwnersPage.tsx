import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useToken } from "../auth/AuthContext";
import { createOwner, listOwners, type Owner } from "../api/owners";

export function OwnersPage() {
  const token = useToken();

  const [owners, setOwners] = useState<Owner[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  function refresh() {
    setLoading(true);
    listOwners(token)
      .then((data) => {
        setOwners(data);
        setLoadError(null);
      })
      .catch((error: unknown) => setLoadError(error instanceof Error ? error.message : "Failed to load owners"))
      .finally(() => setLoading(false));
  }

  useEffect(refresh, [token]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await createOwner(token, {
        first_name: firstName,
        last_name: lastName,
        email: email || undefined,
        phone: phone || undefined,
      });
      setFirstName("");
      setLastName("");
      setEmail("");
      setPhone("");
      refresh();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Failed to create owner");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section>
      <h2>Owners</h2>

      <form className="card" onSubmit={handleSubmit}>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="first_name">First name</label>
            <input id="first_name" value={firstName} onChange={(e) => setFirstName(e.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="last_name">Last name</label>
            <input id="last_name" value={lastName} onChange={(e) => setLastName(e.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="phone">Phone</label>
            <input id="phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>
          <button type="submit" disabled={submitting}>
            {submitting ? "Adding..." : "Add owner"}
          </button>
        </div>
        {formError && <p className="error-text">{formError}</p>}
      </form>

      {loading && <p>Loading owners...</p>}
      {loadError && <p className="error-text">{loadError}</p>}
      {!loading && !loadError && (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Phone</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {owners.map((owner) => (
              <tr key={owner.id}>
                <td>
                  {owner.first_name} {owner.last_name}
                </td>
                <td>{owner.email ?? "—"}</td>
                <td>{owner.phone ?? "—"}</td>
                <td>
                  <Link to={`/owners/${owner.id}`}>View</Link>
                </td>
              </tr>
            ))}
            {owners.length === 0 && (
              <tr>
                <td colSpan={4} className="muted">
                  No owners yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </section>
  );
}
