import { apiFetch } from "./client";

export interface AskResponse {
  answer: string;
  sources: string[];
}

export function askKnowledge(token: string, question: string): Promise<AskResponse> {
  return apiFetch("/api/knowledge/ask", { method: "POST", token, body: { question } });
}
