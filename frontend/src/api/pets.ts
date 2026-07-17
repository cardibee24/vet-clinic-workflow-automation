import { apiFetch } from "./client";
import type { Pet } from "./owners";

export function listPets(token: string): Promise<Pet[]> {
  return apiFetch("/api/pets", { token });
}
