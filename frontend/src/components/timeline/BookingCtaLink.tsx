import type { BookingCta } from '../../types'

export function BookingCtaLink({ cta }: { cta: BookingCta }) {
  return (
    <div className="flex w-full flex-col items-stretch gap-1.5">
      <a
        href={cta.url}
        target="_blank"
        rel="noreferrer sponsored"
        className={`jp-btn w-fit max-w-full ${
          cta.provider === 'kkday' ? 'jp-btn-kkday' : 'jp-btn-klook'
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {cta.label}
      </a>
      {cta.hint ? (
        <p className="max-w-md text-[11px] leading-relaxed text-mist/50">{cta.hint}</p>
      ) : null}
    </div>
  )
}
