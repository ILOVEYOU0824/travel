import { useEffect, useId, useMemo, useRef, useState } from 'react'

function parseHm(value: string): { h: number; m: number } {
  const [hs, ms] = (value || '00:00').split(':')
  const h = Math.min(23, Math.max(0, Number(hs) || 0))
  const m = Math.min(59, Math.max(0, Number(ms) || 0))
  return { h, m: (Math.round(m / 5) * 5) % 60 }
}

function fmt(h: number, m: number): string {
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

const HOURS = Array.from({ length: 24 }, (_, i) => i)
const MINS = Array.from({ length: 12 }, (_, i) => i * 5)

export function JpTimePicker({
  label,
  value,
  onChange,
  accent = '出',
}: {
  label: string
  value: string
  onChange: (hm: string) => void
  accent?: string
}) {
  const id = useId()
  const rootRef = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  const { h, m } = useMemo(() => parseHm(value), [value])

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
    rootRef.current
      ?.querySelectorAll('.jp-time-option-active')
      .forEach((el) => el.scrollIntoView({ block: 'center' }))
    return () => {
      document.removeEventListener('mousedown', onDoc)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  function setHour(next: number) {
    onChange(fmt(next, m))
  }
  function setMin(next: number) {
    onChange(fmt(h, next))
  }

  const period = h < 12 ? '午前' : '午後'
  const h12 = h % 12 === 0 ? 12 : h % 12

  return (
    <div ref={rootRef} className="relative flex flex-col gap-1.5">
      <label htmlFor={id} className="text-xs tracking-[0.12em] text-mist/75">
        {label}
      </label>
      <button
        id={id}
        type="button"
        className="jp-time-trigger"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="jp-time-accent">{accent}</span>
        <span className="font-display text-2xl tracking-[0.08em] text-fog tabular-nums">
          {String(h).padStart(2, '0')}
          <span className="mx-0.5 text-gold/70">:</span>
          {String(m).padStart(2, '0')}
        </span>
        <span className="text-[11px] tracking-[0.18em] text-mist/55">
          {period} {h12}時
        </span>
      </button>

      {open ? (
        <div className="jp-time-popover anim-rise" role="dialog" aria-label={`${label} 시각 선택`}>
          <p className="mb-2 px-1 font-display text-xs tracking-[0.2em] text-gold/90">時刻を選ぶ</p>
          <div className="jp-time-columns">
            <div className="jp-time-col">
              <p className="jp-time-col-label">時</p>
              <div className="jp-time-scroll">
                {HOURS.map((hour) => (
                  <button
                    key={hour}
                    type="button"
                    className={`jp-time-option ${hour === h ? 'jp-time-option-active' : ''}`}
                    onClick={() => setHour(hour)}
                  >
                    {String(hour).padStart(2, '0')}
                  </button>
                ))}
              </div>
            </div>
            <div className="jp-time-divider" aria-hidden />
            <div className="jp-time-col">
              <p className="jp-time-col-label">分</p>
              <div className="jp-time-scroll">
                {MINS.map((min) => (
                  <button
                    key={min}
                    type="button"
                    className={`jp-time-option ${min === m ? 'jp-time-option-active' : ''}`}
                    onClick={() => setMin(min)}
                  >
                    {String(min).padStart(2, '0')}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <button type="button" className="jp-btn jp-btn-secondary mt-3 w-full text-xs" onClick={() => setOpen(false)}>
            確定 · 완료
          </button>
        </div>
      ) : null}
    </div>
  )
}
