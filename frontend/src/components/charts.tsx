/**
 * Hand-rolled SVG charts matching the design's chart language:
 * thin grid lines, rounded line paths, soft area fills, rounded bars.
 * All charts use viewBox + preserveAspectRatio="none" and scale to width.
 */

export interface Pt {
  x: number
  y: number
}

/** Map values into an SVG path across a fixed viewbox. */
export function linePath(
  values: (number | null)[],
  opts: { w: number; h: number; min?: number; max?: number; pad?: number; connectGaps?: boolean },
): { path: string; min: number; max: number } {
  const present = values.filter((v): v is number => v != null && Number.isFinite(v))
  if (present.length === 0) return { path: '', min: 0, max: 1 }
  const pad = opts.pad ?? 0.08
  let min = opts.min ?? Math.min(...present)
  let max = opts.max ?? Math.max(...present)
  if (min === max) {
    min -= 1
    max += 1
  }
  const range = max - min
  min -= range * pad
  max += range * pad

  const dx = values.length > 1 ? opts.w / (values.length - 1) : 0
  let path = ''
  let pen = false
  values.forEach((v, i) => {
    if (v == null || !Number.isFinite(v)) {
      // Sparse metrics are the norm (weight logged occasionally); by default
      // bridge gaps so the trend stays a line instead of orphaned points.
      if (!opts.connectGaps) pen = false
      return
    }
    const x = (i * dx).toFixed(1)
    const y = (opts.h - ((v - min) / (max - min)) * opts.h).toFixed(1)
    path += `${pen ? 'L' : 'M'}${x} ${y}`
    pen = true
  })
  return { path, min, max }
}

export function areaFromLine(path: string, w: number, h: number): string {
  if (!path) return ''
  return `${path} L${w} ${h} L0 ${h} Z`
}

export function GridLines({ w, h, rows = 3 }: { w: number; h: number; rows?: number }) {
  const ys = Array.from({ length: rows }, (_, i) => ((i + 1) * h) / (rows + 1))
  return (
    <path
      d={ys.map((y) => `M0 ${y.toFixed(1)} H${w}`).join(' ')}
      stroke="var(--grid-line)"
      strokeWidth="1"
      fill="none"
    />
  )
}

/** Downsample an array to at most n points (mean of each bucket). */
export function downsample(values: number[], n: number): number[] {
  if (values.length <= n) return values
  const out: number[] = []
  const step = values.length / n
  for (let i = 0; i < n; i++) {
    const start = Math.floor(i * step)
    const end = Math.max(start + 1, Math.floor((i + 1) * step))
    const bucket = values.slice(start, end)
    out.push(bucket.reduce((a, b) => a + b, 0) / bucket.length)
  }
  return out
}

/** HR zone bands (default bpm boundaries; drawn only where they intersect the y-domain). */
export const HR_ZONES: { name: string; from: number; to: number; color: string }[] = [
  { name: 'Z1', from: 0, to: 120, color: 'rgba(94,124,142,0.10)' },
  { name: 'Z2', from: 120, to: 140, color: 'rgba(95,168,138,0.11)' },
  { name: 'Z3', from: 140, to: 155, color: 'rgba(217,169,62,0.10)' },
  { name: 'Z4', from: 155, to: 170, color: 'rgba(238,123,60,0.10)' },
  { name: 'Z5', from: 170, to: 240, color: 'rgba(220,74,59,0.10)' },
]

export const HR_ZONE_LEGEND: { name: string; color: string }[] = [
  { name: 'Z1', color: '#5E7C8E' },
  { name: 'Z2', color: '#5FA88A' },
  { name: 'Z3', color: '#D9A93E' },
  { name: 'Z4', color: '#EE7B3C' },
  { name: 'Z5', color: '#DC4A3B' },
]

export function zoneBands(min: number, max: number, w: number, h: number) {
  return HR_ZONES.flatMap((z) => {
    const lo = Math.max(z.from, min)
    const hi = Math.min(z.to, max)
    if (hi <= lo) return []
    const y = h - ((hi - min) / (max - min)) * h
    const bandH = ((hi - lo) / (max - min)) * h
    return [{ key: z.name, y, h: bandH, color: z.color, w }]
  })
}
