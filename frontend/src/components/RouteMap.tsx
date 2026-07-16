import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useEffect, useRef } from 'react'
import type { RoutePoint } from '../lib/types'

/**
 * GPS polyline over CARTO dark tiles (external tile fetch — the one
 * network dependency this self-hosted app has, flagged in the brief).
 */
export function RouteMap({ points }: { points: RoutePoint[] }) {
  const elRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)

  useEffect(() => {
    const el = elRef.current
    if (!el || points.length < 2 || mapRef.current) return

    // Cap polyline size — routes can be thousands of points.
    const step = Math.max(1, Math.floor(points.length / 600))
    const coords = points
      .filter((_, i) => i % step === 0 || i === points.length - 1)
      .map((p) => [p.latitude, p.longitude] as [number, number])

    const map = L.map(el, { zoomControl: false, attributionControl: true, scrollWheelZoom: false })
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      subdomains: 'abcd',
      attribution: '&copy; OpenStreetMap &copy; CARTO',
    }).addTo(map)

    const accent =
      getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#FF6A3D'
    const line = L.polyline(coords, { color: accent, weight: 4, opacity: 0.95 }).addTo(map)
    map.fitBounds(line.getBounds().pad(0.18))
    L.circleMarker(coords[0], {
      radius: 6,
      color: '#0F0D08',
      fillColor: '#5FB98A',
      fillOpacity: 1,
      weight: 2,
    }).addTo(map)
    L.circleMarker(coords[coords.length - 1], {
      radius: 6,
      color: '#0F0D08',
      fillColor: accent,
      fillOpacity: 1,
      weight: 2,
    }).addTo(map)

    mapRef.current = map
    const t = setTimeout(() => map.invalidateSize(), 80)

    return () => {
      clearTimeout(t)
      map.remove()
      mapRef.current = null
    }
  }, [points])

  return <div ref={elRef} className="route-map" />
}
