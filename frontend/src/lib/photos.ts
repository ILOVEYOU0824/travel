const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

/** Places Photos (New) — 백엔드 프록시 URL. name은 API 원본 photos[].name */
export function placePhotoUrl(photoName: string, maxWidthPx = 800): string {
  const params = new URLSearchParams({
    name: photoName,
    max_width_px: String(maxWidthPx),
  })
  return `${API_BASE}/api/v1/places/photo?${params.toString()}`
}
