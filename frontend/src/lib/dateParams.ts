const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

export function normalizeDateParam(value: string | null | undefined): string {
  const trimmed = value?.trim() ?? "";
  if (!ISO_DATE_PATTERN.test(trimmed) || trimmed.startsWith("0")) {
    return "";
  }

  const parsed = new Date(`${trimmed}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }

  return parsed.toISOString().slice(0, 10) === trimmed ? trimmed : "";
}
