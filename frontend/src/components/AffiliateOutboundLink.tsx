import type { MouseEvent, ReactNode } from 'react'
import { bookingLandingUrl } from '../lib/affiliate'

/** Klook 등은 Referer가 없으면 봇으로 오인하기 쉬움. noreferrer 쓰지 않음. */
export function AffiliateOutboundLink({
  href,
  className,
  title,
  children,
  onClick,
}: {
  href: string
  className?: string
  title?: string
  children: ReactNode
  onClick?: (e: MouseEvent<HTMLAnchorElement>) => void
}) {
  return (
    <a
      href={bookingLandingUrl(href)}
      target="_blank"
      rel="noopener sponsored"
      referrerPolicy="origin-when-cross-origin"
      className={className}
      title={title}
      onClick={onClick}
    >
      {children}
    </a>
  )
}
