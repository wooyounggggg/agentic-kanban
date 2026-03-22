---
name: plan
description: 이슈의 구현 계획(plan.md)을 대화형으로 작성합니다.
user-invocable: true
argument-hint: <ticket-number> [프롬프트]
---

# agentic-kanban:plan

이슈의 plan.md를 대화형으로 작성합니다. 코드베이스를 분석하고, 사용자와 토의하며 구현 계획을 수립합니다.

## 입력

```
/agentic-kanban:plan <ticket-number> [초기 프롬프트]
```

사용자 입력: $ARGUMENTS

## 처리 절차

1. `.kanban/issues/{ticket}/issue.yaml` 읽기 — 이슈 정보 확인.

2. Dooray 티켓 본문이 있으면 `.kanban/issues/{ticket}/description.md` 참조.

3. 기존 plan.md가 있으면 읽어서 컨텍스트로 활용 (수정 모드).

4. 사용자의 프롬프트를 기반으로 구현 계획 작성:
   - 코드베이스 분석 (관련 파일/모듈 탐색)
   - 구현 단계 정리
   - 영향 범위 파악
   - TC(테스트 케이스) 필요 시 함께 작성

5. `.kanban/issues/{ticket}/plan.md` 에 결과 저장.

6. `.kanban/issues/{ticket}/worklog.jsonl` 에 작업 기록 추가.

## 산출물

- `.kanban/issues/{ticket}/plan.md` — 구현 계획서
- `.kanban/issues/{ticket}/checklist.yaml` — TC (선택)
- `.kanban/issues/{ticket}/worklog.jsonl` — 작업 로그

## 주의사항

- plan.md 작성 시 마크다운 형식 사용
- 기존 plan.md가 있으면 덮어쓰지 않고 수정 여부를 사용자에게 확인
- worktree 경로에서 실행하면 해당 프로젝트의 코드베이스를 분석
