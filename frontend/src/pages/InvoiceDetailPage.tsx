import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useToken } from "../auth/AuthContext";
import {
  addLineItem,
  deleteInvoice,
  deleteLineItem,
  getInvoice,
  updateInvoiceStatus,
  updateLineItem,
  PAYMENT_METHOD_LABELS,
  type InvoiceStatus,
  type InvoiceWithLineItems,
  type PaymentMethod,
} from "../api/invoices";
import { formatMoney, statusPillClass } from "../lib/format";

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
  const navigate = useNavigate();

  const [invoice, setInvoice] = useState<InvoiceWithLineItems | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const [description, setDescription] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [unitPrice, setUnitPrice] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod | "">("");

  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [editDescription, setEditDescription] = useState("");
  const [editQuantity, setEditQuantity] = useState("1");
  const [editUnitPrice, setEditUnitPrice] = useState("");
  const [savingItem, setSavingItem] = useState(false);
  const [deletingItemId, setDeletingItemId] = useState<string | null>(null);

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

  function startItemEdit(itemId: string, currentDescription: string, currentQuantity: number, currentUnitPriceCents: number) {
    setActionError(null);
    setEditingItemId(itemId);
    setEditDescription(currentDescription);
    setEditQuantity(String(currentQuantity));
    setEditUnitPrice((currentUnitPriceCents / 100).toFixed(2));
  }

  function cancelItemEdit() {
    setEditingItemId(null);
  }

  async function saveItemEdit(itemId: string) {
    if (!invoiceId) return;
    setSavingItem(true);
    setActionError(null);
    try {
      await updateLineItem(token, invoiceId, itemId, {
        description: editDescription,
        quantity: Number(editQuantity),
        unit_price_cents: Math.round(parseFloat(editUnitPrice) * 100),
      });
      cancelItemEdit();
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to update line item");
    } finally {
      setSavingItem(false);
    }
  }

  async function handleDeleteItem(itemId: string) {
    if (!invoiceId) return;
    if (!window.confirm("Delete this line item?")) {
      return;
    }
    setDeletingItemId(itemId);
    setActionError(null);
    try {
      await deleteLineItem(token, invoiceId, itemId);
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to delete line item");
    } finally {
      setDeletingItemId(null);
    }
  }

  async function handleTransition(status: InvoiceStatus, method?: PaymentMethod) {
    if (!invoiceId) return;
    setActionError(null);
    try {
      await updateInvoiceStatus(token, invoiceId, status, method);
      setPaymentMethod("");
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to update invoice");
    }
  }

  async function handleDelete() {
    if (!invoiceId) return;
    if (!window.confirm("Delete this draft invoice? This cannot be undone.")) {
      return;
    }
    setDeleting(true);
    setActionError(null);
    try {
      await deleteInvoice(token, invoiceId);
      navigate("/invoices");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to delete invoice");
      setDeleting(false);
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
        <span className={`status-pill ${statusPillClass(invoice.status)}`}>{STATUS_LABELS[invoice.status]}</span>
        {invoice.due_date && <span className="muted"> &middot; due {invoice.due_date}</span>}
        {invoice.payment_method && (
          <span className="muted"> &middot; paid via {PAYMENT_METHOD_LABELS[invoice.payment_method]}</span>
        )}
      </p>
      {invoice.notes && <p className="muted">{invoice.notes}</p>}

      <table>
        <thead>
          <tr>
            <th>Description</th>
            <th>Qty</th>
            <th>Unit price</th>
            <th>Amount</th>
            {isDraft && <th></th>}
          </tr>
        </thead>
        <tbody>
          {invoice.line_items.map((item) =>
            editingItemId === item.id ? (
              <tr key={item.id}>
                <td>
                  <input value={editDescription} onChange={(e) => setEditDescription(e.target.value)} />
                </td>
                <td>
                  <input
                    type="number"
                    min={1}
                    value={editQuantity}
                    onChange={(e) => setEditQuantity(e.target.value)}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    value={editUnitPrice}
                    onChange={(e) => setEditUnitPrice(e.target.value)}
                  />
                </td>
                <td>{formatMoney(Math.round(parseFloat(editUnitPrice || "0") * 100) * Number(editQuantity || 0))}</td>
                <td>
                  <div className="actions">
                    <button type="button" disabled={savingItem} onClick={() => saveItemEdit(item.id)}>
                      {savingItem ? "Saving..." : "Save"}
                    </button>
                    <button type="button" className="secondary" onClick={cancelItemEdit}>
                      Cancel
                    </button>
                  </div>
                </td>
              </tr>
            ) : (
              <tr key={item.id}>
                <td>{item.description}</td>
                <td>{item.quantity}</td>
                <td>{formatMoney(item.unit_price_cents)}</td>
                <td>{formatMoney(item.amount_cents)}</td>
                {isDraft && (
                  <td>
                    <div className="actions">
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => startItemEdit(item.id, item.description, item.quantity, item.unit_price_cents)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className="secondary"
                        disabled={deletingItemId === item.id}
                        onClick={() => handleDeleteItem(item.id)}
                      >
                        {deletingItemId === item.id ? "Deleting..." : "Delete"}
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ),
          )}
          {invoice.line_items.length === 0 && (
            <tr>
              <td colSpan={isDraft ? 5 : 4} className="muted">
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
            {isDraft && <td></td>}
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
        {ALLOWED_TRANSITIONS[invoice.status].map((next) =>
          next === "paid" ? (
            <div className="actions" key={next}>
              <select
                aria-label="Payment method"
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod | "")}
              >
                <option value="">Select payment method</option>
                {Object.entries(PAYMENT_METHOD_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <button
                type="button"
                disabled={!paymentMethod}
                onClick={() => handleTransition(next, paymentMethod as PaymentMethod)}
              >
                Mark as Paid
              </button>
            </div>
          ) : (
            <button key={next} type="button" onClick={() => handleTransition(next)}>
              Mark as {STATUS_LABELS[next]}
            </button>
          ),
        )}
        {isDraft && (
          <button type="button" className="secondary" disabled={deleting} onClick={handleDelete}>
            {deleting ? "Deleting..." : "Delete invoice"}
          </button>
        )}
      </div>
      {actionError && <p className="error-text">{actionError}</p>}
    </section>
  );
}
