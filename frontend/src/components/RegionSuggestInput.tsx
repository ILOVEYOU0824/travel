import { useEffect, useId, useRef, useState } from 'react'
import { filterJapanRegions } from '../data/japanRegions'

export function RegionSuggestInput({
  value,
  onChange,
  placeholder,
  required,
  id,
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  required?: boolean
  id?: string
}) {
  const listId = useId()
  const wrapRef = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(0)
  const suggestions = filterJapanRegions(value, 12)

  useEffect(() => {
    setHighlight(0)
  }, [value])

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  function pick(name: string) {
    onChange(name)
    setOpen(false)
  }

  return (
    <div ref={wrapRef} className="relative">
      <input
        id={id}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        autoComplete="off"
        className="jp-field w-full text-sm"
        value={value}
        required={required}
        placeholder={placeholder}
        onChange={(e) => {
          onChange(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (!open && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
            setOpen(true)
            return
          }
          if (e.key === 'ArrowDown') {
            e.preventDefault()
            setHighlight((h) => Math.min(h + 1, Math.max(suggestions.length - 1, 0)))
          } else if (e.key === 'ArrowUp') {
            e.preventDefault()
            setHighlight((h) => Math.max(h - 1, 0))
          } else if (e.key === 'Enter' && open && suggestions[highlight]) {
            e.preventDefault()
            pick(suggestions[highlight].name)
          } else if (e.key === 'Escape') {
            setOpen(false)
          }
        }}
      />
      {open && suggestions.length > 0 ? (
        <ul id={listId} role="listbox" className="jp-dropdown absolute z-20 mt-1 max-h-56 w-full overflow-y-auto py-1">
          {suggestions.map((s, i) => (
            <li key={s.name} role="option" aria-selected={i === highlight}>
              <button
                type="button"
                className="jp-dropdown-item"
                aria-current={i === highlight ? 'true' : undefined}
                onMouseEnter={() => setHighlight(i)}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => pick(s.name)}
              >
                {s.name}
                {s.aliases[1] ? (
                  <span className="ml-2 text-xs text-mist/45">{s.aliases[1]}</span>
                ) : null}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
