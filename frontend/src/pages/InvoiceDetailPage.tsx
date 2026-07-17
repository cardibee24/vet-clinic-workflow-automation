import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { useToken } from "../auth/AuthContext";
import {
  addLineItem,
  getInvoice,
  updateInvoiceStatus,
  type InvoiceStatus,
  type InvoiceWithLineItems,
} from "../api/invoices";
import { formatMoney } from "../lib/format";

const ALLOWED_TRANSITIONS: Record<InvoiceStatus, InvoiceStatus[]> = {
  draft: ["issued", "void"],
  issued: ["paid", "void"],
  paid: [],
  void: [],
};

const STATUS_LABELS: Record<InvoiceStatus, string> = {
  draft: "Draft",
  issued: "Issued",
  paid: "Paid",
  void: "Void",
};

export function InvoiceDetailPage() {
  const token = useToken();
  const { invoiceId } = useParams<{ invoiceId: string }>();

  const [invoice, setInvoice] = useState<InvoiceWithLineItems | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const [description, setDescription] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [unitPrice, setUnitPrice] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  function refresh() {
    if (!invoiceId) return;
    setLoading(true);
    getInvoice(token, invoiceId)
      .then((data) => {
        setInvoice(data);
        setLoadError(null);
      })
      .catch((err: unknown) => setLoadError(err instanceof Error ? err.message : "Failed to load invoice"))
      .finally(() => setLoading(false));
  }

  useEffect(refresh, [token, invoiceId]);

  async function handleAddLineItem(event: FormEvent) {
    event.preventDefault();
    if (!invoiceId) return;
    setSubmitting(true);
    setFormError(null);
    try {
      const unitPriceCents = Math.round(parseFloat(unitPrice) * 100);
      await addLineItem(token, invoiceId, {
        description,
        quantity: Number(quantity),
        unit_price_cents: unitPriceCents,
      });
      setDescription("");
      setQuantity("1");
      setUnitPrice("");
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to add line item");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTransition(status: InvoiceStatus) {
    if (!invoiceId) return;
    setActionError(null);
    try {
      await updateInvoiceStatus(token, invoiceId, status);
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to update invoice");
    }
  }

  if (loading) return <p>Loading invoice...</p>;
  if (loadError) return <p className="error-text">{loadError}</p>;
  if (!invoice) return null;

  const isDraft = invoice.status === "draft";

  return (
    <section>
      <p>
        <Link to="/invoices">&larr; Back to invoices</Link>
      </p>
      <h2>Invoice</h2>
      <p>
        <span className="status-pill">{STATUS_LABELS[invoice.status]}</span>
        {invoice.due_date && <span className="muted"> &middot; due {invoice.due_date}</span>}
      </p>
      {invoice.notes && <p className="muted">{invoice.notes}</p>}

      <table>
        <thead>
          <tr>
            <th>Description</th>
            <th>Qty</th>
            <th>Unit price</th>
            <th>Amount</th>
          </tr>
        </thead>
        <tbody>
          {invoice.line_items.map((item) => (
            <tr key={item.id}>
              <td>{item.description}</td>
              <td>{item.quantity}</td>
              <td>{formatMoney(item.unit_price_cents)}</td>
              <td>{formatMoney(item.amount_cents)}</td>
            </tr>
          ))}
          {invoice.line_items.length === 0 && (
            <tr>
              <td colSpan={4} className="muted">
                No line items yet.
              </td>
            </tr>
          )}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={3}>
              <strong>Total</strong>
            </td>
            <td>
              <strong>{formatMoney(invoice.total_cents)}</strong>
            </td>
          </tr>
        </tfoot>
      </table>

      {isDraft && (
        <form className="card" onSubmit={handleAddLineItem} style={{ marginTop: 24 }}>
          <h3>Add line item</h3>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="description">Description</label>
              <input
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="quantity">Quantity</label>
              <input
                id="quantity"
                type="number"
                min={1}
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="unit_price">Unit price ($)</label>
              <input
                id="unit_price"
                type="number"
                min={0}
                step="0.01"
                value={unitPrice}
                onChange={(e) => setUnitPrice(e.target.value)}
                required
              />
            </div>
            <button type="submit" disabled={submitting}>
              {submitting ? "Adding..." : "Add line item"}
            </button>
          </div>
          {formError && <p className="error-text">{formError}</p>}
        </form>
      )}

      <div className="actions" style={{ marginTop: 24 }}>
        {ALLOWED_TRANSITIONS[invoice.status].map((next) => (
          <button key={next} type="button" onClick={() => handleTransition(next)}>
            Mark as {STATUS_LABELS[next]}
          </button>
        ))}
      </div>
      {actionError && <p className="error-text">{actionError}</p>}
    </section>
  );
}
