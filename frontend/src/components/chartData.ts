export type TrendDatum = {
  label: string;
  shortLabel?: string;
  values: Record<string, number>;
  timestamp?: number;
  endTimestamp?: number;
};

export function chartDate(date: string): number | undefined {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return undefined;
  const timestamp = Date.parse(`${date}T00:00:00Z`);
  return Number.isFinite(timestamp) &&
    new Date(timestamp).toISOString().slice(0, 10) === date
    ? timestamp
    : undefined;
}

export function safeChartNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) && value > 0
    ? value
    : 0;
}

export function chartMaximum(values: number[]): number {
  const maximum = Math.max(0, ...values.map(safeChartNumber));
  if (!maximum) return 4;
  const scale = 10 ** Math.floor(Math.log10(maximum));
  return Math.ceil(maximum / scale / 4) * scale * 4;
}

// Consecutive buckets keep the source order and preserve every series total.
export function aggregateTrend(data: TrendDatum[], limit = 30): TrendDatum[] {
  const size = Math.max(1, Math.ceil(data.length / Math.max(1, limit)));
  const buckets: TrendDatum[] = [];
  for (let offset = 0; offset < data.length; offset += size) {
    const slice = data.slice(offset, offset + size);
    const first = slice[0],
      last = slice[slice.length - 1];
    const values: Record<string, number> = {};
    for (const point of slice)
      for (const [key, value] of Object.entries(point.values))
        values[key] = (values[key] || 0) + safeChartNumber(value);
    buckets.push({
      label:
        slice.length === 1 ? first.label : `${first.label} — ${last.label}`,
      shortLabel:
        slice.length === 1 ? first.shortLabel : first.shortLabel || first.label,
      timestamp: first.timestamp ?? chartDate(first.label),
      endTimestamp:
        last.endTimestamp ?? last.timestamp ?? chartDate(last.label),
      values,
    });
  }
  return buckets;
}

// Preserve calendar gaps without treating dates absent from the API as zero.
export function trendTimeDomain(
  points: TrendDatum[],
): { start: number; end: number } | undefined {
  if (
    !points.length ||
    points.some(
      (point) =>
        !Number.isFinite(point.timestamp) ||
        !Number.isFinite(point.endTimestamp),
    )
  )
    return undefined;
  for (let index = 1; index < points.length; index++) {
    if (points[index].timestamp! <= points[index - 1].endTimestamp!)
      return undefined;
  }
  const halfDay = 43_200_000;
  return {
    start: points[0].timestamp! - halfDay,
    end: points[points.length - 1].endTimestamp! + halfDay,
  };
}
