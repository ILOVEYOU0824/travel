import { useEffect, useId, useRef, useState } from 'react'
import { autocompletePlaces, fetchAirportOptions } from '../api/itinerary'
import type { AirportOption, PlaceAutocompleteSuggestion } from '../types'
import { useAuthStore } from '../store/authStore'
import { usePlannerStore } from '../store/plannerStore'
import { formatDateLabel } from '../lib/format'
import { JpDatePicker } from './JpDatePicker'
import { JpTimePicker } from './JpTimePicker'
import { RegionSuggestInput } from './RegionSuggestInput'

function dayCount(start: string, end: string): number {
  const a = new Date(`${start}T12:00:00`).getTime()
  const b = new Date(`${end}T12:00:00`).getTime()
  if (Number.isNaN(a) || Number.isNaN(b) || b < a) return 1
  return Math.floor((b - a) / 86_400_000) + 1
}

function formatWon(n: number): string {
  return n.toLocaleString('ko-KR')
}

function flightHint(
  outboundDep: string,
  returnDep: string,
  firstRegion: string,
): { arrivalEst: string; summary: string } {
  const toMin = (t: string) => {
    const [h, m] = t.split(':').map(Number)
    return h * 60 + m
  }
  const fmt = (m: number) => {
    const x = ((m % (24 * 60)) + 24 * 60) % (24 * 60)
    return `${String(Math.floor(x / 60)).padStart(2, '0')}:${String(x % 60).padStart(2, '0')}`
  }
  let flight = 130
  if (/후쿠오카|하카타/.test(firstRegion)) flight = 95
  else if (/오사카|교토|고베|나라/.test(firstRegion)) flight = 120
  else if (/도쿄|요코하마|나리타|하네다/.test(firstRegion)) flight = 150
  else if (/삿포로|홋카이도/.test(firstRegion)) flight = 160
  else if (/오키나와|나하/.test(firstRegion)) flight = 165
  else if (/나고야/.test(firstRegion)) flight = 120

  const arrivalEst = fmt(toMin(outboundDep) + flight)
  const ready = toMin(arrivalEst) + 90
  let first = '오전부터'
  if (ready >= 18 * 60 + 30) first = '밤 짧게'
  else if (ready >= 15 * 60 + 30) first = '저녁부터'
  else if (ready >= 12 * 60 + 30) first = '오후부터'
  else if (ready >= 10 * 60) first = '점심부터'

  const leaveBy = toMin(returnDep) - 180
  let last = '저녁까지'
  if (leaveBy < 8 * 60) last = '공항 이동 위주'
  else if (leaveBy < 11 * 60) last = '아침만'
  else if (leaveBy < 14 * 60) last = '점심까지'
  else if (leaveBy < 17 * 60) last = '오후 초반까지'

  return {
    arrivalEst,
    summary: `예상 일본 도착 약 ${arrivalEst}(비행 ~${flight}분) · 첫날 ${first} · 귀국일 ${last}`,
  }
}

function MustHaveSection({
  title,
  hint,
  draft,
  items,
  regionHint,
  onDraft,
  onAdd,
  onRemove,
}: {
  title: string
  hint: string
  draft: string
  items: string[]
  regionHint: string
  onDraft: (v: string) => void
  onAdd: () => void
  onRemove: (v: string) => void
}) {
  const listId = useId()
  const wrapRef = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(0)
  const [suggestions, setSuggestions] = useState<PlaceAutocompleteSuggestion[]>([])

  useEffect(() => {
    const q = draft.trim()
    if (q.length < 2) {
      setSuggestions([])
      return
    }
    const t = window.setTimeout(() => {
      const input = regionHint ? `${regionHint} ${q}` : q
      void autocompletePlaces({ input, max_suggestions: 5 })
        .then((res) => {
          setSuggestions(res.suggestions)
          setOpen(res.suggestions.length > 0)
          setHighlight(0)
        })
        .catch(() => setSuggestions([]))
    }, 280)
    return () => window.clearTimeout(t)
  }, [draft, regionHint])

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  function pick(s: PlaceAutocompleteSuggestion) {
    onDraft(s.primary_text.replace(/^MOCK_/, ''))
    setOpen(false)
    setSuggestions([])
  }

  return (
    <div className="flex flex-col gap-2">
      <p className="font-display text-sm tracking-wide text-fog/90">{title}</p>
      <div className="flex gap-2">
        <div ref={wrapRef} className="relative min-w-0 flex-1">
          <input
            role="combobox"
            aria-expanded={open}
            aria-controls={listId}
            aria-autocomplete="list"
            autoComplete="off"
            className="jp-field w-full text-sm"
            value={draft}
            onChange={(e) => {
              onDraft(e.target.value)
              setOpen(true)
            }}
            onFocus={() => suggestions.length > 0 && setOpen(true)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown' && suggestions.length) {
                e.preventDefault()
                setOpen(true)
                setHighlight((h) => Math.min(h + 1, suggestions.length - 1))
              } else if (e.key === 'ArrowUp' && suggestions.length) {
                e.preventDefault()
                setHighlight((h) => Math.max(h - 1, 0))
              } else if (e.key === 'Enter') {
                e.preventDefault()
                if (open && suggestions[highlight]) pick(suggestions[highlight])
                else onAdd()
              } else if (e.key === 'Escape') {
                setOpen(false)
              }
            }}
            placeholder={hint}
          />
          {open && suggestions.length > 0 ? (
            <ul
              id={listId}
              role="listbox"
              className="jp-dropdown absolute z-20 mt-1 max-h-56 w-full overflow-y-auto py-1"
            >
              {suggestions.map((s, i) => (
                <li key={s.place_id} role="option" aria-selected={i === highlight}>
                  <button
                    type="button"
                    className="jp-dropdown-item text-left"
                    aria-current={i === highlight ? 'true' : undefined}
                    onMouseEnter={() => setHighlight(i)}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => pick(s)}
                  >
                    <span className="block">{s.primary_text.replace(/^MOCK_/, '')}</span>
                    {s.secondary_text ? (
                      <span className="block text-xs text-mist/45">{s.secondary_text}</span>
                    ) : null}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        <button type="button" onClick={onAdd} className="jp-btn jp-btn-secondary jp-btn-icon">
          ＋
        </button>
      </div>
      {items.length > 0 ? (
        <ul className="flex flex-wrap gap-2">
          {items.map((item) => (
            <li key={item} className="jp-chip">
              {item}
              <button
                type="button"
                aria-label={`${item} 삭제`}
                onClick={() => onRemove(item)}
                className="text-mist/55 transition hover:text-ember"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-mist/45">
          입력하면 Places 자동완성 후보가 나옵니다. 없는 장소는 AI가 만들지 않습니다.
        </p>
      )}
    </div>
  )
}

export function PlannerForm() {
  const startDate = usePlannerStore((s) => s.startDate)
  const endDate = usePlannerStore((s) => s.endDate)
  const dayRegions = usePlannerStore((s) => s.dayRegions)
  const foodDraft = usePlannerStore((s) => s.foodDraft)
  const sightDraft = usePlannerStore((s) => s.sightDraft)
  const mustHaveFood = usePlannerStore((s) => s.mustHaveFood)
  const mustHaveSights = usePlannerStore((s) => s.mustHaveSights)
  const includeLodging = usePlannerStore((s) => s.includeLodging)
  const includeTravelTimes = usePlannerStore((s) => s.includeTravelTimes)
  const travelers = usePlannerStore((s) => s.travelers)
  const budgetKrwPerPerson = usePlannerStore((s) => s.budgetKrwPerPerson)
  const outboundDepartureKst = usePlannerStore((s) => s.outboundDepartureKst)
  const returnDepartureJst = usePlannerStore((s) => s.returnDepartureJst)
  const arrivalAirportQuery = usePlannerStore((s) => s.arrivalAirportQuery)
  const loading = usePlannerStore((s) => s.loading)
  const replanning = usePlannerStore((s) => s.replanning)
  const result = usePlannerStore((s) => s.result)
  const error = usePlannerStore((s) => s.error)
  const setField = usePlannerStore((s) => s.setField)
  const setDateRange = usePlannerStore((s) => s.setDateRange)
  const setDayRegion = usePlannerStore((s) => s.setDayRegion)
  const addMustHave = usePlannerStore((s) => s.addMustHave)
  const removeMustHave = usePlannerStore((s) => s.removeMustHave)
  const generate = usePlannerStore((s) => s.generate)
  const authReady = useAuthStore((s) => s.ready)
  const authConfigured = useAuthStore((s) => s.configured)
  const user = useAuthStore((s) => s.user)
  const loginWithKakao = useAuthStore((s) => s.loginWithKakao)
  const [airports, setAirports] = useState<AirportOption[]>([
    { id: 'auto', label: '지역 기준 자동', query: '' },
  ])

  useEffect(() => {
    void fetchAirportOptions()
      .then(setAirports)
      .catch(() => {
        /* 기본 auto만 유지 */
      })
  }, [])

  const days = dayCount(startDate, endDate)
  const groupTotal = budgetKrwPerPerson * Math.max(1, travelers)
  const perPersonPerDay = Math.floor(budgetKrwPerPerson / days)
  const tierHint =
    perPersonPerDay < 80_000 ? '저예산' : perPersonPerDay < 180_000 ? '보통' : '여유'
  const firstRegion = dayRegions[0]?.region?.trim() || '오사카'
  const flight = flightHint(outboundDepartureKst, returnDepartureJst, firstRegion)

  if (!authReady) {
    return <p className="text-sm text-mist/55">로그인 확인 중…</p>
  }

  if (!authConfigured || !user) {
    return (
      <div className="anim-rise-delay jp-panel flex flex-col items-start gap-4 px-5 py-6">
        <p className="text-sm leading-relaxed text-mist/80">
          일정 짜기는 <span className="text-fog">카카오 로그인</span> 후 이용할 수 있습니다.
        </p>
        {!authConfigured ? (
          <p className="text-xs text-ember/90">
            로그인 설정이 없습니다. Netlify Environment에 VITE_SUPABASE_URL /
            VITE_SUPABASE_ANON_KEY / VITE_KAKAO_REST_API_KEY를 넣고 다시 배포하세요.
          </p>
        ) : (
          <button
            type="button"
            onClick={() => void loginWithKakao()}
            className="jp-btn jp-btn-kakao px-6 py-3 text-sm"
          >
            카카오톡 로그인
          </button>
        )}
      </div>
    )
  }

  return (
    <form
      className="anim-rise-delay flex w-full max-w-xl flex-col gap-6"
      onSubmit={(e) => {
        e.preventDefault()
        if (replanning) return
        if (result && !window.confirm('지금 보고 있던 일정을 새 일정으로 바꿀까요?')) return
        void generate()
      }}
    >
      <fieldset className="jp-panel flex flex-col gap-4">
        <legend className="jp-legend px-1">旅の日程 · 여행 기간</legend>
        <p className="text-xs leading-relaxed text-mist/55">
          일본식 달력에서 시작·종료일을 고르세요. 요일은 日〜土로 표시됩니다.
        </p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <JpDatePicker
            label="始 · 시작일"
            value={startDate}
            max={endDate}
            onChange={(v) => setDateRange(v, endDate < v ? v : endDate)}
          />
          <JpDatePicker
            label="終 · 종료일"
            value={endDate}
            min={startDate}
            onChange={(v) => setDateRange(startDate, v)}
          />
        </div>
      </fieldset>

      <fieldset className="jp-panel flex flex-col gap-3">
        <legend className="jp-legend px-1">飛行時刻 · 비행 시간표</legend>
        <p className="text-xs leading-relaxed text-mist/60">
          티켓에 적힌 <span className="text-fog/90">출발 시각</span>만 고르세요. 일본 도착은 첫날
          지역 기준으로 자동 추정합니다.
        </p>
        <div className="jp-flight-row">
          <div className="jp-flight-card">
            <p className="jp-flight-label">出 · 출국편</p>
            <p className="mt-1 text-xs text-mist/55">{formatDateLabel(startDate)} · 한국 출발</p>
            <div className="mt-3">
              <JpTimePicker
                label="출발 시각 (KST)"
                value={outboundDepartureKst}
                onChange={(v) => setField('outboundDepartureKst', v)}
                accent="出"
              />
            </div>
            <p className="mt-3 border-t border-white/10 pt-2 text-xs text-gold/90">
              予想到着 · 예상 도착 {flight.arrivalEst}
            </p>
          </div>
          <div className="jp-flight-card">
            <p className="jp-flight-label">帰 · 귀국편</p>
            <p className="mt-1 text-xs text-mist/55">{formatDateLabel(endDate)} · 일본 출발</p>
            <div className="mt-3">
              <JpTimePicker
                label="출발 시각 (JST)"
                value={returnDepartureJst}
                onChange={(v) => setField('returnDepartureJst', v)}
                accent="帰"
              />
            </div>
          </div>
        </div>
        <p className="text-xs text-gold/90">{flight.summary}</p>
        <label className="flex flex-col gap-1.5 text-xs tracking-wide text-mist/80">
          도착 공항
          <select
            className="jp-field text-sm"
            value={arrivalAirportQuery}
            onChange={(e) => setField('arrivalAirportQuery', e.target.value)}
          >
            {airports.map((a) => (
              <option key={a.id} value={a.query}>
                {a.label}
              </option>
            ))}
          </select>
          <span className="text-[11px] text-mist/45">
            자동이면 첫날 지역으로 공항을 고릅니다. 나리타/하네다 등은 직접 선택하세요.
          </span>
        </label>
      </fieldset>

      <fieldset className="jp-panel flex flex-col gap-3">
        <legend className="jp-legend px-1">여행 경비</legend>
        <p className="text-xs leading-relaxed text-mist/60">
          여기서 정하는 금액은 <span className="text-fog/90">1명이 이번 여행에 쓸 총 경비</span>
          입니다. (하루 단가가 아닙니다.) 인원을 늘리면 일행 전체 합계만 같이 계산됩니다.
        </p>
        <label className="flex flex-col gap-1.5 text-xs tracking-wide text-mist/80">
          인원
          <input
            type="number"
            min={1}
            max={20}
            className="jp-field text-sm"
            value={travelers}
            onChange={(e) => setField('travelers', Math.max(1, Number(e.target.value) || 1))}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-xs tracking-wide text-mist/80">
          1인당 총 여행경비 (원)
          <input
            type="range"
            min={300_000}
            max={5_000_000}
            step={50_000}
            value={budgetKrwPerPerson}
            onChange={(e) => setField('budgetKrwPerPerson', Number(e.target.value))}
            className="jp-range w-full"
          />
          <div className="flex items-center gap-2">
            <input
              type="number"
              min={100_000}
              max={20_000_000}
              step={50_000}
              className="jp-field min-w-0 flex-1 text-sm"
              value={budgetKrwPerPerson}
              onChange={(e) => {
                const n = Number(e.target.value)
                if (!Number.isFinite(n)) return
                setField('budgetKrwPerPerson', Math.min(20_000_000, Math.max(100_000, n)))
              }}
            />
            <span className="shrink-0 text-xs text-mist/60">원 / 1인</span>
          </div>
        </label>
        <ul className="space-y-1 text-xs leading-relaxed text-mist/65">
          <li>
            1인 총경비 <span className="text-fog">{formatWon(budgetKrwPerPerson)}원</span>
            {travelers > 1 ? (
              <>
                {' '}
                · 일행 {travelers}명 합계 <span className="text-fog">{formatWon(groupTotal)}원</span>
              </>
            ) : null}
          </li>
          <li>
            예상 티어 <span className="text-gold">{tierHint}</span>
            <span className="text-mist/45">
              {' '}
              (일정 {days}일 기준 참고 환산 약 {formatWon(perPersonPerDay)}원/일 · Exact 견적 아님)
            </span>
          </li>
          <li>숙소·식사는 Google 가격대(₩)로 맞춥니다. 실제 예약가는 직접 확인하세요.</li>
        </ul>
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="jp-legend">날짜별 지역</legend>
        <p className="text-xs text-mist/50">예: 1일차 오사카 → 2일차 교토 · 입력하면 지역이 필터됩니다</p>
        <ul className="flex flex-col gap-3">
          {dayRegions.map((d, i) => (
            <li
              key={d.date}
              className="grid grid-cols-[7rem_1fr] items-end gap-3 sm:grid-cols-[9rem_1fr]"
            >
              <span className="pb-2 text-xs tracking-wide text-mist/70">
                {i + 1}일차 · {formatDateLabel(d.date)}
              </span>
              <RegionSuggestInput
                value={d.region}
                onChange={(v) => setDayRegion(d.date, v)}
                placeholder="지역 검색 (오사카, 京都, osaka…)"
                required
              />
            </li>
          ))}
        </ul>
      </fieldset>

      <fieldset className="jp-panel flex flex-col gap-4">
        <legend className="jp-legend px-1">필수 요청</legend>
        <MustHaveSection
          title="음식"
          hint="예: 라멘, 오코노미야키"
          draft={foodDraft}
          items={mustHaveFood}
          regionHint={dayRegions[0]?.region ?? ''}
          onDraft={(v) => setField('foodDraft', v)}
          onAdd={() => addMustHave('food')}
          onRemove={(v) => removeMustHave('food', v)}
        />
        <MustHaveSection
          title="관광지"
          hint="예: 후시미이나리, 오사카성"
          draft={sightDraft}
          items={mustHaveSights}
          regionHint={dayRegions[0]?.region ?? ''}
          onDraft={(v) => setField('sightDraft', v)}
          onAdd={() => addMustHave('sight')}
          onRemove={(v) => removeMustHave('sight', v)}
        />
      </fieldset>

      <label className="flex items-center gap-2.5 text-sm text-mist/80">
        <input
          type="checkbox"
          checked={includeLodging}
          onChange={(e) => setField('includeLodging', e.target.checked)}
          className="jp-check"
        />
        숙소 추천 포함 (Google Places · 예약은 Klook)
      </label>

      <label className="flex items-center gap-2.5 text-sm text-mist/80">
        <input
          type="checkbox"
          checked={includeTravelTimes}
          onChange={(e) => setField('includeTravelTimes', e.target.checked)}
          className="jp-check"
        />
        장소 사이 이동시간·수단 계산 (도보/대중교통 비교)
      </label>

      {error ? (
        <p className="border border-ember/40 bg-ember/10 px-3 py-2 text-sm text-ember">{error}</p>
      ) : null}

      <button
        type="submit"
        disabled={loading || replanning}
        className="jp-btn jp-btn-primary mt-1 w-full py-3.5 text-base"
      >
        {loading ? '일정 구성 중…' : replanning ? '일정 수정이 끝난 뒤 만들 수 있습니다' : '일정 만들기'}
      </button>
    </form>
  )
}
