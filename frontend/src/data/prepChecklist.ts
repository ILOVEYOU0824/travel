/** 일본여행 준비물 체크리스트 (폴더 이미지 기준, UI용 정적 목록) */
export type PrepCategoryId = 'essentials' | 'toiletries' | 'general'

export type PrepChecklistItem = {
  id: string
  label: string
}

export type PrepChecklistCategory = {
  id: PrepCategoryId
  title: string
  items: PrepChecklistItem[]
}

export const PREP_CHECKLIST: PrepChecklistCategory[] = [
  {
    id: 'essentials',
    title: '필수준비물',
    items: [
      { id: 'ess-eticket', label: '항공권 E-ticket' },
      { id: 'ess-passport', label: '여권(사본)' },
      { id: 'ess-cash', label: '현금(원화, 환전엔화)' },
      { id: 'ess-card', label: '해외사용 카드' },
      { id: 'ess-voucher', label: '숙소 및 항공, 예약 바우처' },
      { id: 'ess-backup-card', label: '비상용 체크카드 or 신용카드' },
      { id: 'ess-sim', label: '이심/유심, 로밍, 포켓 와이파이' },
      { id: 'ess-insurance', label: '여행자 보험' },
    ],
  },
  {
    id: 'toiletries',
    title: '세면도구',
    items: [
      { id: 'toi-brush', label: '칫솔, 치약' },
      { id: 'toi-shampoo', label: '샴푸, 린스' },
      { id: 'toi-face', label: '세안용품(클렌징 폼)' },
      { id: 'toi-body', label: '바디클렌저, 샤워볼' },
      { id: 'toi-skincare', label: '기초화장품 (스킨, 로션)' },
      { id: 'toi-sunscreen', label: '선크림' },
      { id: 'toi-makeup', label: '개인 화장품' },
      { id: 'toi-washbag', label: '3단 여행용 워시백' },
    ],
  },
  {
    id: 'general',
    title: '일반준비물',
    items: [
      { id: 'gen-outer', label: '겉옷' },
      { id: 'gen-pjs', label: '잠옷' },
      { id: 'gen-hat', label: '모자' },
      { id: 'gen-underwear', label: '속옷, 양말' },
      { id: 'gen-cold', label: '방한용품(목도리, 장갑)' },
      { id: 'gen-bag', label: '미니가방 or 백팩' },
      { id: 'gen-shoes', label: '운동화, 부츠, 슬리퍼' },
      { id: 'gen-dryer', label: '여행화 건조기' },
    ],
  },
]

export const PREP_CHECKLIST_STORAGE_KEY = 'jp-prep-checklist-v1'

export function allPrepItemIds(): string[] {
  return PREP_CHECKLIST.flatMap((c) => c.items.map((i) => i.id))
}
