import { usePlannerStore } from '../store/plannerStore'

const CHIPS = [
  '라멘 추가해줘',
  '오코노미야키 먹고 싶어',
  '이 장소 빼줘',
  '쓰텐카쿠는 빼줘',
  '카페 하나 더 넣어줘',
] as const

export function ReplanBar({ embedded = false }: { embedded?: boolean }) {
  const replanPrompt = usePlannerStore((s) => s.replanPrompt)
  const replanning = usePlannerStore((s) => s.replanning)
  const replanMessage = usePlannerStore((s) => s.replanMessage)
  const error = usePlannerStore((s) => s.error)
  const selectedPlaceId = usePlannerStore((s) => s.selectedPlaceId)
  const result = usePlannerStore((s) => s.result)
  const selectedDayIndex = usePlannerStore((s) => s.selectedDayIndex)
  const setField = usePlannerStore((s) => s.setField)
  const replan = usePlannerStore((s) => s.replan)
  const goHome = usePlannerStore((s) => s.goHome)

  function applyChip(chip: string) {
    if (chip === '이 장소 빼줘') {
      const day = result?.days[selectedDayIndex]
      const place = day?.items.find((it) => it.place.place_id === selectedPlaceId)?.place
      const name = place?.name
      setField('replanPrompt', name ? `${name} 빼줘` : '선택 장소를 빼줘')
      return
    }
    setField('replanPrompt', chip)
  }

  return (
    <div className={embedded ? 'px-4 py-4' : 'border-b border-white/10 px-4 py-2.5 sm:px-6'}>
      <form
        className={`flex flex-col gap-3 ${embedded ? '' : 'mx-auto max-w-7xl gap-2'}`}
        onSubmit={(e) => {
          e.preventDefault()
          if (!replanPrompt.trim() || replanning) return
          void replan()
          setField('resultTab', 'itinerary')
        }}
      >
        {embedded ? (
          <p className="text-xs text-mist/55">
            반영을 누르면 뒤에서 수정합니다. 홈·다른 탭으로 이동해도 됩니다.
          </p>
        ) : null}
        <div className="flex flex-wrap items-center gap-2">
          <p className="jp-legend shrink-0 text-sm">일정 수정</p>
          {CHIPS.map((chip) => (
            <button
              key={chip}
              type="button"
              className="jp-chip"
              disabled={replanning}
              onClick={() => applyChip(chip)}
            >
              {chip}
            </button>
          ))}
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <label className="sr-only" htmlFor="replan-prompt">
            일정 재조정 요청
          </label>
          <input
            id="replan-prompt"
            className="jp-field min-w-0 flex-1 text-sm"
            placeholder="먹고 싶은 것·빼고 싶은 장소를 적어 주세요"
            value={replanPrompt}
            onChange={(e) => setField('replanPrompt', e.target.value)}
            disabled={replanning}
          />
          <button
            type="submit"
            disabled={replanning || !replanPrompt.trim()}
            className="jp-btn jp-btn-primary text-xs"
          >
            {replanning ? '수정 중…' : '반영하기'}
          </button>
        </div>
      </form>
      {replanning ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <p className="text-xs text-gold/85">완료되면 상단에 알려 드립니다.</p>
          <button type="button" className="jp-btn jp-btn-ghost text-xs" onClick={goHome}>
            홈으로
          </button>
          <button
            type="button"
            className="jp-btn jp-btn-secondary text-xs"
            onClick={() => setField('resultTab', 'itinerary')}
          >
            일정 보기
          </button>
        </div>
      ) : null}
      {replanMessage && !replanning ? (
        <p
          className={`mt-2 whitespace-pre-line text-xs text-gold ${embedded ? 'px-0' : 'mx-auto max-w-7xl'}`}
        >
          {replanMessage}
        </p>
      ) : null}
      {error && !replanning ? (
        <p
          className={`mt-2 whitespace-pre-line text-xs text-ember ${embedded ? 'px-0' : 'mx-auto max-w-7xl'}`}
        >
          {error}
        </p>
      ) : null}
    </div>
  )
}
