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
  pet_id: string;
  assigned_user_id: string | null;
  scheduled_at: string;
  status: AppointmentStatus;
  reason: string | null;
  checked_in_at: string | null;
}

export interface QueueEntry {
  position: number;
  appointment_id: string;
  pet_id: string;
  checked_in_at: string | null;
  reason: string | null;
}

export interface QueueSummary {
  total_waiting: number;
  entries: QueueEntry[];
}

export interface AppointmentQueueStatus {
  appointment_id: string;
  status: AppointmentStatus;
  position: number | null;
  total_waiting: number;
}

export interface AppointmentCreateInput {
  pet_id: string;
  assigned_user_id?: string;
  scheduled_at: string;
  reason?: string;
}

export interface AppointmentUpdateInput {
  scheduled_at?: string;
  reason?: string;
  assigned_user_id?: string;
}

export function listAppointments(token: string): Promise<Appointment[]> {
  return apiFetch("/api/appointments", { token });
}

export function createAppointment(token: string, body: AppointmentCreateInput): Promise<Appointment> {
  return apiFetch("/api/appointments", { method: "POST", token, body });
}

export function updateAppointment(
  token: string,
  appointmentId: string,
  body: AppointmentUpdateInput,
): Promise<Appointment> {
  return apiFetch(`/api/appointments/${appointmentId}`, { method: "PATCH", token, body });
}

export function updateAppointmentStatus(
  token: string,
  appointmentId: string,
  status: AppointmentStatus,
): Promise<Appointment> {
  return apiFetch(`/api/appointments/${appointmentId}/status`, { method: "PATCH", token, body: { status } });
}

export function deleteAppointment(token: string, appointmentId: string): Promise<void> {
  return apiFetch(`/api/appointments/${appointmentId}`, { method: "DELETE", token });
}

export function getQueue(token: string): Promise<QueueSummary> {
  return apiFetch("/api/appointments/queue", { token });
}

/** Public: no auth required, used by clients checking their own queue position. */
export function getAppointmentQueueStatus(appointmentId: string): Promise<AppointmentQueueStatus> {
  return apiFetch(`/api/appointments/${appointmentId}/queue`);
}
