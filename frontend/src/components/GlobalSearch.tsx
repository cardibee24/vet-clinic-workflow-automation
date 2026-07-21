import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useToken } from "../auth/AuthContext";
import { listOwners, type Owner } from "../api/owners";
import { usePetDirectory } from "../hooks/usePetDirectory";

export function GlobalSearch() {
  const token = useToken();
  const navigate = useNavigate();
  const petDirectory = usePetDirectory(token);

  const [owners, setOwners] = useState<Owner[]>([]);
  useEffect(() => {
    listOwners(token)
      .then(setOwners)
      .catch(() => setOwners([]));
  }, [token]);

  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);

  const q = query.trim().toLowerCase();

  const matchedOwners = useMemo(() => {
    if (!q) return [];
    return owners
      .filter((owner) =>
        [`${owner.first_name} ${owner.last_name}`, owner.email, owner.phone].some((field) =>
          field?.toLowerCase().includes(q),
        ),
      )
      .slice(0, 5);
  }, [owners, q]);

  const matchedPets = useMemo(() => {
    if (!q) return [];
    return petDirectory.pets
      .filter((pet) => [pet.name, pet.ownerName].some((field) => field.toLowerCase().includes(q)))
      .slice(0, 5);
  }, [petDirectory.pets, q]);

  function goToOwner(ownerId: string) {
    navigate(`/owners/${ownerId}`);
    setQuery("");
    setOpen(false);
  }

  function goToPet(petId: string) {
    navigate(`/pets/${petId}`);
    setQuery("");
    setOpen(false);
  }

  const hasResults = matchedOwners.length > 0 || matchedPets.length > 0;

  return (
    <div className="global-search">
      <input
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder="Search owners or pets..."
        autoComplete="off"
      />
      {open && q && (
        <div className="combobox-menu">
          {matchedOwners.map((owner) => (
            <button
              type="button"
              key={`owner-${owner.id}`}
              className="combobox-option"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => goToOwner(owner.id)}
            >
              {owner.first_name} {owner.last_name} <span className="muted">Owner</span>
            </button>
          ))}
          {matchedPets.map((pet) => (
            <button
              type="button"
              key={`pet-${pet.id}`}
              className="combobox-option"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => goToPet(pet.id)}
            >
              {pet.name} <span className="muted">— {pet.ownerName}</span>
            </button>
          ))}
          {!hasResults && <div className="combobox-empty">No matches</div>}
        </div>
      )}
    </div>
  );
}
