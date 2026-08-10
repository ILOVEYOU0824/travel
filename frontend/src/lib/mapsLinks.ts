/** Places API googleMapsUri 또는 place_id로 Google 지도(리뷰 포함) 링크. */

export function placeMapsUrl(place: {
  place_id: string
  google_maps_uri?: string | null
  name?: string
}): string | null {
  if (place.google_maps_uri) return place.google_maps_uri
  if (!place.place_id) return null
  const q = encodeURIComponent(place.name || 'place')
  return `https://www.google.com/maps/search/?api=1&query=${q}&query_place_id=${encodeURIComponent(place.place_id)}`
}
