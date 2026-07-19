import { apiFetch } from "./client";

export type InvoiceStatus = "draft" | "issued" | "paid" | "void";

export type PaymentMethod = "cash" | "card" | "bank_transfer" | "other";

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  cash: "Cash",
  card: "Card",
  bank_transfer: "Bank transfer",
  other: "Other",
};

export interface LineItem {
  id: string;
  invoice_id: string;
  description: string;
  quantity: number;
  unit_price_cents: number;
  amount_cents: number;
}

export interface LineItemCreateInput {
  description: string;
  quantity?: number;
  unit_price_cents: number;
}

export interface LineItemUpdateInput {
  description?: string;
  quantity?: number;
  unit_price_cents?: number;
}

export interface Invoice {
  id: string;
  owner_id: string;
  appointment_id: string | null;
  status: InvoiceStatus;
  issued_at: string | null;
  due_date: string | null;
  notes: string | null;
  paid_at: string | null;
  payment_method: PaymentMethod | null;
}

export interface InvoiceWithLineItems extends Invoice {
  line_items: LineItem[];
  total_cents: number;
}

export interface InvoiceCreateInput {
  owner_id: string;
  appointment_id?: string;
  due_date?: string;
  notes?: string;
}

export function listInvoices(token: string): Promise<Invoice[]> {
  return apiFetch("/api/invoices", { token });
}

export function createInvoice(token: string, body: InvoiceCreateInput): Promise<Invoice> {
  return apiFetch("/api/invoices", { method: "POST", token, body });
}

export function getInvoice(token: string, invoiceId: string): Promise<InvoiceWithLineItems> {
  return apiFetch(`/api/invoices/${invoiceId}`, { token });
}

export function addLineItem(token: string, invoiceId: string, body: LineItemCreateInput): Promise<LineItem> {
  return apiFetch(`/api/invoices/${invoiceId}/line-items`, { method: "POST", token, body });
}

export function updateLineItem(
  token: string,
  invoiceId: string,
  lineItemId: string,
  body: LineItemUpdateInput,
): Promise<LineItem> {
  return apiFetch(`/api/invoices/${invoiceId}/line-items/${lineItemId}`, { method: "PATCH", token, body });
}

export function deleteLineItem(token: string, invoiceId: string, lineItemId: string): Promise<void> {
  return apiFetch(`/api/invoices/${invoiceId}/line-items/${lineItemId}`, { method: "DELETE", token });
}

export function updateInvoiceStatus(
  token: string,
  invoiceId: string,
  status: InvoiceStatus,
  paymentMethod?: PaymentMethod,
): Promise<Invoice> {
  return apiFetch(`/api/invoices/${invoiceId}/status`, {
    method: "PATCH",
    token,
    body: { status, payment_method: paymentMethod },
  });
}

export function deleteInvoice(token: string, invoiceId: string): Promise<void> {
  return apiFetch(`/api/invoices/${invoiceId}`, { method: "DELETE", token });
}
