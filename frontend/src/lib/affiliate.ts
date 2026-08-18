/** Travelpayouts(tp.media) 경유는 Klook WAF가 봇 유입으로 막는 경우가 많다. */

const BOOKING_HOSTS = ['.klook.com', '.kkday.com'] as const

function isBookingHost(hostname: string): boolean {
  const h = hostname.toLowerCase()
  return BOOKING_HOSTS.some((suffix) => h === suffix.slice(1) || h.endsWith(suffix))
}

export function bookingLandingUrl(raw: string): string {
  try {
    const u = new URL(raw)
    const destRaw = u.searchParams.get('u')
    if (
      destRaw &&
      (u.hostname === 'tp.media' || u.hostname.endsWith('.tp.media') || u.hostname.endsWith('.tpk.lu'))
    ) {
      const dest = new URL(destRaw)
      if (isBookingHost(dest.hostname)) return dest.toString()
    }
  } catch {
    /* keep original */
  }
  return raw
}
