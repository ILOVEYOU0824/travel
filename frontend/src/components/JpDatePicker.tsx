import { useEffect, useId, useMemo, useRef, useState } from 'react'

const WEEK = ['日', '月', '火', '水', '木', '金', '土'] as const

function parseIso(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, (m || 1) - 1, d || 1)
}

function toIso(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function sameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

function formatDisplay(iso: string): string {
  if (!iso) return '날짜 선택'
  const d = parseIso(iso)
  const w = WEEK[d.getDay()]
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}（${w}）`
}

export function JpDatePicker({
  label,
  value,
  onChange,
  min,
  max,
  hint,
}: {
  label: string
  value: string
  onChange: (iso: string) => void
  min?: string
  max?: string
  hint?: string
}) {
  const id = useId()
  const rootRef = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  const selected = useMemo(() => (value ? parseIso(value) : new Date()), [value])
  const [view, setView] = useState(() => new Date(selected.getFullYear(), selected.getMonth(), 1))

  useEffect(() => {
    if (open) setView(new Date(selected.getFullYear(), selected.getMonth(), 1))
  }, [open, selected])

  useEffect(() => {
    if (!open) return
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const cells = useMemo(() => {
    const first = new Date(view.getFullYear(), view.getMonth(), 1)
    const startPad = first.getDay()
    const daysInMonth = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate()
    const out: Array<{ date: Date; inMonth: boolean } | null> = []
    for (let i = 0; i < startPad; i++) out.push(null)
    for (let d = 1; d <= daysInMonth; d++) {
      out.push({ date: new Date(view.getFullYear(), view.getMonth(), d), inMonth: true })
    }
    while (out.length % 7 !== 0) out.push(null)
    return out
  }, [view])

  const minD = min ? parseIso(min) : null
  const maxD = max ? parseIso(max) : null
  const today = new Date()

  function pick(d: Date) {
    if (minD && d < minD) return
    if (maxD && d > maxD) return
    onChange(toIso(d))
    setOpen(false)
  }

  function shiftMonth(delta: number) {
    setView((v) => new Date(v.getFullYear(), v.getMonth() + delta, 1))
  }

  return (
    <div ref={rootRef} className="relative flex flex-col gap-1.5">
      <label htmlFor={id} className="text-xs tracking-[0.14em] text-mist/80">
        {label}
      </label>
      <button
        id={id}
        type="button"
        className="jp-cal-trigger"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="font-display text-sm tracking-wide text-fog">{formatDisplay(value)}</span>
        <span className="text-[10px] tracking-[0.2em] text-gold/80">暦</span>
      </button>
      {hint ? <p className="text-[11px] text-mist/45">{hint}</p> : null}

      {open ? (
        <div className="jp-cal-popover anim-rise" role="dialog" aria-label={`${label} 달력`}>
          <div
            className="jp-cal-banner"
            style={{ backgroundImage: 'url(/generated/calendar-header-strip.png)' }}
          >
            <p className="font-display text-sm tracking-[0.22em] text-gold">
              {view.getFullYear()}年 {view.getMonth() + 1}月
            </p>
            <div className="flex gap-1">
              <button type="button" className="jp-cal-nav" onClick={() => shiftMonth(-1)} aria-label="이전 달">
                ‹
              </button>
              <button type="button" className="jp-cal-nav" onClick={() => shiftMonth(1)} aria-label="다음 달">
                ›
              </button>
            </div>
          </div>

          <div className="grid grid-cols-7 gap-px px-2 pt-2">
            {WEEK.map((w, i) => (
              <div
                key={w}
                className={`py-1 text-center font-display text-[11px] tracking-widest ${
                  i === 0 ? 'text-ember/80' : i === 6 ? 'text-sea-bright/80' : 'text-mist/55'
                }`}
              >
                {w}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-1 px-2 pb-3 pt-1">
            {cells.map((cell, idx) => {
              if (!cell) return <div key={`e-${idx}`} />
              const { date } = cell
              const disabled =
                (minD != null && date < new Date(minD.getFullYear(), minD.getMonth(), minD.getDate())) ||
                (maxD != null && date > new Date(maxD.getFullYear(), maxD.getMonth(), maxD.getDate()))
              const isSelected = value ? sameDay(date, selected) : false
              const isToday = sameDay(date, today)
              const dow = date.getDay()
              return (
                <button
                  key={toIso(date)}
                  type="button"
                  disabled={disabled}
                  onClick={() => pick(date)}
                  className={`jp-cal-day ${isSelected ? 'jp-cal-day-selected' : ''} ${
                    isToday && !isSelected ? 'jp-cal-day-today' : ''
                  } ${dow === 0 ? 'text-ember/90' : dow === 6 ? 'text-sea-bright/90' : ''}`}
                >
                  {date.getDate()}
                </button>
              )
            })}
          </div>
        </div>
      ) : null}
    </div>
  )
}
