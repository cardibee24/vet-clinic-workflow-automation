import { apiFetch } from "./client";

export interface Pet {
  id: string;
  owner_id: string;
  name: string;
  species: string;
  breed: string | null;
  date_of_birth: string | null;
}

export interface PetCreateInput {
  name: string;
  species: string;
  breed?: string;
  date_of_birth?: string;
}

export interface Owner {
  id: string;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
}

export interface OwnerWithPets extends Owner {
  pets: Pet[];
}

export interface OwnerCreateInput {
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
}

export interface OwnerUpdateInput {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
}

export function listOwners(token: string): Promise<Owner[]> {
  return apiFetch("/api/owners", { token });
}

export function createOwner(token: string, body: OwnerCreateInput): Promise<Owner> {
  return apiFetch("/api/owners", { method: "POST", token, body });
}

export function getOwner(token: string, ownerId: string): Promise<OwnerWithPets> {
  return apiFetch(`/api/owners/${ownerId}`, { token });
}

export function addPet(token: string, ownerId: string, body: PetCreateInput): Promise<Pet> {
  return apiFetch(`/api/owners/${ownerId}/pets`, { method: "POST", token, body });
}

export function updateOwner(token: string, ownerId: string, body: OwnerUpdateInput): Promise<Owner> {
  return apiFetch(`/api/owners/${ownerId}`, { method: "PATCH", token, body });
}

export function deleteOwner(token: string, ownerId: string): Promise<void> {
  return apiFetch(`/api/owners/${ownerId}`, { method: "DELETE", token });
}
