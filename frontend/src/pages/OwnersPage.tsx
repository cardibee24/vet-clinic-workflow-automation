import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useToken } from "../auth/AuthContext";
import { createOwner, deleteOwner, updateOwner, listOwners, type Owner } from "../api/owners";

interface EditState {
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
}

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
  const [rowError, setRowError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editState, setEditState] = useState<EditState | null>(null);
  const [savingEdit, setSavingEdit] = useState(false);

  const [search, setSearch] = useState("");
  const query = search.trim().toLowerCase();
  const visibleOwners = query
    ? owners.filter((owner) =>
        [owner.first_name, owner.last_name, owner.email, owner.phone].some((field) =>
          field?.toLowerCase().includes(query),
        ),
      )
    : owners;

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

  async function handleDelete(owner: Owner) {
    if (!window.confirm(`Delete ${owner.first_name} ${owner.last_name}? This cannot be undone.`)) {
      return;
    }
    setDeletingId(owner.id);
    setRowError(null);
    try {
      await deleteOwner(token, owner.id);
      refresh();
    } catch (error) {
      setRowError(error instanceof Error ? error.message : "Failed to delete owner");
    } finally {
      setDeletingId(null);
    }
  }

  function startEdit(owner: Owner) {
    setRowError(null);
    setEditingId(owner.id);
    setEditState({
      firstName: owner.first_name,
      lastName: owner.last_name,
      email: owner.email ?? "",
      phone: owner.phone ?? "",
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setEditState(null);
  }

  async function saveEdit(ownerId: string) {
    if (!editState) return;
    setSavingEdit(true);
    setRowError(null);
    try {
      await updateOwner(token, ownerId, {
        first_name: editState.firstName,
        last_name: editState.lastName,
        email: editState.email || undefined,
        phone: editState.phone || undefined,
      });
      cancelEdit();
      refresh();
    } catch (error) {
      setRowError(error instanceof Error ? error.message : "Failed to update owner");
    } finally {
      setSavingEdit(false);
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
      {rowError && <p className="error-text">{rowError}</p>}
      {!loading && !loadError && (
        <>
          <div className="field" style={{ maxWidth: 320, marginBottom: 12 }}>
            <label htmlFor="owner_search">Search</label>
            <input
              id="owner_search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Name, email, or phone"
            />
          </div>
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
              {visibleOwners.map((owner) =>
                editingId === owner.id && editState ? (
                  <tr key={owner.id}>
                    <td>
                      <div className="form-grid">
                        <input
                          value={editState.firstName}
                          onChange={(e) => setEditState({ ...editState, firstName: e.target.value })}
                          placeholder="First name"
                        />
                        <input
                          value={editState.lastName}
                          onChange={(e) => setEditState({ ...editState, lastName: e.target.value })}
                          placeholder="Last name"
                        />
                      </div>
                    </td>
                    <td>
                      <input
                        value={editState.email}
                        onChange={(e) => setEditState({ ...editState, email: e.target.value })}
                        placeholder="Email"
                      />
                    </td>
                    <td>
                      <input
                        value={editState.phone}
                        onChange={(e) => setEditState({ ...editState, phone: e.target.value })}
                        placeholder="Phone"
                      />
                    </td>
                    <td>
                      <div className="actions">
                        <button type="button" disabled={savingEdit} onClick={() => saveEdit(owner.id)}>
                          {savingEdit ? "Saving..." : "Save"}
                        </button>
                        <button type="button" className="secondary" onClick={cancelEdit}>
                          Cancel
                        </button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  <tr key={owner.id}>
                    <td>
                      {owner.first_name} {owner.last_name}
                    </td>
                    <td>{owner.email ?? "—"}</td>
                    <td>{owner.phone ?? "—"}</td>
                    <td>
                      <div className="actions">
                        <Link to={`/owners/${owner.id}`}>View</Link>
                        <button type="button" className="secondary" onClick={() => startEdit(owner)}>
                          Edit
                        </button>
                        <button
                          type="button"
                          className="secondary"
                          disabled={deletingId === owner.id}
                          onClick={() => handleDelete(owner)}
                        >
                          {deletingId === owner.id ? "Deleting..." : "Delete"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ),
              )}
              {visibleOwners.length === 0 && (
                <tr>
                  <td colSpan={4} className="muted">
                    {owners.length === 0 ? "No owners yet." : "No owners match your search."}
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
