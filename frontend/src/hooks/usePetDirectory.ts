import { useCallback, useEffect, useState } from "react";
import { listOwners } from "../api/owners";
import { listPets } from "../api/pets";

export interface DirectoryPet {
  id: string;
  name: string;
  species: string;
  ownerId: string;
  ownerName: string;
}

interface State {
  pets: DirectoryPet[];
  loading: boolean;
  error: string | null;
}

export function usePetDirectory(token: string) {
  const [state, setState] = useState<State>({ pets: [], loading: true, error: null });

  const refresh = useCallback(() => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    Promise.all([listOwners(token), listPets(token)])
      .then(([owners, pets]) => {
        const ownerNames = new Map(owners.map((owner) => [owner.id, `${owner.first_name} ${owner.last_name}`]));
        const directory = pets.map((pet) => ({
          id: pet.id,
          name: pet.name,
          species: pet.species,
          ownerId: pet.owner_id,
          ownerName: ownerNames.get(pet.owner_id) ?? "Unknown owner",
        }));
        setState({ pets: directory, loading: false, error: null });
      })
      .catch((error: unknown) =>
        setState({ pets: [], loading: false, error: error instanceof Error ? error.message : "Failed to load pets" }),
      );
  }, [token]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { ...state, refresh };
}
