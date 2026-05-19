export function formatDate(value?: string | null) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not available";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(date);
}

export function formatRelative(value?: string | null) {
  if (!value) return "Recently";
  const date = new Date(value);
  const diff = Date.now() - date.getTime();
  if (Number.isNaN(diff)) return "Recently";
  const minutes = Math.round(diff / 60000);
  if (minutes < 2) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function percent(value?: number | null) {
  if (value == null || Number.isNaN(value)) return "0%";
  const normalized = value <= 1 ? value * 100 : value;
  return `${Math.round(normalized)}%`;
}

export function scoreValue(value?: number | null) {
  if (value == null || Number.isNaN(value)) return 0;
  return Math.round(value <= 1 ? value * 100 : value);
}
