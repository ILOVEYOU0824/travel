import { usePlannerStore } from '../store/plannerStore'
import { AffiliateBadge } from './AffiliateBadge'

const PREP_LINKS = [
  {
    key: 'visitjapan',
    label: 'Visit Japan',
    url: 'https://www.vjw.digital.go.jp/main/#/vjwplo001',
    className: 'jp-btn jp-btn-visit',
    title: 'Visit Japan Web 입국 수속',
    rel: 'noreferrer',
  },
  {
    key: 'insurance',
    label: '여행자 보험',
    url: 'https://insurance.pay.naver.com/travel',
    className: 'jp-btn jp-btn-insurance',
    title: '네이버페이 해외여행보험 비교',
    rel: 'noreferrer',
  },
] as const

export function PrepCtasBar() {
  const prepCtas = usePlannerStore((s) => s.result?.prep_ctas)
  const arrivalCta = usePlannerStore(
    (s) => s.result?.days[0]?.arrival_from_airport?.connectivity_cta,
  )

  const ctas = prepCtas?.length
    ? prepCtas
    : arrivalCta
      ? [arrivalCta]
      : []

  return (
    <div className="border-b border-white/10 px-4 py-2 sm:px-6">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-2">
        <p className="jp-legend shrink-0 text-sm">준비</p>
        {PREP_LINKS.map((link) => (
          <a
            key={link.key}
            href={link.url}
            target="_blank"
            rel={link.rel}
            className={link.className}
            title={link.title}
          >
            {link.label}
          </a>
        ))}
        {ctas.map((cta) => (
          <a
            key={`${cta.provider}-${cta.label}`}
            href={cta.url}
            target="_blank"
            rel="noreferrer sponsored"
            className={`jp-btn ${cta.provider === 'kkday' ? 'jp-btn-kkday' : 'jp-btn-klook'}`}
            title={cta.hint}
          >
            {cta.label}
          </a>
        ))}
        <div className="w-full sm:ml-auto sm:w-auto">
          <AffiliateBadge />
        </div>
      </div>
    </div>
  )
}
