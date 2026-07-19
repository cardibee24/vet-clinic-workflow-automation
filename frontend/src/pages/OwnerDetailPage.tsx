import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { useToken } from "../auth/AuthContext";
import { addPet, getOwner, type OwnerWithPets } from "../api/owners";
import { deletePet, updatePet } from "../api/pets";

interface PetEditState {
  name: string;
  species: string;
  breed: string;
  dateOfBirth: string;
}

export function OwnerDetailPage() {
  const token = useToken();
  const { ownerId } = useParams<{ ownerId: string }>();

  const [owner, setOwner] = useState<OwnerWithPets | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [species, setSpecies] = useState("");
  const [breed, setBreed] = useState("");
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);
  const [deletingPetId, setDeletingPetId] = useState<string | null>(null);

  const [editingPetId, setEditingPetId] = useState<string | null>(null);
  const [petEditState, setPetEditState] = useState<PetEditState | null>(null);
  const [savingEdit, setSavingEdit] = useState(false);

  function refresh() {
    if (!ownerId) return;
    setLoading(true);
    getOwner(token, ownerId)
      .then((data) => {
        setOwner(data);
        setLoadError(null);
      })
      .catch((error: unknown) => setLoadError(error instanceof Error ? error.message : "Failed to load owner"))
      .finally(() => setLoading(false));
  }

  useEffect(refresh, [token, ownerId]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!ownerId) return;
    setSubmitting(true);
    setFormError(null);
    try {
      await addPet(token, ownerId, {
        name,
        species,
        breed: breed || undefined,
        date_of_birth: dateOfBirth || undefined,
      });
      setName("");
      setSpecies("");
      setBreed("");
      setDateOfBirth("");
      refresh();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Failed to add pet");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeletePet(pet: OwnerWithPets["pets"][number]) {
    if (!window.confirm(`Delete ${pet.name}? This cannot be undone.`)) {
      return;
    }
    setDeletingPetId(pet.id);
    setRowError(null);
    try {
      await deletePet(token, pet.id);
      refresh();
    } catch (error) {
      setRowError(error instanceof Error ? error.message : "Failed to delete pet");
    } finally {
      setDeletingPetId(null);
    }
  }

  function startEditPet(pet: OwnerWithPets["pets"][number]) {
    setRowError(null);
    setEditingPetId(pet.id);
    setPetEditState({
      name: pet.name,
      species: pet.species,
      breed: pet.breed ?? "",
      dateOfBirth: pet.date_of_birth ?? "",
    });
  }

  function cancelEditPet() {
    setEditingPetId(null);
    setPetEditState(null);
  }

  async function saveEditPet(petId: string) {
    if (!petEditState) return;
    setSavingEdit(true);
    setRowError(null);
    try {
      await updatePet(token, petId, {
        name: petEditState.name,
        species: petEditState.species,
        breed: petEditState.breed || undefined,
        date_of_birth: petEditState.dateOfBirth || undefined,
      });
      cancelEditPet();
      refresh();
    } catch (error) {
      setRowError(error instanceof Error ? error.message : "Failed to update pet");
    } finally {
      setSavingEdit(false);
    }
  }

  if (loading) return <p>Loading owner...</p>;
  if (loadError) return <p className="error-text">{loadError}</p>;
  if (!owner) return null;

  return (
    <section>
      <p>
        <Link to="/owners">&larr; Back to owners</Link>
      </p>
      <h2>
        {owner.first_name} {owner.last_name}
      </h2>
      <p className="muted">
        {owner.email ?? "No email"} &middot; {owner.phone ?? "No phone"}
      </p>

      <h3>Pets</h3>
      {rowError && <p className="error-text">{rowError}</p>}
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Species</th>
            <th>Breed</th>
            <th>Date of birth</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {owner.pets.map((pet) =>
            editingPetId === pet.id && petEditState ? (
              <tr key={pet.id}>
                <td>
                  <input
                    value={petEditState.name}
                    onChange={(e) => setPetEditState({ ...petEditState, name: e.target.value })}
                    placeholder="Name"
                  />
                </td>
                <td>
                  <input
                    value={petEditState.species}
                    onChange={(e) => setPetEditState({ ...petEditState, species: e.target.value })}
                    placeholder="Species"
                  />
                </td>
                <td>
                  <input
                    value={petEditState.breed}
                    onChange={(e) => setPetEditState({ ...petEditState, breed: e.target.value })}
                    placeholder="Breed"
                  />
                </td>
                <td>
                  <input
                    type="date"
                    value={petEditState.dateOfBirth}
                    onChange={(e) => setPetEditState({ ...petEditState, dateOfBirth: e.target.value })}
                  />
                </td>
                <td>
                  <div className="actions">
                    <button type="button" disabled={savingEdit} onClick={() => saveEditPet(pet.id)}>
                      {savingEdit ? "Saving..." : "Save"}
                    </button>
                    <button type="button" className="secondary" onClick={cancelEditPet}>
                      Cancel
                    </button>
                  </div>
                </td>
              </tr>
            ) : (
              <tr key={pet.id}>
                <td>
                  <Link to={`/pets/${pet.id}`}>{pet.name}</Link>
                </td>
                <td>{pet.species}</td>
                <td>{pet.breed ?? "—"}</td>
                <td>{pet.date_of_birth ?? "—"}</td>
                <td>
                  <div className="actions">
                    <button type="button" className="secondary" onClick={() => startEditPet(pet)}>
                      Edit
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      disabled={deletingPetId === pet.id}
                      onClick={() => handleDeletePet(pet)}
                    >
                      {deletingPetId === pet.id ? "Deleting..." : "Delete"}
                    </button>
                  </div>
                </td>
              </tr>
            ),
          )}
          {owner.pets.length === 0 && (
            <tr>
              <td colSpan={5} className="muted">
                No pets yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <form className="card" onSubmit={handleSubmit} style={{ marginTop: 24 }}>
        <h3>Add a pet</h3>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="pet_name">Name</label>
            <input id="pet_name" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="species">Species</label>
            <input id="species" value={species} onChange={(e) => setSpecies(e.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="breed">Breed</label>
            <input id="breed" value={breed} onChange={(e) => setBreed(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="date_of_birth">Date of birth</label>
            <input
              id="date_of_birth"
              type="date"
              value={dateOfBirth}
              onChange={(e) => setDateOfBirth(e.target.value)}
            />
          </div>
          <button type="submit" disabled={submitting}>
            {submitting ? "Adding..." : "Add pet"}
          </button>
        </div>
        {formError && <p className="error-text">{formError}</p>}
      </form>
    </section>
  );
}
