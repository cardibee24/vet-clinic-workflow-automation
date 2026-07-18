import { apiFetch } from "./client";
import type { Pet } from "./owners";

export function listPets(token: string): Promise<Pet[]> {
  return apiFetch("/api/pets", { token });
}

export function deletePet(token: string, petId: string): Promise<void> {
  return apiFetch(`/api/pets/${petId}`, { method: "DELETE", token });
}
