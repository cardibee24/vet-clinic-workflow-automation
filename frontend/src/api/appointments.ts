import { apiFetch } from "./client";

export type AppointmentStatus =
  | "scheduled"
  | "checked_in"
  | "in_progress"
  | "completed"
  | "cancelled"
  | "no_show";

export type AppointmentReason =
  | "checkup"
  | "vaccination"
  | "surgery"
  | "dental"
  | "follow_up"
  | "emergency"
  | "diagnostic";

export const APPOINTMENT_REASON_LABELS: Record<AppointmentReason, string> = {
  checkup: "Checkup",
  vaccination: "Vaccination",
  surgery: "Surgery",
  dental: "Dental",
  follow_up: "Follow-up",
  emergency: "Emergency",
  diagnostic: "Diagnostic",
};

export interface Appointment {
  id: string;
  pet_id: string;
  assigned_user_id: string | null;
  scheduled_at: string;
  status: AppointmentStatus;
  reason: AppointmentReason | null;
  checked_in_at: string | null;
  ticket_number: number | null;
  visit_notes: string | null;
  prescription: string | null;
}

export interface QueueEntry {
  position: number;
  appointment_id: string;
  pet_id: string;
  checked_in_at: string | null;
  ticket_number: number | null;
  reason: AppointmentReason | null;
}

export interface QueueSummary {
  total_waiting: number;
  entries: QueueEntry[];
}

export interface AppointmentQueueStatus {
  appointment_id: string;
  status: AppointmentStatus;
  ticket_number: number | null;
  position: number | null;
  total_waiting: number;
}

/** Formats a ticket number for display, e.g. 42 -> "Q-042". */
export function formatTicketNumber(ticketNumber: number): string {
  return `Q-${String(ticketNumber).padStart(3, "0")}`;
}

export interface AppointmentCreateInput {
  pet_id: string;
  assigned_user_id?: string;
  scheduled_at: string;
  reason?: AppointmentReason;
}

export interface AppointmentUpdateInput {
  scheduled_at?: string;
  reason?: AppointmentReason;
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

export function updateAppointmentNotes(
  token: string,
  appointmentId: string,
  visitNotes: string,
  prescription: string,
): Promise<Appointment> {
  return apiFetch(`/api/appointments/${appointmentId}/notes`, {
    method: "PATCH",
    token,
    body: { visit_notes: visitNotes || null, prescription: prescription || null },
  });
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

/** Public: no auth required, lets a client look up their status with today's short ticket number. */
export function getQueueStatusByTicket(ticketNumber: number): Promise<AppointmentQueueStatus> {
  return apiFetch(`/api/appointments/ticket/${ticketNumber}`);
}

export interface SelfCheckInInput {
  pet_id: string;
  reason?: AppointmentReason;
}

/** Public: no auth required, used by clients checking themselves in for a walk-in. */
export function selfCheckIn(body: SelfCheckInInput): Promise<Appointment> {
  return apiFetch("/api/appointments/self-check-in", { method: "POST", body });
}
