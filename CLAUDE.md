# JapanTrip AI — Agent 지침

이 프로젝트의 영속 규칙은 `.cursor/rules/`에 있다. 특히 **anti-hallucination.mdc**를 절대 어기지 말 것.

요약: Places/Directions API만 장소·이동 데이터를 제공하고, Claude는 후보 `place_id` 선택·일자 배정·intent 파싱만 한다.

개발 순서: Places → Directions → LLM+검증 → FE → 리플래닝 → Agoda → Redis/마무리.
