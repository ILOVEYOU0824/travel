import { AffiliateOutboundLink } from './AffiliateOutboundLink'
import { usePlannerStore } from '../store/plannerStore'

const PREP_LINKS = [
  {
    key: 'visitjapan',
    label: 'Visit Japan',
    url: 'https://www.vjw.digital.go.jp/main/#/vjwplo001',
    className: 'jp-btn jp-btn-visit text-xs',
    title: 'Visit Japan Web 입국 수속',
  },
  {
    key: 'insurance',
    label: '여행자 보험',
    url: 'https://insurance.pay.naver.com/travel',
    className: 'jp-btn jp-btn-insurance text-xs',
    title: '네이버페이 해외여행보험 비교',
  },
] as const

/** 준비 CTA만 (이동수단 선택은 구글맵 길찾기로 대체) */
export function TripControlsBar({ embedded = false }: { embedded?: boolean }) {
  const prepCtas = usePlannerStore((s) => s.result?.prep_ctas)
  const arrivalCta = usePlannerStore(
    (s) => s.result?.days[0]?.arrival_from_airport?.connectivity_cta,
  )

  const ctas = prepCtas?.length ? prepCtas : arrivalCta ? [arrivalCta] : []

  return (
    <div className={embedded ? 'px-4 py-4' : 'border-b border-white/10 px-4 py-2.5 sm:px-6'}>
      <div className={`flex flex-col gap-3 ${embedded ? '' : 'mx-auto max-w-7xl'}`}>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5">
          <p className="jp-legend shrink-0 text-sm">준비</p>
          {PREP_LINKS.map((link) => (
            <a
              key={link.key}
              href={link.url}
              target="_blank"
              rel="noreferrer"
              className={link.className}
              title={link.title}
            >
              {link.label}
            </a>
          ))}
          {ctas.map((cta) => (
            <AffiliateOutboundLink
              key={`${cta.provider}-${cta.label}`}
              href={cta.url}
              className={`jp-btn text-xs ${
                cta.provider === 'kkday' ? 'jp-btn-kkday' : 'jp-btn-klook'
              }`}
              title={cta.hint}
            >
              {cta.label.replace(/^KKday에서\s*/, '').replace(/^Klook에서\s*/, '')}
            </AffiliateOutboundLink>
          ))}
        </div>
        <p className="text-[11px] leading-relaxed text-mist/45">
          이동 수단·다른 경로는 일정 카드의 「구글맵 길찾기」에서 출발·도착을 바꿔 확인하세요.
        </p>
      </div>
    </div>
  )
}
