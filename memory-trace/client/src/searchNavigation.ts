export function stepSearchCursor(current: number, total: number, step: number): number {
  if (total <= 0) return -1;
  const start = current >= 0 && current < total ? current : step > 0 ? -1 : 0;
  return (start + step + total) % total;
}

export function searchResultCursor<T>(results: readonly T[], selected: T): number {
  return results.indexOf(selected);
}
