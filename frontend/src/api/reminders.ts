import { apiFetch } from "./client";

export type ReminderChannel = "email" | "sms";
export type ReminderStatus = "pending" | "sent" | "failed" | "cancelled";

export interface Reminder {
  id: string;
  clinic_id: string;
  appointment_id: string;
  channel: ReminderChannel;
  send_at: string;
  status: ReminderStatus;
  sent_at: string | null;
}

export interface ReminderCreateInput {
  appointment_id: string;
  channel: ReminderChannel;
  send_at: string;
}

export function listReminders(token: string): Promise<Reminder[]> {
  return apiFetch("/api/reminders", { token });
}

export function createReminder(token: string, body: ReminderCreateInput): Promise<Reminder> {
  return apiFetch("/api/reminders", { method: "POST", token, body });
}

export function updateReminderStatus(
  token: string,
  reminderId: string,
  status: ReminderStatus,
): Promise<Reminder> {
  return apiFetch(`/api/reminders/${reminderId}/status`, { method: "PATCH", token, body: { status } });
}
