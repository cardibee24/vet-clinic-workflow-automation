import { apiFetch } from "./client";
import type { Pet } from "./owners";

export interface PetUpdateInput {
  name?: string;
  species?: string;
  breed?: string;
  date_of_birth?: string;
}

export function listPets(token: string): Promise<Pet[]> {
  return apiFetch("/api/pets", { token });
}

export function updatePet(token: string, petId: string, body: PetUpdateInput): Promise<Pet> {
  return apiFetch(`/api/pets/${petId}`, { method: "PATCH", token, body });
}

export function deletePet(token: string, petId: string): Promise<void> {
  return apiFetch(`/api/pets/${petId}`, { method: "DELETE", token });
}
