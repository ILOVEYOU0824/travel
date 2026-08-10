import { useState } from 'react'
import { exportItineraryPdf } from '../lib/exportPdf'
import { kakaoShareConfigured, shareTripToKakao } from '../lib/kakaoShare'
import { usePlannerStore } from '../store/plannerStore'

export function SaveBar() {
  const result = usePlannerStore((s) => s.result)
  const tripId = usePlannerStore((s) => s.tripId)
  const tripTitle = usePlannerStore((s) => s.tripTitle)
  const saving = usePlannerStore((s) => s.saving)
  const shareUrl = usePlannerStore((s) => s.shareUrl)
  const saveMessage = usePlannerStore((s) => s.saveMessage)
  const setField = usePlannerStore((s) => s.setField)
  const save = usePlannerStore((s) => s.save)
  const [copied, setCopied] = useState(false)
  const [pdfBusy, setPdfBusy] = useState(false)
  const [status, setStatus] = useState<string | null>(null)
  const [statusTone, setStatusTone] = useState<'ok' | 'err'>('ok')
  const [sharing, setSharing] = useState(false)

  function flash(msg: string, tone: 'ok' | 'err' = 'ok') {
    setStatus(msg)
    setStatusTone(tone)
  }

  async function copyLink() {
    if (!shareUrl) return
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      flash('링크를 복사했습니다.')
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      flash('링크 복사에 실패했습니다.', 'err')
    }
  }

  async function downloadPdf() {
    if (!result) return
    setPdfBusy(true)
    flash('인쇄 창을 여는 중… PDF로 저장을 선택하세요.')
    try {
      await exportItineraryPdf(result, tripTitle)
      flash('인쇄 창에서 «PDF로 저장»을 선택하세요.')
    } catch (e) {
      flash(e instanceof Error ? e.message : 'PDF 저장에 실패했습니다.', 'err')
    } finally {
      setPdfBusy(false)
    }
  }

  async function shareKakao() {
    let url = shareUrl
    if (!url) {
      await save()
      url = usePlannerStore.getState().shareUrl
    }
    if (!url) {
      flash('먼저 일정을 저장해 주세요.', 'err')
      return
    }
    const title = tripTitle.trim() || '내 일본 여행'
    const n = result?.days.length ?? 0
    const regions = Array.from(
      new Set((result?.days ?? []).map((d) => d.region).filter(Boolean)),
    ).slice(0, 3)
    const description = `${regions.join(' · ') || '일본'} ${n}일 일정 · JapanTrip`
    setSharing(true)
    try {
      await shareTripToKakao({ title, description, shareUrl: url })
      flash('카카오톡 공유 창을 열었습니다.')
    } catch (e) {
      const msg = e instanceof Error ? e.message : '카카오톡 공유에 실패했습니다.'
      const origin = window.location.origin
      flash(
        /4019|인증|domain|도메인/i.test(msg)
          ? `카카오 콘솔에 웹 도메인 등록 필요: ${origin}`
          : msg,
        'err',
      )
    } finally {
      setSharing(false)
    }
  }

  const banner = status || saveMessage

  return (
    <div className="border-b border-white/10 px-4 py-3 sm:px-6">
      <div className="mx-auto flex max-w-7xl flex-col gap-2.5">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
          <label className="flex min-w-0 flex-1 flex-col gap-1 text-[11px] tracking-wide text-mist/60">
            일정 제목
            <input
              className="jp-field text-sm"
              value={tripTitle}
              onChange={(e) => setField('tripTitle', e.target.value)}
              placeholder="예: 오사카·교토 3박"
              aria-label="일정 제목"
            />
          </label>
          <div className="flex flex-wrap items-center gap-1.5 lg:justify-end">
            <button
              type="button"
              onClick={() => void save()}
              disabled={saving}
              className="jp-btn jp-btn-primary text-xs"
            >
              {saving ? '저장 중…' : tripId ? '저장' : '일정 저장'}
            </button>
            <button
              type="button"
              onClick={() => void downloadPdf()}
              disabled={pdfBusy}
              className="jp-btn jp-btn-secondary text-xs"
            >
              {pdfBusy ? 'PDF 준비 중…' : 'PDF'}
            </button>
            {shareUrl ? (
              <button
                type="button"
                onClick={() => void copyLink()}
                className="jp-btn jp-btn-ghost text-xs"
              >
                {copied ? '복사됨' : '링크 복사'}
              </button>
            ) : null}
            {kakaoShareConfigured() ? (
              <button
                type="button"
                onClick={() => void shareKakao()}
                disabled={sharing || saving}
                className="jp-btn jp-btn-kakao text-xs"
              >
                {sharing ? '공유 중…' : '카카오톡'}
              </button>
            ) : null}
          </div>
        </div>
        {banner ? (
          <p
            className={`text-xs ${statusTone === 'err' && status ? 'text-ember' : 'text-gold/85'}`}
          >
            {banner}
          </p>
        ) : null}
      </div>
    </div>
  )
}
