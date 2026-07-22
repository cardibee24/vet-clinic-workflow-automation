import { apiFetch } from "./client";

export interface AssistantResult {
  intent: string;
  reply: string;
}

export function askAssistant(token: string, message: string): Promise<AssistantResult> {
  return apiFetch("/api/assistant", { method: "POST", token, body: { message } });
}
