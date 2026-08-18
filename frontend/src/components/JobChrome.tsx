import { useEffect } from 'react'
import { usePlannerStore } from '../store/plannerStore'

export function JobChrome() {
  const replanning = usePlannerStore((s) => s.replanning)
  const jobToast = usePlannerStore((s) => s.jobToast)
  const showResult = usePlannerStore((s) => s.showResult)
  const dismissJobToast = usePlannerStore((s) => s.dismissJobToast)

  useEffect(() => {
    if (!replanning) return
    const onLeave = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', onLeave)
    return () => window.removeEventListener('beforeunload', onLeave)
  }, [replanning])

  useEffect(() => {
    if (!jobToast) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') dismissJobToast()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [jobToast, dismissJobToast])

  useEffect(() => {
    if (jobToast?.action === 'open-result') {
      document.getElementById('jp-job-go')?.focus()
    }
  }, [jobToast])

  if (!replanning && !jobToast) return null

  return (
    <div className="pointer-events-none fixed inset-x-0 top-0 z-[60] flex flex-col items-center gap-2 px-3 pt-3">
      {replanning ? (
        <div role="status" aria-live="polite" className="jp-job-chip pointer-events-auto max-w-lg">
          <span className="jp-job-dot" aria-hidden />
          <p className="text-xs tracking-wide text-fog">일정 수정 중 · 다른 화면을 둘러보셔도 됩니다</p>
        </div>
      ) : null}

      {jobToast ? (
        <div
          role={jobToast.kind === 'error' ? 'alert' : 'status'}
          aria-live="assertive"
          className={`jp-job-toast pointer-events-auto ${
            jobToast.kind === 'error' ? 'jp-job-toast-error' : 'jp-job-toast-ok'
          }`}
        >
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium tracking-wide text-fog">{jobToast.title}</p>
            {jobToast.detail ? (
              <p className="mt-0.5 line-clamp-2 text-[11px] text-mist/70">{jobToast.detail}</p>
            ) : null}
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            {jobToast.action === 'open-result' ? (
              <button
                type="button"
                id="jp-job-go"
                className="jp-btn jp-btn-primary text-xs"
                onClick={() => showResult('itinerary')}
              >
                이동
              </button>
            ) : null}
            <button
              type="button"
              className="jp-btn jp-btn-ghost px-2.5 text-xs"
              aria-label="알림 닫기"
              onClick={dismissJobToast}
            >
              닫기
            </button>
          </div>
        </div>
      ) : null}
    </div>
  )
}
