import type { BookingCta } from '../../types'
import { AffiliateOutboundLink } from '../AffiliateOutboundLink'

export function BookingCtaLink({ cta }: { cta: BookingCta }) {
  const isKlook = cta.provider === 'klook'
  return (
    <div className="flex w-full flex-col items-stretch gap-1.5">
      <AffiliateOutboundLink
        href={cta.url}
        className={`jp-btn w-fit max-w-full ${isKlook ? 'jp-btn-klook' : 'jp-btn-kkday'}`}
        onClick={(e) => e.stopPropagation()}
      >
        {cta.label}
      </AffiliateOutboundLink>
      {cta.hint ? (
        <p className="max-w-md text-[11px] leading-relaxed text-mist/50">{cta.hint}</p>
      ) : null}
      {isKlook ? (
        <p className="max-w-md text-[11px] leading-relaxed text-mist/40">
          접속이 막히면 휴대폰 데이터(LTE/5G)로 열어 보세요.
        </p>
      ) : null}
    </div>
  )
}
