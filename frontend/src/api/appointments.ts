import { apiFetch } from "./client";

export type AppointmentStatus =
  | "scheduled"
  | "checked_in"
  | "in_progress"
  | "completed"
  | "cancelled"
  | "no_show";

export interface Appointment {
  id: string;
  clinic_id: string;
  pet_id: string;
  assigned_user_id: string | null;
  scheduled_start: string;
  scheduled_end: string;
  status: AppointmentStatus;
  reason: string | null;
}

export interface AppointmentCreateInput {
  pet_id: string;
  assigned_user_id?: string;
  scheduled_start: string;
  scheduled_end: string;
  reason?: string;
}

export function listAppointments(token: string): Promise<Appointment[]> {
  return apiFetch("/api/appointments", { token });
}

export function createAppointment(token: string, body: AppointmentCreateInput): Promise<Appointment> {
  return apiFetch("/api/appointments", { method: "POST", token, body });
}

export function updateAppointmentStatus(
  token: string,
  appointmentId: string,
  status: AppointmentStatus,
): Promise<Appointment> {
  return apiFetch(`/api/appointments/${appointmentId}/status`, { method: "PATCH", token, body: { status } });
}
