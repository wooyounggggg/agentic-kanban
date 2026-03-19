# wt-board 기능 체크리스트

## A. 메인 화면 (칸반보드)

- [x] A1. 앱 실행 — `PYTHONPATH=wt-board/src python3 -m wt_board.cli.main`
- [x] A2. 컬럼 표시 — config의 statuses 순서대로
- [x] A3. 카드 표시 — 티켓번호 + 제목
- [ ] A4. 카드 상태 chip — 한글 라벨, 배경색 chip (이모지 아님) → 실 터미널 확인 필요
- [x] A5. 카드 담당자 — @이름
- [x] A6. 카드 TC 진행률 — 3/7 TC
- [x] A7. 카드 태그 — labels 표시
- [x] A8. 카드 에이전트 뱃지 — ● 활성 표시
- [x] A9. 빈 컬럼 스킵 — ←→ 네비게이션에서 카드 없는 컬럼 건너뜀
- [x] A10. 마우스 클릭 — 카드 선택, 더블클릭 진입
- [x] A11. Footer 키바인딩 표시

## B. 사이드바 (프로젝트)

- [x] B1. 맨 왼쪽에서 ← → 사이드바 포커스
- [x] B2. 포커스 시 파란 테두리 + ◀ 표시
- [x] B3. ↑↓로 프로젝트 즉시 전환 (보드 갱신)
- [x] B4. → 또는 Enter로 보드 복귀
- [x] B5. n (사이드바) — 프로젝트 추가 다이얼로그
- [x] B6. x (사이드바) — 프로젝트 삭제
- [x] B7. 프로젝트 추가 시 Dooray project ID + 루트 경로 + worktree 경로 입력

## C. 이슈 관리

- [x] C1. n (보드) — 이슈 추가 다이얼로그 (한글 UI)
- [x] C2. 이슈 생성: 조회 → 미리보기 → 생성 플로우
- [x] C3. 빈 입력 validation — 생성 버튼 비활성
- [x] C4. m — 상태 이동 다이얼로그
- [ ] C5. x (보드) — 이슈 삭제/아카이브 → **미구현**
- [ ] C6. / — 검색/필터 → **미구현**

## D. 에이전트 (Enter 키) ← **P0 버그**

- [ ] D1. Enter → 에이전트 시작/resume → tmux 윈도우로 전환 → **안 됨**
- [ ] D2. tmux 안에서 실행 시 같은 세션에 agent window 생성
- [ ] D3. 이미 실행 중이면 resume/focus
- [ ] D4. 카드에 에이전트 활성 뱃지 반영
- [ ] D5. 실제 claude CLI가 worktree에서 실행됨

## E. 이슈 상세 (i 키)

- [x] E1. i → 50/50 스플릿 상세 화면
- [x] E2. Esc → 보드 복귀
- [x] E3. 에이전트 상태 표시 (좌측)
- [x] E4. TC 체크리스트 (우측) + Space 토글
- [x] E5. Plan 섹션 (p 토글)
- [x] E6. Worklog 섹션 (l 토글)
- [x] E7. Description 섹션 (d 토글)
- [x] E8. Comments 섹션 (c 토글)
- [x] E9. f — Dooray fetch (본문 + 댓글)
- [x] E10. m — 상태 이동
- [x] E11. a — 에이전트 시작/포커스

## F. Dooray 연동

- [x] F1. s — 수동 전체 동기화
- [x] F2. 자동 폴링 (60초, 제목/상태/담당자만)
- [x] F3. f — 본문 + 댓글 fetch (상세 화면)
- [x] F4. DoorayTracker → dooray-cli.js 호출
- [x] F5. SyncService 생성 정상 (DoorayConfig 파라미터 수정 완료)

## G. UX / 렌더링

- [ ] G1. q 한번 → 경고 알림 → **렌더링 깨짐 보고됨** → 확인 필요
- [x] G2. q 두번 → 종료
- [x] G3. 한글 UI (모든 다이얼로그)
- [ ] G4. GitHub Dark 테마 → 실 터미널에서 색상 확인 필요
- [ ] G5. 상태 chip 배경색 렌더링 확인 필요

## H. 온보딩 / 설정

- [x] H1. 최초 실행 시 Dooray API key 입력
- [x] H2. .board/ init + config.yaml 생성
- [x] H3. 기존 .wt-state/ 마이그레이션

## I. CLI

- [x] I1. `wt-board init`
- [x] I2. `wt-board migrate`
- [x] I3. `wt-board add <ticket>`
- [x] I4. `wt-board list`
- [x] I5. `wt-board move <ticket> <status>`
- [x] I6. `wt-board show <ticket>`
