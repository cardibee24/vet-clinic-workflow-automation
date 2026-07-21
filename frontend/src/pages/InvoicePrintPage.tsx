import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useToken } from "../auth/AuthContext";
import { getInvoice, PAYMENT_METHOD_LABELS, type InvoiceWithLineItems } from "../api/invoices";
import { listOwners, type Owner } from "../api/owners";
import { formatMoney } from "../lib/format";

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  issued: "Issued",
  paid: "Paid",
  void: "Void",
};

export function InvoicePrintPage() {
  const token = useToken();
  const { invoiceId } = useParams<{ invoiceId: string }>();

  const [invoice, setInvoice] = useState<InvoiceWithLineItems | null>(null);
  const [owner, setOwner] = useState<Owner | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!invoiceId) return;
    setLoading(true);
    Promise.all([getInvoice(token, invoiceId), listOwners(token)])
      .then(([invoiceData, owners]) => {
        setInvoice(invoiceData);
        setOwner(owners.find((o) => o.id === invoiceData.owner_id) ?? null);
        setLoadError(null);
      })
      .catch((err: unknown) => setLoadError(err instanceof Error ? err.message : "Failed to load invoice"))
      .finally(() => setLoading(false));
  }, [token, invoiceId]);

  if (loading) return <p style={{ padding: 24 }}>Loading...</p>;
  if (loadError) return <p className="error-text" style={{ padding: 24 }}>{loadError}</p>;
  if (!invoice) return null;

  return (
    <div className="print-page">
      <div className="actions no-print" style={{ padding: 24, paddingBottom: 0 }}>
        <Link to={`/invoices/${invoice.id}`} className="back-link" style={{ marginBottom: 0 }}>
          &larr; Back to invoice
        </Link>
        <button type="button" onClick={() => window.print()}>
          Print / Save as PDF
        </button>
      </div>

      <div className="print-sheet">
        <div className="print-header">
          <div className="brand">
            VetFlow
          </div>
          <div className="print-invoice-meta">
            <div>
              <strong>Invoice</strong>
            </div>
            <div className="muted">#{invoice.id.slice(0, 8).toUpperCase()}</div>
          </div>
        </div>

        <div className="print-grid">
          <div>
            <div className="print-label">Bill to</div>
            <div>{owner ? `${owner.first_name} ${owner.last_name}` : "Unknown owner"}</div>
            {owner?.email && <div className="muted">{owner.email}</div>}
            {owner?.phone && <div className="muted">{owner.phone}</div>}
          </div>
          <div>
            <div className="print-label">Status</div>
            <div>{STATUS_LABELS[invoice.status] ?? invoice.status}</div>
            {invoice.issued_at && (
              <div className="muted">Issued {new Date(invoice.issued_at).toLocaleDateString()}</div>
            )}
            {invoice.due_date && <div className="muted">Due {invoice.due_date}</div>}
            {invoice.paid_at && invoice.payment_method && (
              <div className="muted">
                Paid {new Date(invoice.paid_at).toLocaleDateString()} via{" "}
                {PAYMENT_METHOD_LABELS[invoice.payment_method]}
              </div>
            )}
          </div>
        </div>

        {invoice.notes && <p style={{ marginTop: 20 }}>{invoice.notes}</p>}

        <table style={{ marginTop: 24 }}>
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
                  No line items.
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

        <p className="muted" style={{ marginTop: 32 }}>
          Thank you for trusting us with your pet's care.
        </p>
      </div>
    </div>
  );
}
