import { useEffect, useState } from 'react'
import { fetchAffiliateStatus } from '../api/itinerary'

export function AffiliateBadge() {
  const [mode, setMode] = useState<string | null>(null)
  const [kkday, setKkday] = useState(false)

  useEffect(() => {
    void fetchAffiliateStatus()
      .then((s) => {
        setMode(s.mode)
        setKkday(Boolean(s.has_kkday_link))
      })
      .catch(() => setMode(null))
  }, [])

  if (mode == null) return null

  return (
    <p className="text-[10px] text-mist/40">
      제휴 {kkday ? 'KKday·' : ''}Klook 연결
    </p>
  )
}
