export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

export function formatMoney(cents: number): string {
  return (cents / 100).toLocaleString(undefined, { style: "currency", currency: "USD" });
}
