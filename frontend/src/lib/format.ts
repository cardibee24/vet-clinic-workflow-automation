export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

export function formatMoney(cents: number): string {
  return (cents / 100).toLocaleString(undefined, { style: "currency", currency: "USD" });
}

const STATUS_PILL_CLASSES: Record<string, string> = {
  checked_in: "status-info",
  issued: "status-info",
  in_progress: "status-warning",
  completed: "status-success",
  paid: "status-success",
  cancelled: "status-danger",
  no_show: "status-danger",
  void: "status-danger",
};

export function statusPillClass(status: string): string {
  return STATUS_PILL_CLASSES[status] ?? "";
}

export function isToday(iso: string): boolean {
  const date = new Date(iso);
  const now = new Date();
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  );
}
